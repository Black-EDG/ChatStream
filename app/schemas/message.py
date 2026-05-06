"""
Schemas para mensajes y chats
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime

class MessageMediaSchema(BaseModel):
    """Schema para contenido multimedia de mensaje"""
    type: Literal["text", "image", "audio", "video", "file", "sticker", "gif"] = "text"
    content: str = Field(..., min_length=1, max_length=5000)
    thumbnail_url: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = Field(None, le=50 * 1024 * 1024)  # 50MB max
    duration: Optional[int] = Field(None, ge=1, le=3600)  # Máximo 1 hora
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: Optional[str] = None

    @validator('content')
    def validate_content(cls, v, values):
        if not v or not v.strip():
            raise ValueError('El contenido no puede estar vacío')
        if len(v) > 5000:
            raise ValueError('El contenido excede los 5000 caracteres permitidos')
        return v.strip()

class MessageReplySchema(BaseModel):
    """Schema para respuesta a mensaje"""
    message_id: str
    content_preview: str = Field(..., max_length=100)

class SendMessageRequest(BaseModel):
    """Schema para enviar un mensaje"""
    chat_id: str = Field(...)
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: Literal["text", "image", "audio", "video", "file"] = "text"
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    reply_to: Optional[str] = None
    file_info: Optional[dict] = None

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('El mensaje no puede estar vacío')
        # Sanitizar HTML básico
        import html
        return html.escape(v.strip())

class MessageReactionSchema(BaseModel):
    """Schema para reacción a mensaje"""
    reaction_type: Literal["like", "love", "haha", "wow", "sad", "angry"] = "like"

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
    read_by: List[str] = []
    timestamp: datetime
    edited_at: Optional[datetime] = None

    class Config:
        populate_by_name = True

class ChatCreateSchema(BaseModel):
    """Schema para crear un chat"""
    type: Literal["private", "group"] = "private"
    participant_ids: List[str] = Field(..., min_items=1, max_items=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class ChatResponse(BaseModel):
    """Schema para respuesta de chat"""
    id: str = Field(alias="_id")
    type: str
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    participants: List[dict] = []
    participants_ids: List[str] = []
    language: Optional[str] = None
    country: Optional[str] = None
    last_message: Optional[dict] = None
    message_count: int = 0
    unread_count: dict = {}
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        populate_by_name = True

class TypingStatusSchema(BaseModel):
    """Schema para estado de escritura"""
    chat_id: str
    is_typing: bool

class MessageSearchSchema(BaseModel):
    """Schema para búsqueda de mensajes"""
    query: str = Field(..., min_length=1)
    chat_id: Optional[str] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=50)

class ChatListResponse(BaseModel):
    """Schema para lista de chats"""
    chats: List[ChatResponse]
    total: int
    page: int
    pages: int