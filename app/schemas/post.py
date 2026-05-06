from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime

class PostMediaSchema(BaseModel):
    """Schema para media de publicación"""
    type: Literal["image", "video", "audio", "gif"]
    url: str
    thumbnail_url: Optional[str] = None
    alt_text: Optional[str] = None
    order: int = 0

class CreatePostRequest(BaseModel):
    """Schema para crear publicación"""
    content: str = Field(..., min_length=1, max_length=2000)
    media: List[PostMediaSchema] = Field(default=[], max_items=10)
    visibility: Literal["public", "friends", "private"] = "public"
    tags: List[str] = Field(default=[], max_items=20)
    hashtags: List[str] = Field(default=[], max_items=20)
    location: Optional[dict] = None
    is_nsfw: bool = False
    has_spoiler: bool = False
    scheduled_at: Optional[datetime] = None
    
    @validator('content')
    def validate_content(cls, v):
        if len(v.strip()) == 0 and not cls.media:
            raise ValueError('La publicación debe tener contenido o media')
        return v

class UpdatePostRequest(BaseModel):
    """Schema para actualizar publicación"""
    content: Optional[str] = Field(None, max_length=2000)
    visibility: Optional[Literal["public", "friends", "private"]] = None
    tags: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    is_nsfw: Optional[bool] = None
    has_spoiler: Optional[bool] = None

class CommentRequest(BaseModel):
    """Schema para crear comentario"""
    content: str = Field(..., min_length=1, max_length=1000)
    reply_to_comment_id: Optional[str] = None

class PostResponse(BaseModel):
    """Schema para respuesta de publicación"""
    id: str = Field(alias="_id")
    user_id: str
    username: str
    profile_picture: Optional[str] = None
    content: str
    media: List[dict] = []
    poll: Optional[dict] = None
    location: Optional[dict] = None
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    views_count: int = 0
    visibility: str = "public"
    tags: List[str] = []
    hashtags: List[str] = []
    is_pinned: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True

class FeedRequest(BaseModel):
    """Schema para solicitar feed"""
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=50)
    feed_type: Literal["following", "explore", "trending"] = "following"
    country: Optional[str] = None
    language: Optional[str] = None