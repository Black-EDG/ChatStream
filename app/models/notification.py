from datetime import datetime
from typing import Optional, List, Literal
from bson import ObjectId
from pydantic import BaseModel, Field

class NotificationAction(BaseModel):
    """Acción asociada a la notificación"""
    type: str  # view, follow, like, comment, etc.
    target_id: Optional[str] = None  # ID del recurso objetivo
    target_type: Optional[str] = None  # user, post, comment, stream
    url: Optional[str] = None

class Notification(BaseModel):
    """Modelo de notificación"""
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str  # Usuario que recibe la notificación
    from_user_id: Optional[str] = None  # Usuario que generó la notificación
    from_username: Optional[str] = None
    
    # Tipo de notificación
    type: Literal[
        "follow", "like_profile", "like_post", "like_comment",
        "comment", "reply", "mention", "friend_request",
        "friend_accepted", "new_follower", "stream_started",
        "stream_ended", "message", "system"
    ]
    
    # Contenido
    title: str
    message: str
    icon: Optional[str] = None
    image_url: Optional[str] = None
    
    # Acción
    action: Optional[NotificationAction] = None
    
    # Estado
    is_read: bool = False
    is_seen: bool = False
    read_at: Optional[datetime] = None
    
    # Prioridad
    priority: int = 0  # 0: normal, 1: alta, 2: urgente
    
    # Metadatos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}