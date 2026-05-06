from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime

class CreateStreamRequest(BaseModel):
    """Schema para crear stream"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = None
    tags: List[str] = Field(default=[], max_items=10)
    language: Optional[str] = None
    resolution: str = "1080p"
    fps: int = Field(30, ge=15, le=60)
    bitrate: int = Field(6000, ge=1000, le=50000)
    is_recorded: bool = False
    chat_config: Optional[dict] = None
    scheduled_at: Optional[datetime] = None
    
    @validator('resolution')
    def validate_resolution(cls, v):
        allowed = ["720p", "1080p", "1440p", "2160p", "4K"]
        if v not in allowed:
            raise ValueError(f'Resolución no válida. Opciones: {allowed}')
        return v

class UpdateStreamRequest(BaseModel):
    """Schema para actualizar stream"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    chat_config: Optional[dict] = None

class StreamResponse(BaseModel):
    """Schema para respuesta de stream"""
    id: str = Field(alias="_id")
    user_id: str
    username: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    language: Optional[str] = None
    stream_key: str
    rtmp_url: str
    room_id: str
    resolution: str = "1080p"
    status: str
    current_viewers: int = 0
    metrics: dict = {}
    thumbnail_url: Optional[str] = None
    is_recorded: bool = False
    recording_url: Optional[str] = None
    duration: int = 0
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        populate_by_name = True

class StreamFilter(BaseModel):
    """Schema para filtrar streams"""
    status: Optional[Literal["live", "scheduled", "ended"]] = None
    category: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=50)