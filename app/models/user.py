from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr

class UserLocation(BaseModel):
    """Ubicación del usuario"""
    country: str
    city: Optional[str] = None
    state: Optional[str] = None
    timezone: Optional[str] = None
    coordinates: Optional[dict] = None  # {lat: float, lng: float}

class UserPreferences(BaseModel):
    """Preferencias de usuario"""
    language: str = "es"
    notifications_enabled: bool = True
    private_profile: bool = False
    show_online_status: bool = True
    dark_mode: bool = False
    email_notifications: bool = True
    push_notifications: bool = True

class UserSocialLinks(BaseModel):
    """Enlaces sociales del perfil"""
    website: Optional[str] = None
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None

class UserStats(BaseModel):
    """Estadísticas del usuario"""
    total_posts: int = 0
    total_likes_received: int = 0
    total_comments: int = 0
    total_streams: int = 0
    total_streaming_hours: float = 0.0
    account_age_days: int = 0

class User(BaseModel):
    """Modelo principal de usuario"""
    id: Optional[str] = Field(alias="_id", default=None)
    username: str
    email: str
    hashed_password: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    cover_picture: Optional[str] = None
    location: UserLocation = UserLocation(country="Unknown")
    preferences: UserPreferences = UserPreferences()
    social_links: UserSocialLinks = UserSocialLinks()
    
    # Seguidores y seguidos
    followers_count: int = 0
    following_count: int = 0
    followers: List[str] = []  # IDs de seguidores (opcional, para consultas rápidas)
    following: List[str] = []  # IDs de seguidos
    
    # Amigos
    friends_count: int = 0
    friends: List[str] = []  # IDs de amigos
    
    # Likes
    likes_received: int = 0
    liked_users: List[str] = []  # Usuarios que dieron like al perfil
    
    # Estado
    is_active: bool = True
    is_verified: bool = False
    is_online: bool = False
    last_seen: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # Roles y permisos
    roles: List[str] = ["user"]
    permissions: List[str] = []
    
    # Estadísticas
    stats: UserStats = UserStats()
    
    # Metadatos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

class Follower(BaseModel):
    """Modelo de relación seguidor"""
    id: Optional[str] = Field(alias="_id", default=None)
    follower_id: str  # Quién sigue
    following_id: str  # A quién sigue
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class FriendRequest(BaseModel):
    """Modelo de solicitud de amistad"""
    id: Optional[str] = Field(alias="_id", default=None)
    from_user_id: str
    to_user_id: str
    status: str = "pending"  # pending, accepted, rejected
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}