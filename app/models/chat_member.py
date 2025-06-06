from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class ChatMember(BaseModel):
    __tablename__ = "chat_members"
    
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Связи
    chat = relationship("Chat", back_populates="members")
    user = relationship("User", back_populates="chat_memberships")
    
    # Уникальная связь пользователь-чат
    __table_args__ = (
        {"extend_existing": True},
    ) 