"""
Configuración central de la aplicación
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Información de la aplicación
    APP_NAME: str = "Social Stream Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "social_stream"
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "tu-super-secreto-cambiar-en-produccion-2024"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Bcrypt
    BCRYPT_ROUNDS: int = 12
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # segundos
    RATE_LIMIT_BURST: int = 20
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "mp4", "mp3", "webm"]
    UPLOAD_DIR: str = "uploads"
    
    # Media
    MEDIA_BASE_URL: str = "http://localhost:8000/media"
    
    # Streaming
    RTMP_SERVER_URL: str = "rtmp://localhost:1935/live"
    RTMP_APPLICATION: str = "live"
    TURN_SERVER_URL: str = "turn:localhost:3478"
    TURN_USERNAME: str = "turnuser"
    TURN_PASSWORD: str = "turnpassword"
    STREAM_KEY_SECRET: str = "stream-secret-key"
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # segundos
    WS_MAX_CONNECTIONS: int = 10000
    
    # Chat
    MAX_MESSAGE_LENGTH: int = 5000
    MAX_CHAT_MEMBERS_PRIVATE: int = 2
    MAX_GLOBAL_CHATS_PER_USER: int = 10
    
    # Posts
    MAX_POST_LENGTH: int = 2000
    MAX_POSTS_PER_PAGE: int = 20
    FEED_CACHE_TTL: int = 300  # 5 minutos
    
    # Notifications
    MAX_NOTIFICATIONS_PER_PAGE: int = 50
    NOTIFICATION_RETENTION_DAYS: int = 30
    
    # Friends
    MAX_FRIENDS_COUNT: int = 5000
    MAX_FRIEND_REQUESTS_PER_DAY: int = 50
    
    # Recommendations
    RECOMMENDATION_BATCH_SIZE: int = 20
    RECOMMENDATION_UPDATE_INTERVAL: int = 3600  # 1 hora
    
    # Email (opcional para verificaciones futuras)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = "noreply@socialstream.com"
    
    # Seguridad adicional
    CORS_ORIGINS: List[str] = ["*"]
    CSP_ENABLED: bool = False
    HSTS_ENABLED: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Permitir campos extra

# Instancia global de configuración
settings = Settings()