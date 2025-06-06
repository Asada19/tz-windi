from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    chat_memberships = relationship("ChatMember", back_populates="user")
    created_chats = relationship("Chat", foreign_keys="Chat.creator_id", back_populates="creator") 