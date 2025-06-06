from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.chat import ChatType

class ChatBase(BaseModel):
    name: Optional[str] = None
    chat_type: ChatType

class ChatCreate(ChatBase):
    member_ids: Optional[List[int]] = []

class ChatUpdate(BaseModel):
    name: Optional[str] = None

class ChatResponse(ChatBase):
    id: int
    creator_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChatMemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    is_admin: bool
    joined_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ChatWithMembersResponse(ChatResponse):
    members: List[ChatMemberResponse]

class CreatePrivateChat(BaseModel):
    recipient_id: int

class CreateGroupChat(BaseModel):
    name: str
    member_ids: List[int] 