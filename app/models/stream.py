from datetime import datetime
from typing import Optional, List, Literal
from bson import ObjectId
from pydantic import BaseModel, Field

class StreamViewer(BaseModel):
    """Espectador de un stream"""
    user_id: str
    username: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    watch_time: int = 0  # Segundos viendo
    is_subscribed: bool = False

class StreamMetrics(BaseModel):
    """Métricas del stream"""
    peak_viewers: int = 0
    total_viewers: int = 0
    average_watch_time: float = 0.0
    total_watch_time: int = 0
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0

class StreamChat(BaseModel):
    """Chat del stream"""
    enabled: bool = True
    slow_mode: int = 0
    subscribers_only: bool = False
    followers_only: bool = False
    min_account_age_days: int = 0

class Stream(BaseModel):
    """Modelo de stream"""
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    username: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None  # Gaming, Music, Talk, etc.
    tags: List[str] = []
    language: Optional[str] = None
    
    # Configuración técnica
    stream_key: str
    rtmp_url: str
    room_id: str  # Para WebRTC
    resolution: str = "1080p"
    fps: int = 30
    bitrate: int = 6000  # kbps
    
    # Estado
    status: Literal["scheduled", "live", "ended", "cancelled"] = "scheduled"
    
    # Audiencia
    viewers: List[StreamViewer] = []
    current_viewers: int = 0
    metrics: StreamMetrics = StreamMetrics()
    
    # Chat
    chat_config: StreamChat = StreamChat()
    
    # Miniatura
    thumbnail_url: Optional[str] = None
    
    # Grabación
    is_recorded: bool = False
    recording_url: Optional[str] = None
    duration: int = 0  # Segundos
    
    # Monetización
    is_monetized: bool = False
    donations_enabled: bool = False
    
    # Horarios
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Metadatos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}