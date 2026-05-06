"""
Manejador WebSocket para streaming
"""
from fastapi import WebSocket, WebSocketDisconnect
from app.api.websocket.manager import manager
from app.services.stream_service import StreamService
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class StreamWebSocket:
    """Manejador de conexiones WebSocket de stream"""
    
    def __init__(self, stream_service: StreamService):
        self.stream_service = stream_service
    
    async def handle_stream_chat(
        self,
        websocket: WebSocket,
        stream_id: str,
        user_id: str
    ):
        """Manejar chat de stream en vivo"""
        await manager.connect(websocket, user_id)
        await manager.join_stream(stream_id, user_id, websocket)
        
        try:
            while True:
                data = await websocket.receive_json()
                message_type = data.get("type", "message")
                
                if message_type == "message":
                    await self._handle_chat_message(stream_id, user_id, data)
                    
                elif message_type == "reaction":
                    await self._handle_stream_reaction(stream_id, user_id, data)
                    
                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "viewer_count": manager.get_stream_viewers(stream_id),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
        except WebSocketDisconnect:
            logger.info(f"Espectador {user_id} salió del stream {stream_id}")
        except Exception as e:
            logger.error(f"Error en WebSocket stream: {e}")
        finally:
            await manager.leave_stream(stream_id, user_id)
            await manager.disconnect(user_id)
    
    async def handle_stream_broadcast(
        self,
        websocket: WebSocket,
        stream_id: str,
        user_id: str
    ):
        """Manejar conexión del streamer (broadcaster)"""
        await manager.connect(websocket, user_id)
        
        try:
            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "stream_status":
                    await manager.broadcast_to_stream(stream_id, {
                        "type": "stream_update",
                        "status": data.get("status"),
                        "viewer_count": manager.get_stream_viewers(stream_id),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "viewer_count": manager.get_stream_viewers(stream_id),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
        except WebSocketDisconnect:
            logger.info(f"Streamer {user_id} desconectado del stream {stream_id}")
        except Exception as e:
            logger.error(f"Error en WebSocket broadcaster: {e}")
        finally:
            await manager.disconnect(user_id)
    
    async def _handle_chat_message(self, stream_id: str, user_id: str, data: dict):
        """Procesar mensaje del chat del stream"""
        content = data.get("content", "")
        
        # Validar que el usuario puede enviar mensajes (según configuración del chat)
        can_send = await self.stream_service.can_send_message(
            stream_id, user_id
        )
        
        if not can_send:
            # Notificar solo al usuario que no puede enviar mensajes
            if user_id in manager.active_connections:
                await manager.active_connections[user_id].send_json({
                    "type": "error",
                    "message": "No tienes permiso para enviar mensajes en este chat"
                })
            return
        
        # Transmitir mensaje a todos los espectadores
        await manager.broadcast_to_stream(stream_id, {
            "type": "chat_message",
            "user_id": user_id,
            "username": data.get("username", ""),
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_stream_reaction(self, stream_id: str, user_id: str, data: dict):
        """Procesar reacción al stream"""
        reaction_type = data.get("reaction_type", "like")
        
        # Guardar reacción
        await self.stream_service.add_stream_reaction(
            stream_id, user_id, reaction_type
        )
        
        # Transmitir reacción
        await manager.broadcast_to_stream(stream_id, {
            "type": "stream_reaction",
            "user_id": user_id,
            "username": data.get("username", ""),
            "reaction_type": reaction_type,
            "timestamp": datetime.utcnow().isoformat()
        })