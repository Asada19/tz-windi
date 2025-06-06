from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, Boolean, String
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel

class Message(BaseModel):
    __tablename__ = "messages"
    
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False)
    
    # Уникальный идентификатор для предотвращения дублирования
    client_message_id = Column(String(100), nullable=True, index=True)
    
    # Связи
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    read_receipts = relationship("MessageReadReceipt", back_populates="message", cascade="all, delete-orphan") 