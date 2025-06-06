from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.message_repository import MessageRepository
from app.repositories.chat_repository import ChatRepository
from app.schemas.message import MessageResponse, MessageCreate
from app.auth import get_current_active_user
from app.models.user import User
from app.websocket_manager import manager

router = APIRouter()

@router.get("/history/{chat_id}", response_model=List[MessageResponse])
async def get_chat_history(
    chat_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    chat_repo = ChatRepository(db)
    message_repo = MessageRepository(db)
    
    if not await chat_repo.is_member(chat_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await message_repo.get_chat_messages(chat_id, limit, offset)
    
    return [{
        "id": msg.id,
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
        "sender_username": msg.sender.username,
        "text": msg.text,
        "timestamp": msg.timestamp,
        "is_read": msg.is_read,
        "client_message_id": msg.client_message_id
    } for msg in messages]

@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Отправка сообщения в чат"""
    chat_repo = ChatRepository(db)
    message_repo = MessageRepository(db)
    
    # Проверяем, является ли пользователь участником чата
    if not await chat_repo.is_member(message_data.chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому чату"
        )
    
    # Создаем сообщение (с проверкой дублирования)
    message = await message_repo.create(message_data, current_user.id)
    
    # Формируем данные для WebSocket
    message_response = {
        "id": message.id,
        "chat_id": message.chat_id,
        "sender_id": message.sender_id,
        "sender_username": current_user.username,
        "text": message.text,
        "timestamp": message.timestamp.isoformat(),
        "is_read": message.is_read,
        "client_message_id": message.client_message_id
    }
    
    # Отправляем через WebSocket всем участникам чата
    await manager.broadcast_new_message(
        message_response, 
        message.chat_id, 
        current_user.id
    )
    
    return message_response

@router.post("/{message_id}/read")
async def mark_message_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Отметка сообщения как прочитанного"""
    message_repo = MessageRepository(db)
    chat_repo = ChatRepository(db)
    
    # Получаем сообщение
    message = await message_repo.get_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено"
        )
    
    # Проверяем доступ к чату
    if not await chat_repo.is_member(message.chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому чату"
        )
    
    # Нельзя отметить свое сообщение как прочитанное
    if message.sender_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отметить свое сообщение как прочитанное"
        )
    
    # Отмечаем как прочитанное
    success = await message_repo.mark_message_read(message_id, current_user.id)
    
    if success:
        # Уведомляем через WebSocket о прочтении
        await manager.broadcast_message_read(
            message_id, 
            message.chat_id, 
            current_user.id
        )
        return {"message": "Сообщение отмечено как прочитанное"}
    else:
        return {"message": "Сообщение уже было прочитано"}

@router.get("/{message_id}/read-receipts")
async def get_message_read_receipts(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получение списка пользователей, прочитавших сообщение"""
    message_repo = MessageRepository(db)
    chat_repo = ChatRepository(db)
    
    # Получаем сообщение
    message = await message_repo.get_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено"
        )
    
    # Проверяем доступ к чату
    if not await chat_repo.is_member(message.chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому чату"
        )
    
    # Получаем квитанции о прочтении
    receipts = await message_repo.get_message_read_receipts(message_id)
    
    result = [
        {
            "user_id": receipt.user_id,
            "username": receipt.user.username,
            "read_at": receipt.read_at
        }
        for receipt in receipts
    ]
    
    return {"read_by": result}

@router.get("/unread/{chat_id}")
async def get_unread_messages(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получение непрочитанных сообщений в чате"""
    chat_repo = ChatRepository(db)
    message_repo = MessageRepository(db)
    
    # Проверяем доступ к чату
    if not await chat_repo.is_member(chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому чату"
        )
    
    # Получаем непрочитанные сообщения
    messages = await message_repo.get_unread_messages(chat_id, current_user.id)
    
    result = []
    for message in messages:
        message_data = {
            "id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "sender_username": message.sender.username,
            "text": message.text,
            "timestamp": message.timestamp,
            "is_read": message.is_read,
            "client_message_id": message.client_message_id
        }
        result.append(message_data)
    
    return {"unread_messages": result, "count": len(result)}

@router.get("/stats/{chat_id}")
async def get_chat_message_stats(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получение статистики сообщений в чате"""
    chat_repo = ChatRepository(db)
    message_repo = MessageRepository(db)
    
    # Проверяем доступ к чату
    if not await chat_repo.is_member(chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому чату"
        )
    
    # Получаем общее количество сообщений
    total_messages = await message_repo.get_chat_message_count(chat_id)
    
    # Получаем количество непрочитанных
    unread_messages = await message_repo.get_unread_messages(chat_id, current_user.id)
    unread_count = len(unread_messages)
    
    return {
        "chat_id": chat_id,
        "total_messages": total_messages,
        "unread_count": unread_count
    } 