from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MessageBase(BaseModel):
    text: str

class MessageCreate(MessageBase):
    chat_id: int
    client_message_id: Optional[str] = None

class MessageUpdate(BaseModel):
    text: Optional[str] = None
    is_read: Optional[bool] = None

class MessageResponse(MessageBase):
    id: int
    chat_id: int
    sender_id: int
    sender_username: str
    timestamp: datetime
    is_read: bool
    client_message_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class MessageWithReadReceipts(MessageResponse):
    read_by: List[dict]

class WebSocketMessageData(BaseModel):
    action: str
    data: dict

class SendMessageWebSocket(BaseModel):
    chat_id: int
    text: str
    client_message_id: Optional[str] = None

class MarkMessageRead(BaseModel):
    message_id: int

class TypingIndicator(BaseModel):
    chat_id: int
    is_typing: bool 