import json
import asyncio
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.database import get_db, get_redis
from app.repositories.message_repository import MessageRepository
from app.repositories.chat_repository import ChatRepository
from app.models.user import User

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.typing_users: Dict[int, Set[int]] = {}
        self.redis_client = None

    async def connect(self, websocket: WebSocket, user: User):
        await websocket.accept()
        
        if user.id not in self.active_connections:
            self.active_connections[user.id] = []
        
        self.active_connections[user.id].append(websocket)
        
        if self.redis_client is None:
            self.redis_client = await get_redis()
        
        await self.broadcast_user_status(user.id, "online")

    async def disconnect(self, websocket: WebSocket, user: User):
        if user.id in self.active_connections:
            if websocket in self.active_connections[user.id]:
                self.active_connections[user.id].remove(websocket)
            
            if not self.active_connections[user.id]:
                del self.active_connections[user.id]
                await self.broadcast_user_status(user.id, "offline")
                
                for chat_id in list(self.typing_users.keys()):
                    if user.id in self.typing_users[chat_id]:
                        self.typing_users[chat_id].discard(user.id)
                        await self.broadcast_typing_status(chat_id, user.id, False)

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            disconnected_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    disconnected_connections.append(connection)
            
            for connection in disconnected_connections:
                self.active_connections[user_id].remove(connection)

    async def broadcast_to_chat(self, message: str, chat_id: int, sender_id: int = None):
        async for db in get_db():
            chat_repo = ChatRepository(db)
            chat = await chat_repo.get_by_id(chat_id)
            
            if chat:
                for member in chat.members:
                    if sender_id and member.user_id == sender_id:
                        continue
                    
                    await self.send_personal_message(message, member.user_id)
            break

    async def handle_typing_indicator(self, chat_id: int, user_id: int, is_typing: bool):
        if chat_id not in self.typing_users:
            self.typing_users[chat_id] = set()
        
        if is_typing:
            self.typing_users[chat_id].add(user_id)
        else:
            self.typing_users[chat_id].discard(user_id)
        
        await self.broadcast_typing_status(chat_id, user_id, is_typing)

    async def broadcast_typing_status(self, chat_id: int, user_id: int, is_typing: bool):
        message = {
            "type": "typing_indicator",
            "data": {
                "chat_id": chat_id,
                "user_id": user_id,
                "is_typing": is_typing
            }
        }
        await self.broadcast_to_chat(json.dumps(message), chat_id, user_id)

    async def broadcast_user_status(self, user_id: int, status: str):
        message = {
            "type": "user_status",
            "data": {
                "user_id": user_id,
                "status": status
            }
        }
        
        for connected_user_id in self.active_connections:
            if connected_user_id != user_id:
                await self.send_personal_message(json.dumps(message), connected_user_id)

    async def broadcast_new_message(self, message_data: dict, chat_id: int, sender_id: int):
        message = {
            "type": "new_message",
            "data": message_data
        }
        await self.broadcast_to_chat(json.dumps(message), chat_id, sender_id)

    async def broadcast_message_read(self, message_id: int, chat_id: int, reader_id: int):
        message = {
            "type": "message_read",
            "data": {
                "message_id": message_id,
                "chat_id": chat_id,
                "reader_id": reader_id
            }
        }
        await self.broadcast_to_chat(json.dumps(message), chat_id)

    def get_connected_users(self) -> List[int]:
        return list(self.active_connections.keys())

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self.active_connections

manager = ConnectionManager() 