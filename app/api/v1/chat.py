"""
Endpoints de chat y mensajería
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query, WebSocket
from typing import Optional, List
from app.services.chat_service import ChatService
from app.core.dependencies import get_chat_service, get_current_user, get_db
from app.schemas.message import (
    SendMessageRequest, MessageResponse, ChatCreateSchema,
    ChatResponse, ChatListResponse, MessageSearchSchema,
    MessageReactionSchema
)
from app.api.websocket.chat_ws import ChatWebSocket

router = APIRouter(prefix="/chat", tags=["💬 Chat"])

@router.get(
    "/global",
    summary="Obtener chat global",
    description="Obtiene o crea un chat global según país e idioma."
)
async def get_global_chat(
    country: str = Query(..., min_length=2),
    language: str = Query("es"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Obtener chat global"""
    chat = await chat_service.get_or_create_global_chat(country, language)
    return chat

@router.post(
    "/private",
    response_model=ChatResponse,
    summary="Crear chat privado",
    description="Crea un chat privado con otro usuario."
)
async def create_private_chat(
    user_id: str = Query(..., description="ID del otro usuario"),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Crear o obtener chat privado"""
    if user_id == current_user["_id"]:
        raise HTTPException(status_code=400, detail="No puedes chatear contigo mismo")
    
    chat = await chat_service.get_or_create_private_chat(current_user["_id"], user_id)
    return chat

@router.get(
    "/",
    response_model=ChatListResponse,
    summary="Listar mis chats",
    description="Obtiene todos los chats del usuario actual."
)
async def get_my_chats(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Obtener chats del usuario"""
    chats = await chat_service.get_user_chats(current_user["_id"], page, limit)
    return chats

@router.get(
    "/{chat_id}",
    response_model=ChatResponse,
    summary="Obtener chat específico",
    description="Obtiene los detalles de un chat."
)
async def get_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Obtener chat por ID"""
    chat = await chat_service.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    return chat

@router.get(
    "/{chat_id}/messages",
    summary="Obtener mensajes",
    description="Obtiene los mensajes de un chat con paginación."
)
async def get_chat_messages(
    chat_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Obtener mensajes de un chat"""
    messages = await chat_service.get_chat_messages(chat_id, page, limit)
    return messages  # Devuelve el dict directamente

@router.post(
    "/{chat_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensaje",
    description="Envía un mensaje a un chat."
)
async def send_message(
    chat_id: str,
    message_data: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Enviar mensaje a un chat"""
    message = await chat_service.send_message(
        chat_id=chat_id,
        sender_id=current_user["_id"],
        sender_username=current_user["username"],
        content=message_data.content,
        message_type=message_data.message_type,
        media_url=message_data.media_url,
        reply_to=message_data.reply_to
    )
    
    if not message:
        raise HTTPException(status_code=400, detail="Error al enviar mensaje")
    
    return message

@router.post(
    "/messages/{message_id}/reaction",
    summary="Reaccionar a mensaje",
    description="Agrega una reacción a un mensaje."
)
async def react_to_message(
    message_id: str,
    reaction: MessageReactionSchema,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Reaccionar a un mensaje"""
    success = await chat_service.add_reaction(
        message_id=message_id,
        user_id=current_user["_id"],
        reaction_type=reaction.reaction_type
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Ya has reaccionado a este mensaje")
    
    return {"message": "Reacción agregada"}

@router.put(
    "/messages/{message_id}",
    response_model=MessageResponse,
    summary="Editar mensaje",
    description="Edita el contenido de un mensaje propio."
)
async def edit_message(
    message_id: str,
    new_content: str = Query(..., min_length=1, max_length=5000),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Editar mensaje propio"""
    message = await chat_service.edit_message(
        message_id=message_id,
        user_id=current_user["_id"],
        new_content=new_content
    )
    
    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado o no autorizado")
    
    return message

@router.delete(
    "/messages/{message_id}",
    summary="Eliminar mensaje",
    description="Elimina un mensaje propio (soft delete)."
)
async def delete_message(
    message_id: str,
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Eliminar mensaje"""
    success = await chat_service.delete_message(message_id, current_user["_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    
    return {"message": "Mensaje eliminado"}

@router.post(
    "/messages/read",
    summary="Marcar mensajes como leídos",
    description="Marca mensajes como leídos en un chat."
)
async def mark_messages_read(
    chat_id: str = Query(...),
    message_ids: List[str] = Query(...),
    current_user: dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Marcar mensajes como leídos"""
    await chat_service.mark_messages_read(chat_id, current_user["_id"], message_ids)
    return {"message": "Mensajes marcados como leídos"}

# WebSocket para chat
@router.websocket("/ws/{chat_id}")
async def websocket_chat(
    websocket: WebSocket,
    chat_id: str,
    token: str = Query(...),
    db=Depends(get_db)
):
    """
    Conexión WebSocket para chat en tiempo real.
    
    Parámetros:
    - chat_id: ID del chat
    - token: Token JWT de autenticación
    """
    from app.core.dependencies import get_current_user_ws
    from app.api.websocket.manager import manager
    
    # Autenticar usuario
    user = await get_current_user_ws(websocket, token)
    if not user:
        return
    
    chat_service = ChatService(db)
    chat_ws = ChatWebSocket(chat_service)
    
    await chat_ws.handle_chat_connection(websocket, chat_id, user["_id"])