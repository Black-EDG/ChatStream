"""
Endpoints de gestión de amigos
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, List
from app.services.friend_service import FriendService
from app.core.dependencies import get_friend_service, get_current_user
from app.schemas.user import FriendRequestSchema

router = APIRouter(prefix="/friends", tags=["👥 Amigos"])

@router.post(
    "/request/{user_id}",
    summary="Enviar solicitud",
    description="Envía una solicitud de amistad a un usuario."
)
async def send_friend_request(
    user_id: str,
    request_data: Optional[FriendRequestSchema] = None,
    current_user: dict = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Enviar solicitud de amistad"""
    message = request_data.message if request_data and request_data.message else None
    success, msg = await friend_service.send_friend_request(
        from_user_id=current_user["_id"],
        to_user_id=user_id,
        message=message
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    return {"message": msg}


@router.post(
    "/accept/{request_id}",
    summary="Aceptar solicitud",
    description="Acepta una solicitud de amistad pendiente."
)
async def accept_friend_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Aceptar solicitud de amistad"""
    success = await friend_service.accept_friend_request(request_id, current_user["_id"])
    if not success:
        raise HTTPException(status_code=400, detail="Error al aceptar solicitud")
    
    return {"message": "Solicitud aceptada, ahora son amigos"}


@router.post(
    "/reject/{request_id}",
    summary="Rechazar solicitud",
    description="Rechaza una solicitud de amistad pendiente."
)
async def reject_friend_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Rechazar solicitud de amistad"""
    success = await friend_service.reject_friend_request(request_id, current_user["_id"])
    if not success:
        raise HTTPException(status_code=400, detail="Error al rechazar solicitud")
    
    return {"message": "Solicitud rechazada"}


@router.get(
    "/requests",
    summary="Solicitudes pendientes",
    description="Obtiene las solicitudes de amistad pendientes."
)
async def get_pending_requests(
    type: str = Query("received", pattern="^(received|sent)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Obtener solicitudes pendientes"""
    if type == "received":
        requests = await friend_service.get_pending_requests(current_user["_id"], page, limit)
    else:
        requests = await friend_service.get_sent_requests(current_user["_id"], page, limit)
    
    return requests


@router.get(
    "/",
    summary="Lista de amigos",
    description="Obtiene la lista de amigos del usuario."
)
async def get_friends_list(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Obtener lista de amigos"""
    friends = await friend_service.get_friends(current_user["_id"], page, limit)
    return friends


@router.delete(
    "/{friend_id}",
    summary="Eliminar amigo",
    description="Elimina a un usuario de tu lista de amigos."
)
async def remove_friend(
    friend_id: str,
    current_user: dict = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Eliminar amigo"""
    success = await friend_service.remove_friend(current_user["_id"], friend_id)
    if not success:
        raise HTTPException(status_code=400, detail="Error al eliminar amigo")
    
    return {"message": "Amigo eliminado"}


@router.get(
    "/suggestions",
    summary="Sugerencias de amigos",
    description="Obtiene sugerencias de posibles amigos."
)
async def get_friend_suggestions(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Obtener sugerencias de amigos"""
    suggestions = await friend_service.get_friend_suggestions(current_user["_id"], limit)
    return suggestions