"""
Router principal que agrupa todos los endpoints
"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.chat import router as chat_router
from app.api.v1.posts import router as posts_router
from app.api.v1.streams import router as streams_router
from app.api.v1.friends import router as friends_router
from app.api.v1.notifications import router as notifications_router

api_router = APIRouter()

# Incluir todos los routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(chat_router)
api_router.include_router(posts_router)
api_router.include_router(streams_router)
api_router.include_router(friends_router)
api_router.include_router(notifications_router)

@api_router.get("/")
async def api_root():
    """Raíz de la API v1"""
    return {
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "chat": "/api/v1/chat",
            "posts": "/api/v1/posts",
            "streams": "/api/v1/streams",
            "friends": "/api/v1/friends",
            "notifications": "/api/v1/notifications"
        }
    }