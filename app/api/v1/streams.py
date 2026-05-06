"""
Endpoints de streaming en vivo
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query, WebSocket
from typing import Optional, List
from app.services.stream_service import StreamService
from app.core.dependencies import get_stream_service, get_current_user, get_db
from app.schemas.stream import (
    CreateStreamRequest, UpdateStreamRequest,
    StreamResponse, StreamFilter
)

router = APIRouter(prefix="/streams", tags=["📹 Streaming"])

@router.post(
    "/",
    response_model=StreamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear stream",
    description="Configura un nuevo stream en vivo."
)
async def create_stream(
    stream_data: CreateStreamRequest,
    current_user: dict = Depends(get_current_user),
    stream_service: StreamService = Depends(get_stream_service)
):
    """Crear nuevo stream"""
    stream = await stream_service.create_stream(
        user_id=current_user["_id"],
        username=current_user["username"],
        title=stream_data.title,
        description=stream_data.description,
        category=stream_data.category,
        tags=stream_data.tags,
        language=stream_data.language,
        resolution=stream_data.resolution,
        fps=stream_data.fps,
        bitrate=stream_data.bitrate,
        is_recorded=stream_data.is_recorded,
        chat_config=stream_data.chat_config
    )
    
    if not stream:
        raise HTTPException(status_code=400, detail="Error al crear stream")
    
    return stream

@router.get(
    "/live",
    response_model=dict,
    summary="Streams en vivo",
    description="Obtiene la lista de streams actualmente en vivo."
)
async def get_live_streams(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    category: Optional[str] = None,
    language: Optional[str] = None,
    country: Optional[str] = None,
    stream_service: StreamService = Depends(get_stream_service)
):
    """Obtener streams en vivo"""
    streams = await stream_service.get_live_streams(
        page=page,
        limit=limit,
        category=category,
        language=language,
        country=country
    )
    return streams

@router.get(
    "/{stream_id}",
    response_model=StreamResponse,
    summary="Obtener stream",
    description="Obtiene los detalles de un stream específico."
)
async def get_stream(
    stream_id: str,
    stream_service: StreamService = Depends(get_stream_service)
):
    """Obtener stream por ID"""
    stream = await stream_service.get_stream_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream no encontrado")
    return stream

@router.put(
    "/{stream_id}",
    response_model=StreamResponse,
    summary="Actualizar stream",
    description="Actualiza la configuración de un stream."
)
async def update_stream(
    stream_id: str,
    update_data: UpdateStreamRequest,
    current_user: dict = Depends(get_current_user),
    stream_service: StreamService = Depends(get_stream_service)
):
    """Actualizar stream"""
    stream = await stream_service.update_stream(
        stream_id=stream_id,
        user_id=current_user["_id"],
        update_data=update_data.dict(exclude_unset=True)
    )
    
    if not stream:
        raise HTTPException(status_code=404, detail="Stream no encontrado o no autorizado")
    
    return stream

@router.post(
    "/{stream_id}/start",
    summary="Iniciar stream",
    description="Inicia la transmisión en vivo."
)
async def start_stream(
    stream_id: str,
    current_user: dict = Depends(get_current_user),
    stream_service: StreamService = Depends(get_stream_service)
):
    """Iniciar transmisión"""
    success = await stream_service.start_stream(stream_id, current_user["_id"])
    if not success:
        raise HTTPException(status_code=400, detail="Error al iniciar stream")
    
    return {"message": "Stream iniciado", "status": "live"}

@router.post(
    "/{stream_id}/end",
    summary="Finalizar stream",
    description="Finaliza la transmisión en vivo."
)
async def end_stream(
    stream_id: str,
    current_user: dict = Depends(get_current_user),
    stream_service: StreamService = Depends(get_stream_service)
):
    """Finalizar stream"""
    success = await stream_service.end_stream(stream_id, current_user["_id"])
    if not success:
        raise HTTPException(status_code=400, detail="Error al finalizar stream")
    
    return {"message": "Stream finalizado", "status": "ended"}

@router.post(
    "/{stream_id}/join",
    summary="Unirse a stream",
    description="Unirse como espectador a un stream en vivo."
)
async def join_stream(
    stream_id: str,
    current_user: dict = Depends(get_current_user),
    stream_service: StreamService = Depends(get_stream_service)
):
    """Unirse a stream como espectador"""
    success = await stream_service.join_stream(stream_id, current_user["_id"])
    if not success:
        raise HTTPException(status_code=400, detail="Error al unirse al stream")
    
    return {"message": "Te has unido al stream"}

@router.post(
    "/{stream_id}/leave",
    summary="Salir de stream",
    description="Salir como espectador de un stream."
)
async def leave_stream(
    stream_id: str,
    current_user: dict = Depends(get_current_user),
    stream_service: StreamService = Depends(get_stream_service)
):
    """Salir de stream"""
    await stream_service.leave_stream(stream_id, current_user["_id"])
    return {"message": "Has salido del stream"}

@router.get(
    "/{stream_id}/viewers",
    summary="Espectadores del stream",
    description="Obtiene la lista de espectadores actuales."
)
async def get_stream_viewers(
    stream_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    stream_service: StreamService = Depends(get_stream_service)
):
    """Obtener espectadores del stream"""
    viewers = await stream_service.get_viewers(stream_id, page, limit)
    return viewers

# WebSocket para stream chat
@router.websocket("/{stream_id}/chat")
async def stream_chat_websocket(
    websocket: WebSocket,
    stream_id: str,
    token: str = Query(...),
    db=Depends(get_db)
):
    """
    WebSocket para chat de stream en vivo.
    """
    from app.core.dependencies import get_current_user_ws
    from app.api.websocket.stream_ws import StreamWebSocket
    
    user = await get_current_user_ws(websocket, token)
    if not user:
        return
    
    stream_service = StreamService(db)
    stream_ws = StreamWebSocket(stream_service)
    
    await stream_ws.handle_stream_chat(websocket, stream_id, user["_id"])