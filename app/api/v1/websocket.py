import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.database import get_db
from app.repositories.message_repository import MessageRepository
from app.repositories.chat_repository import ChatRepository
from app.schemas.message import SendMessageWebSocket, MarkMessageRead, TypingIndicator
from app.websocket_manager import manager
from app.config import settings
from app.auth import get_user_by_username
from app.models.user import User

router = APIRouter()

async def get_user_from_token(token: str, db: AsyncSession) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await get_user_by_username(db, username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket, token: str = None):
    if not token:
        await websocket.close(code=1008, reason="Token required")
        return
    
    async for db in get_db():
        try:
            user = await get_user_from_token(token, db)
        except HTTPException:
            await websocket.close(code=1008, reason="Invalid token")
            return
        break
    
    await manager.connect(websocket, user)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                action = message_data.get("action")
                payload = message_data.get("data", {})
                
                async for db in get_db():
                    await handle_websocket_message(action, payload, user, db)
                    break
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": f"Error processing message: {str(e)}"
                }))
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user)

async def handle_websocket_message(action: str, payload: dict, user: User, db: AsyncSession):
    
    if action == "send_message":
        await handle_send_message(payload, user, db)
    
    elif action == "mark_read":
        await handle_mark_read(payload, user, db)
    
    elif action == "typing":
        await handle_typing_indicator(payload, user, db)
    
    elif action == "ping":
        await manager.send_personal_message(
            json.dumps({"type": "pong"}), 
            user.id
        )
    
    else:
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "message": f"Unknown action: {action}"
            }),
            user.id
        )

async def handle_send_message(payload: dict, user: User, db: AsyncSession):
    try:
        message_data = SendMessageWebSocket(**payload)
        
        chat_repo = ChatRepository(db)
        message_repo = MessageRepository(db)
        
        if not await chat_repo.is_member(message_data.chat_id, user.id):
            await manager.send_personal_message(
                json.dumps({
                    "type": "error",
                    "message": "No access to this chat"
                }),
                user.id
            )
            return
        
        from app.schemas.message import MessageCreate
        message_create = MessageCreate(
            chat_id=message_data.chat_id,
            text=message_data.text,
            client_message_id=message_data.client_message_id
        )
        
        message = await message_repo.create(message_create, user.id)
        
        # Формируем ответ
        message_response = {
            "id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "sender_username": user.username,
            "text": message.text,
            "timestamp": message.timestamp.isoformat(),
            "is_read": message.is_read,
            "client_message_id": message.client_message_id
        }
        
        # Отправляем всем участникам чата
        await manager.broadcast_new_message(
            message_response,
            message.chat_id,
            user.id
        )
        
        # Подтверждаем отправителю
        await manager.send_personal_message(
            json.dumps({
                "type": "message_sent",
                "data": message_response
            }),
            user.id
        )
        
    except Exception as e:
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "message": f"Failed to send message: {str(e)}"
            }),
            user.id
        )

async def handle_mark_read(payload: dict, user: User, db: AsyncSession):
    """Обработка отметки сообщения как прочитанного"""
    try:
        mark_read_data = MarkMessageRead(**payload)
        
        message_repo = MessageRepository(db)
        chat_repo = ChatRepository(db)
        
        # Получаем сообщение
        message = await message_repo.get_by_id(mark_read_data.message_id)
        if not message:
            await manager.send_personal_message(
                json.dumps({
                    "type": "error",
                    "message": "Message not found"
                }),
                user.id
            )
            return
        
        # Проверяем доступ
        if not await chat_repo.is_member(message.chat_id, user.id):
            await manager.send_personal_message(
                json.dumps({
                    "type": "error",
                    "message": "No access to this chat"
                }),
                user.id
            )
            return
        
        # Нельзя отметить свое сообщение
        if message.sender_id == user.id:
            return
        
        # Отмечаем как прочитанное
        success = await message_repo.mark_message_read(mark_read_data.message_id, user.id)
        
        if success:
            # Уведомляем участников чата
            await manager.broadcast_message_read(
                mark_read_data.message_id,
                message.chat_id,
                user.id
            )
            
    except Exception as e:
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "message": f"Failed to mark message as read: {str(e)}"
            }),
            user.id
        )

async def handle_typing_indicator(payload: dict, user: User, db: AsyncSession):
    """Обработка индикатора печатания"""
    try:
        typing_data = TypingIndicator(**payload)
        
        chat_repo = ChatRepository(db)
        
        # Проверяем доступ к чату
        if not await chat_repo.is_member(typing_data.chat_id, user.id):
            return
        
        # Обрабатываем индикатор печатания
        await manager.handle_typing_indicator(
            typing_data.chat_id,
            user.id,
            typing_data.is_typing
        )
        
    except Exception as e:
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "message": f"Failed to handle typing indicator: {str(e)}"
            }),
            user.id
        )

@router.get("/online-users")
async def get_online_users():
    """Получение списка подключенных пользователей"""
    connected_users = manager.get_connected_users()
    return {"online_users": connected_users, "count": len(connected_users)}

@router.websocket("/test")
async def websocket_test(websocket: WebSocket):
    """Тестовый WebSocket эндпоинт для проверки подключения"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass 