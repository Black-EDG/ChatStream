"""
Dependencias de FastAPI para inyección
"""
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.core.database import Database
from app.core.redis_client import RedisClient
from app.core.security import SecurityManager
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.chat_service import ChatService
from app.services.post_service import PostService
from app.services.stream_service import StreamService
from app.services.friend_service import FriendService
from app.services.notification_service import NotificationService
from app.services.recommendation_service import RecommendationService
from bson import ObjectId

# Esquema OAuth2 para Swagger UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    description="Ingresa el token JWT obtenido en el login"
)

async def get_db():
    """Obtener instancia de la base de datos"""
    return Database.get_db()

async def get_redis():
    """Obtener instancia de Redis"""
    return RedisClient.get_redis()

async def get_auth_service(db=Depends(get_db)):
    """Obtener servicio de autenticación"""
    return AuthService(db)

async def get_user_service(db=Depends(get_db)):
    """Obtener servicio de usuarios"""
    return UserService(db)

async def get_chat_service(db=Depends(get_db)):
    """Obtener servicio de chat"""
    return ChatService(db)

async def get_post_service(db=Depends(get_db)):
    """Obtener servicio de publicaciones"""
    return PostService(db)

async def get_stream_service(db=Depends(get_db)):
    """Obtener servicio de streaming"""
    return StreamService(db)

async def get_friend_service(db=Depends(get_db)):
    """Obtener servicio de amigos"""
    return FriendService(db)

async def get_notification_service(db=Depends(get_db)):
    """Obtener servicio de notificaciones"""
    return NotificationService(db)

async def get_recommendation_service(db=Depends(get_db)):
    """Obtener servicio de recomendaciones"""
    return RecommendationService(db)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db)
) -> dict:
    """
    Obtener usuario actual desde token JWT
    
    Args:
        token: Token JWT de autorización
        db: Instancia de base de datos
        
    Returns:
        Datos del usuario autenticado
        
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Validar token
    payload = SecurityManager.validate_access_token(token)
    if not payload:
        raise credentials_exception
    
    # Obtener user_id del token
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    # Buscar usuario en base de datos
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise credentials_exception
    
    if not user:
        raise credentials_exception
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada"
        )
    
    # Remover datos sensibles
    user["_id"] = str(user["_id"])
    user.pop("hashed_password", None)
    
    return user

async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = None
) -> Optional[dict]:
    """
    Obtener usuario actual para WebSocket
    
    Args:
        websocket: Conexión WebSocket
        token: Token JWT (opcional, puede venir en query params)
        
    Returns:
        Datos del usuario o None
    """
    # Intentar obtener token de los query params
    if not token:
        token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=4001, reason="Token no proporcionado")
        return None
    
    # Validar token
    payload = SecurityManager.validate_access_token(token)
    if not payload:
        await websocket.close(code=4002, reason="Token inválido")
        return None
    
    # Obtener usuario
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4003, reason="Token sin usuario")
        return None
    
    try:
        db = Database.get_db()
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            await websocket.close(code=4004, reason="Usuario no encontrado")
            return None
        
        user["_id"] = str(user["_id"])
        user.pop("hashed_password", None)
        
        return user
        
    except Exception as e:
        await websocket.close(code=4005, reason="Error interno")
        return None

async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db=Depends(get_db)
) -> Optional[dict]:
    """
    Obtener usuario actual de forma opcional (no requiere autenticación)
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None