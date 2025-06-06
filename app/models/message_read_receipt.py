from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel

class MessageReadReceipt(BaseModel):
    __tablename__ = "message_read_receipts"
    
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Связи
    message = relationship("Message", back_populates="read_receipts")
    user = relationship("User")
    
    # Уникальное ограничение: один пользователь может прочитать сообщение только один раз
    __table_args__ = (
        UniqueConstraint('message_id', 'user_id', name='unique_message_user_read'),
    ) 