from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime

class MessageContent(BaseModel):
    """Contenido del mensaje"""
    type: Literal["text", "image", "audio", "video", "file", "sticker", "gif"] = "text"
    content: str = Field(..., min_length=1, max_length=5000)
    thumbnail_url: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    
    @validator('content')
    def validate_content(cls, v, values):
        if not v.strip():
            raise ValueError('El contenido no puede estar vacío')
        return v

class SendMessageRequest(BaseModel):
    """Schema para enviar mensaje"""
    chat_id: str
    content: MessageContent
    reply_to_message_id: Optional[str] = None

class MessageResponse(BaseModel):
    """Schema para respuesta de mensaje"""
    id: str = Field(alias="_id")
    chat_id: str
    sender_id: str
    sender_username: str
    content: dict
    reply_to: Optional[dict] = None
    reactions: List[dict] = []
    reactions_count: int = 0
    is_edited: bool = False
    is_deleted: bool = False
    is_read: bool = False
    timestamp: datetime
    edited_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True

class ChatCreate(BaseModel):
    """Schema para crear chat"""
    type: Literal["private", "group"] = "private"
    participant_ids: List[str] = Field(..., min_items=1, max_items=50)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class ChatResponse(BaseModel):
    """Schema para respuesta de chat"""
    id: str = Field(alias="_id")
    type: str
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    participants: List[dict] = []
    language: Optional[str] = None
    country: Optional[str] = None
    last_message: Optional[dict] = None
    message_count: int = 0
    unread_count: dict = {}
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True

class ReactionRequest(BaseModel):
    """Schema para reaccionar a mensaje"""
    message_id: str
    reaction_type: str = Field(..., pattern="^(like|love|haha|wow|sad|angry)$")

class TypingStatus(BaseModel):
    """Schema para estado de escritura"""
    chat_id: str
    is_typing: bool