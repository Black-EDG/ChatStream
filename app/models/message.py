from datetime import datetime
from typing import Optional, List, Literal
from bson import ObjectId
from pydantic import BaseModel, Field

class MessageMedia(BaseModel):
    type: Literal["text", "image", "audio", "video"]
    content: str  # Texto o URL del media
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None  # Para audio/video
    size: Optional[int] = None

class MessageReaction(BaseModel):
    user_id: str
    reaction_type: str  # like, love, laugh, etc
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    chat_id: str
    sender_id: str
    sender_username: str
    content: MessageMedia
    reactions: List[MessageReaction] = []
    is_edited: bool = False
    is_deleted: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    edited_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class Chat(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    type: Literal["global", "private"]
    participants: List[str] = []
    language: Optional[str] = None  # Para chats globales
    country: Optional[str] = None   # Para chats globales
    name: Optional[str] = None
    last_message: Optional[Message] = None
    unread_count: dict = Field(default_factory=dict)  # {user_id: count}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True