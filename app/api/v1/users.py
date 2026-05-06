"""
Endpoints de usuarios y perfiles
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File
from typing import Optional, List
from app.services.user_service import UserService
from app.services.friend_service import FriendService
from app.core.dependencies import (
    get_user_service, get_friend_service,
    get_current_user, get_optional_current_user
)
from app.schemas.user import UserResponse, UserUpdate, FollowRequest, UserSearch, FriendRequestSchema
from app.models.user import User

router = APIRouter(prefix="/users", tags=["👥 Usuarios"])

# ==========================================
# ENDPOINTS SIN {user_id} (RUTAS FIJAS PRIMERO)
# ==========================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener mi perfil",
    description="Obtiene el perfil completo del usuario autenticado."
)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Obtener perfil del usuario actual"""
    user = await user_service.get_user_by_id(current_user["_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@router.put(
    "/me",
    response_model=UserResponse,
    summary="Actualizar mi perfil",
    description="Actualiza los datos del perfil del usuario autenticado."
)
async def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Actualizar perfil del usuario actual"""
    update_dict = update_data.model_dump(exclude_unset=True) if hasattr(update_data, 'model_dump') else update_data.dict(exclude_unset=True)
    updated_user = await user_service.update_user(current_user["_id"], update_dict)
    if not updated_user:
        raise HTTPException(status_code=400, detail="Error al actualizar perfil")
    return updated_user

@router.post(
    "/me/avatar",
    summary="Subir foto de perfil",
    description="Sube una imagen como foto de perfil."
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Subir avatar del usuario"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes")
    
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La imagen no debe superar 5MB")
    
    result = await user_service.upload_avatar(current_user["_id"], file)
    return result

@router.post(
    "/me/cover",
    summary="Subir foto de portada",
    description="Sube una imagen como foto de portada del perfil."
)
async def upload_cover(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Subir portada del usuario"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes")
    
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La imagen no debe superar 5MB")
    
    result = await user_service.upload_cover(current_user["_id"], file)
    return result

@router.get(
    "/search",
    summary="Buscar usuarios",
    description="Busca usuarios por nombre, username o ubicación."
)
async def search_users(
    q: str = Query(default="", min_length=0, description="Término de búsqueda"),
    country: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_service: UserService = Depends(get_user_service)
):
    """Buscar usuarios"""
    results = await user_service.search_users(q, country, page, limit)
    return results


# ==========================================
# ENDPOINTS CON {user_id} (RUTAS DINÁMICAS DESPUÉS)
# ==========================================

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Obtener perfil de usuario",
    description="Obtiene el perfil público de cualquier usuario."
)
async def get_user_profile(
    user_id: str,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Obtener perfil de un usuario específico"""
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@router.post(
    "/{user_id}/follow",
    summary="Seguir usuario",
    description="Comienza a seguir a un usuario."
)
async def follow_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Seguir a un usuario"""
    if user_id == current_user["_id"]:
        raise HTTPException(status_code=400, detail="No puedes seguirte a ti mismo")
    
    success = await user_service.follow_user(current_user["_id"], user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Error al seguir usuario")
    
    return {"message": "Ahora sigues a este usuario"}

@router.post(
    "/{user_id}/unfollow",
    summary="Dejar de seguir",
    description="Deja de seguir a un usuario."
)
async def unfollow_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Dejar de seguir a un usuario"""
    success = await user_service.unfollow_user(current_user["_id"], user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Error al dejar de seguir")
    
    return {"message": "Has dejado de seguir a este usuario"}

@router.post(
    "/{user_id}/like",
    summary="Dar like al perfil",
    description="Da like al perfil de un usuario."
)
async def like_user_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Dar like al perfil de un usuario"""
    if user_id == current_user["_id"]:
        raise HTTPException(status_code=400, detail="No puedes darte like a ti mismo")
    
    success = await user_service.like_user(current_user["_id"], user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Ya has dado like a este perfil")
    
    return {"message": "Like agregado al perfil"}

@router.get(
    "/{user_id}/followers",
    summary="Listar seguidores",
    description="Obtiene la lista de seguidores de un usuario."
)
async def get_user_followers(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_service: UserService = Depends(get_user_service)
):
    """Obtener seguidores de un usuario"""
    followers = await user_service.get_followers(user_id, page, limit)
    return followers

@router.get(
    "/{user_id}/following",
    summary="Listar seguidos",
    description="Obtiene la lista de usuarios que sigue."
)
async def get_user_following(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_service: UserService = Depends(get_user_service)
):
    """Obtener usuarios que sigue"""
    following = await user_service.get_following(user_id, page, limit)
    return following

@router.post(
    "/{user_id}/friend-request",
    summary="Enviar solicitud de amistad",
    description="Envía una solicitud de amistad a otro usuario."
)
async def send_friend_request(
    user_id: str,
    request_data: FriendRequestSchema,
    current_user: dict = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Enviar solicitud de amistad"""
    if user_id == current_user["_id"]:
        raise HTTPException(status_code=400, detail="No puedes enviarte solicitud a ti mismo")
    
    success, message = await friend_service.send_friend_request(
        from_user_id=current_user["_id"],
        to_user_id=user_id,
        message=request_data.message
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}