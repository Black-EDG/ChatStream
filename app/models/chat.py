from datetime import datetime
from typing import Optional, List, Literal
from bson import ObjectId
from pydantic import BaseModel, Field

class MessageMedia(BaseModel):
    """Contenido multimedia del mensaje"""
    type: Literal["text", "image", "audio", "video", "file", "sticker", "gif"]
    content: str  # Texto o URL del media
    thumbnail_url: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None  # Duración en segundos para audio/video
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: Optional[str] = None

class MessageReaction(BaseModel):
    """Reacción a un mensaje"""
    user_id: str
    username: str
    reaction_type: str  # like, love, haha, wow, sad, angry
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MessageReply(BaseModel):
    """Respuesta a un mensaje"""
    message_id: str
    content_preview: str
    sender_username: str

class Message(BaseModel):
    """Modelo de mensaje"""
    id: Optional[str] = Field(alias="_id", default=None)
    chat_id: str
    sender_id: str
    sender_username: str
    content: MessageMedia
    reply_to: Optional[MessageReply] = None
    reactions: List[MessageReaction] = []
    reactions_count: int = 0
    is_edited: bool = False
    is_deleted: bool = False
    is_read: bool = False
    read_by: List[str] = []  # IDs de usuarios que leyeron
    delivered_to: List[str] = []  # IDs de usuarios que recibieron
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    edited_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class ChatParticipant(BaseModel):
    """Participante de un chat"""
    user_id: str
    username: str
    profile_picture: Optional[str] = None
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_read_at: Optional[datetime] = None
    is_admin: bool = False
    is_muted: bool = False

class Chat(BaseModel):
    """Modelo de chat"""
    id: Optional[str] = Field(alias="_id", default=None)
    type: Literal["global", "private", "group"]
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    participants: List[ChatParticipant] = []
    participants_ids: List[str] = []  # Para búsquedas rápidas
    
    # Para chats globales
    language: Optional[str] = None
    country: Optional[str] = None
    topic: Optional[str] = None  # Tema del chat global
    
    # Configuración
    is_encrypted: bool = False
    max_participants: int = 100
    slow_mode_seconds: int = 0  # Modo lento (0 = desactivado)
    
    # Último mensaje
    last_message: Optional[Message] = None
    
    # Contadores
    message_count: int = 0
    unread_count: dict = Field(default_factory=dict)  # {user_id: count}
    
    # Creador
    created_by: Optional[str] = None
    
    # Metadatos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}