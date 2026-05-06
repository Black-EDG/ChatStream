"""
Punto de entrada principal de la aplicación FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.core.database import Database
from app.core.redis_client import RedisClient
from app.api.v1.router import api_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manejar eventos de inicio y apagado de la aplicación
    """
    # Startup
    logger.info("🚀 Iniciando Social Stream Backend...")
    
    # Crear directorios de uploads
    os.makedirs("uploads/posts", exist_ok=True)
    os.makedirs("uploads/avatars", exist_ok=True)
    os.makedirs("uploads/streams", exist_ok=True)
    
    # Conectar a MongoDB
    await Database.connect_db(settings.MONGODB_URL, settings.MONGODB_DB_NAME)
    
    # Conectar a Redis
    await RedisClient.connect_redis(settings.REDIS_URL)
    
    logger.info(f"✅ Aplicación iniciada en modo: {settings.ENVIRONMENT}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Apagando aplicación...")
    await Database.close_db()
    await RedisClient.close_redis()
    logger.info("✅ Aplicación apagada correctamente")

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="""
    Backend completo para red social con:
    * 🔐 Autenticación JWT
    * 💬 Chat en tiempo real con WebSockets
    * 📹 Streaming en vivo con WebRTC
    * 👥 Sistema de amigos y seguidores
    * 📝 Publicaciones y feed de noticias
    """,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware personalizado
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Incluir routers de API
app.include_router(api_router, prefix="/api/v1")

# ✅ SERVIR ARCHIVOS ESTÁTICOS (IMÁGENES, VIDEOS, ETC)
# Debe ir DESPUÉS de los routers de API
app.mount("/media", StaticFiles(directory="uploads"), name="media")

@app.get("/")
async def root():
    """Endpoint raíz para health check"""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
async def health_check():
    """Health check detallado"""
    try:
        db = Database.get_db()
        await db.command('ping')
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    try:
        redis = RedisClient.get_redis()
        await redis.ping()
        redis_status = "connected"
    except:
        redis_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "cache": redis_status,
        "timestamp": "2024-01-01T00:00:00Z"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )