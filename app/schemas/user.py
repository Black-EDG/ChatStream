from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import re

class UserRegister(BaseModel):
    """Schema para registro de usuario"""
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=30,
        pattern="^[a-zA-Z0-9_]+$",
        description="Nombre de usuario (solo letras, números y guiones bajos)"
    )
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    language: str = "es"
    
    @validator('username')
    def validate_username(cls, v):
        if v.lower() in ['admin', 'root', 'system', 'moderator', 'null', 'undefined']:
            raise ValueError('Nombre de usuario no permitido')
        return v
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

class UserLogin(BaseModel):
    """Schema para inicio de sesión"""
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    """Schema para actualizar perfil"""
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    profile_picture: Optional[str] = None
    cover_picture: Optional[str] = None
    location: Optional[dict] = None
    preferences: Optional[dict] = None
    social_links: Optional[dict] = None

class UserResponse(BaseModel):
    """Schema para respuesta de usuario (sin datos sensibles)"""
    id: str = Field(alias="_id")
    username: str
    email: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    cover_picture: Optional[str] = None
    location: dict = {}
    preferences: dict = {}
    social_links: dict = {}
    followers_count: int = 0
    following_count: int = 0
    friends_count: int = 0
    likes_received: int = 0
    is_active: bool = True
    is_verified: bool = False
    is_online: bool = False
    last_seen: Optional[datetime] = None
    stats: dict = {}
    created_at: datetime
    
    class Config:
        populate_by_name = True

class TokenResponse(BaseModel):
    """Schema para respuesta de tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None

class RefreshTokenRequest(BaseModel):
    """Schema para refrescar token"""
    refresh_token: str

class FollowRequest(BaseModel):
    """Schema para seguir/dejar de seguir"""
    user_id: str

class FriendRequestSchema(BaseModel):
    """Schema para solicitud de amistad"""
    message: Optional[str] = Field(None, max_length=200)
    # SIN user_id, porque ya va en la URL

class UserSearch(BaseModel):
    """Schema para búsqueda de usuarios"""
    query: str = Field(..., min_length=1)
    country: Optional[str] = None
    language: Optional[str] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)