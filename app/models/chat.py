from sqlalchemy import Column, String, Enum, Integer, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from .base import BaseModel

class ChatType(PyEnum):
    PRIVATE = "private"
    GROUP = "group"

class Chat(BaseModel):
    __tablename__ = "chats"
    
    name = Column(String(100), nullable=True)  # Для группововых чатов
    chat_type = Column(Enum(ChatType), nullable=False, default=ChatType.PRIVATE)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Связи
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    members = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan") 