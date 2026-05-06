"""
Endpoints de notificaciones
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.services.notification_service import NotificationService
from app.core.dependencies import get_notification_service, get_current_user

router = APIRouter(prefix="/notifications", tags=["🔔 Notificaciones"])

@router.get(
    "/",
    summary="Mis notificaciones",
    description="Obtiene las notificaciones del usuario actual."
)
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    unread_only: bool = Query(False),
    type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Obtener notificaciones"""
    notifications = await notification_service.get_notifications(
        user_id=current_user["_id"],
        page=page,
        limit=limit,
        unread_only=unread_only,
        type=type
    )
    return notifications

@router.get(
    "/count",
    summary="Contador de notificaciones",
    description="Obtiene el número de notificaciones no leídas."
)
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Obtener contador de no leídas"""
    count = await notification_service.get_unread_count(current_user["_id"])
    return {"unread_count": count}

@router.post(
    "/{notification_id}/read",
    summary="Marcar como leída",
    description="Marca una notificación como leída."
)
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Marcar notificación como leída"""
    await notification_service.mark_as_read(notification_id, current_user["_id"])
    return {"message": "Notificación marcada como leída"}

@router.post(
    "/read-all",
    summary="Marcar todas como leídas",
    description="Marca todas las notificaciones como leídas."
)
async def mark_all_as_read(
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Marcar todas como leídas"""
    await notification_service.mark_all_as_read(current_user["_id"])
    return {"message": "Todas las notificaciones marcadas como leídas"}

@router.delete(
    "/{notification_id}",
    summary="Eliminar notificación",
    description="Elimina una notificación específica."
)
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Eliminar notificación"""
    await notification_service.delete_notification(notification_id, current_user["_id"])
    return {"message": "Notificación eliminada"}