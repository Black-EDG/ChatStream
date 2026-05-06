"""
Manejador WebSocket para chat
"""
from fastapi import WebSocket, WebSocketDisconnect
from app.api.websocket.manager import manager
from app.services.chat_service import ChatService
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class ChatWebSocket:
    """Manejador de conexiones WebSocket de chat"""
    
    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service
    
    async def handle_chat_connection(
        self,
        websocket: WebSocket,
        chat_id: str,
        user_id: str
    ):
        """Manejar conexión WebSocket de chat"""
        await manager.connect(websocket, user_id)
        await manager.join_chat(chat_id, user_id, websocket)
        
        try:
            while True:
                # Recibir mensaje del cliente
                data = await websocket.receive_json()
                
                # Procesar según tipo de mensaje
                message_type = data.get("type", "message")
                
                if message_type == "message":
                    await self._handle_message(chat_id, user_id, data)
                    
                elif message_type == "typing":
                    await self._handle_typing(chat_id, user_id, data)
                    
                elif message_type == "reaction":
                    await self._handle_reaction(chat_id, user_id, data)
                    
                elif message_type == "read_receipt":
                    await self._handle_read_receipt(chat_id, user_id, data)
                    
                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
        except WebSocketDisconnect:
            logger.info(f"Usuario {user_id} desconectado del chat {chat_id}")
        except Exception as e:
            logger.error(f"Error en WebSocket chat: {e}")
        finally:
            await manager.leave_chat(chat_id, user_id)
            await manager.disconnect(user_id)
    
    async def _handle_message(self, chat_id: str, user_id: str, data: dict):
        """Procesar nuevo mensaje"""
        try:
            content = data.get("content", "")
            message_type = data.get("message_type", "text")
            media_url = data.get("media_url")
            reply_to = data.get("reply_to")
            
            # Guardar mensaje en base de datos
            message = await self.chat_service.send_message(
                chat_id=chat_id,
                sender_id=user_id,
                sender_username=data.get("username", ""),
                content=content,
                message_type=message_type,
                media_url=media_url,
                reply_to=reply_to
            )
            
            if message:
                # Transmitir a todos en el chat
                await manager.broadcast_to_chat(chat_id, {
                    "type": "new_message",
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
    
    async def _handle_typing(self, chat_id: str, user_id: str, data: dict):
        """Procesar estado de escritura"""
        is_typing = data.get("is_typing", False)
        username = data.get("username", "")
        
        await manager.update_typing_status(
            chat_id, user_id, username, is_typing
        )
    
    async def _handle_reaction(self, chat_id: str, user_id: str, data: dict):
        """Procesar reacción a mensaje"""
        message_id = data.get("message_id")
        reaction_type = data.get("reaction_type", "like")
        
        success = await self.chat_service.add_reaction(
            message_id, user_id, reaction_type
        )
        
        if success:
            await manager.broadcast_to_chat(chat_id, {
                "type": "message_reaction",
                "message_id": message_id,
                "user_id": user_id,
                "reaction_type": reaction_type,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_read_receipt(self, chat_id: str, user_id: str, data: dict):
        """Procesar confirmación de lectura"""
        message_ids = data.get("message_ids", [])
        
        if message_ids:
            await self.chat_service.mark_messages_read(
                chat_id, user_id, message_ids
            )
            
            await manager.broadcast_to_chat(chat_id, {
                "type": "messages_read",
                "user_id": user_id,
                "message_ids": message_ids,
                "timestamp": datetime.utcnow().isoformat()
            })