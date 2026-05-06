from datetime import datetime
from typing import Optional, List, Literal
from bson import ObjectId
from pydantic import BaseModel, Field

class PostMedia(BaseModel):
    """Media de una publicación"""
    type: Literal["image", "video", "audio", "gif"]
    url: str
    thumbnail_url: Optional[str] = None
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None  # Para videos
    file_size: Optional[int] = None
    order: int = 0  # Orden en el carrusel

class PostLocation(BaseModel):
    """Ubicación de la publicación"""
    country: Optional[str] = None
    city: Optional[str] = None
    place_name: Optional[str] = None
    coordinates: Optional[dict] = None

class Comment(BaseModel):
    """Comentario en una publicación"""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    username: str
    profile_picture: Optional[str] = None
    content: str
    likes: List[str] = []  # IDs de usuarios que dieron like
    likes_count: int = 0
    replies: List['Comment'] = []  # Respuestas anidadas
    replies_count: int = 0
    is_edited: bool = False
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    edited_at: Optional[datetime] = None

class PostPoll(BaseModel):
    """Encuesta en una publicación"""
    question: str
    options: List[dict]  # [{text: str, votes: int, voters: List[str]}]
    total_votes: int = 0
    ends_at: Optional[datetime] = None
    is_multiple_choice: bool = False

class Post(BaseModel):
    """Modelo de publicación"""
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    username: str
    profile_picture: Optional[str] = None
    
    # Contenido
    content: str
    media: List[PostMedia] = []
    poll: Optional[PostPoll] = None
    location: Optional[PostLocation] = None
    
    # Metadatos del contenido
    language: Optional[str] = None
    sentiment: Optional[str] = None  # positive, negative, neutral
    has_spoiler: bool = False
    is_nsfw: bool = False
    
    # Interacciones
    likes: List[str] = []  # IDs de usuarios
    likes_count: int = 0
    comments: List[Comment] = []
    comments_count: int = 0
    shares_count: int = 0
    views_count: int = 0
    bookmarks_count: int = 0
    
    # Visibilidad
    visibility: Literal["public", "friends", "private"] = "public"
    allowed_users: List[str] = []  # Usuarios específicos que pueden ver
    excluded_users: List[str] = []  # Usuarios excluidos
    
    # Etiquetas y menciones
    tags: List[str] = []
    hashtags: List[str] = []
    mentions: List[str] = []  # IDs de usuarios mencionados
    
    # Compartir
    is_shared: bool = False
    original_post_id: Optional[str] = None
    shared_from: Optional[str] = None
    
    # Pinned
    is_pinned: bool = False
    
    # Programación
    scheduled_at: Optional[datetime] = None
    
    # Metadatos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    edited_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}