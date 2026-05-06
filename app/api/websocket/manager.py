"""
Gestor de conexiones WebSocket
"""
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Gestor centralizado de conexiones WebSocket"""
    
    def __init__(self):
        # Conexiones activas por usuario
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Salas de chat: {chat_id: {user_id: WebSocket}}
        self.chat_rooms: Dict[str, Dict[str, WebSocket]] = {}
        
        # Salas de stream: {stream_id: {user_id: WebSocket}}
        self.stream_rooms: Dict[str, Dict[str, WebSocket]] = {}
        
        # Estados de usuarios
        self.user_statuses: Dict[str, Dict[str, Any]] = {}
        
        # Lock para operaciones thread-safe
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Registrar nueva conexión WebSocket"""
        await websocket.accept()
        
        async with self._lock:
            # Cerrar conexión anterior si existe
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].close()
                except:
                    pass
            
            self.active_connections[user_id] = websocket
            self.user_statuses[user_id] = {
                "status": "online",
                "last_seen": datetime.utcnow(),
                "connection_time": datetime.utcnow()
            }
        
        logger.info(f"Usuario {user_id} conectado via WebSocket")
        await self.broadcast_user_status(user_id, "online")
    
    async def disconnect(self, user_id: str):
        """Desconectar usuario y limpiar recursos"""
        async with self._lock:
            # Remover de conexiones activas
            if user_id in self.active_connections:
                del self.active_connections[user_id]
            
            # Remover de todas las salas de chat
            for chat_id in list(self.chat_rooms.keys()):
                if user_id in self.chat_rooms.get(chat_id, {}):
                    del self.chat_rooms[chat_id][user_id]
                    if not self.chat_rooms[chat_id]:
                        del self.chat_rooms[chat_id]
            
            # Remover de todas las salas de stream
            for stream_id in list(self.stream_rooms.keys()):
                if user_id in self.stream_rooms.get(stream_id, {}):
                    del self.stream_rooms[stream_id][user_id]
                    if not self.stream_rooms[stream_id]:
                        del self.stream_rooms[stream_id]
            
            # Actualizar estado
            if user_id in self.user_statuses:
                self.user_statuses[user_id]["status"] = "offline"
                self.user_statuses[user_id]["last_seen"] = datetime.utcnow()
        
        logger.info(f"Usuario {user_id} desconectado")
        await self.broadcast_user_status(user_id, "offline")
    
    async def join_chat(self, chat_id: str, user_id: str, websocket: WebSocket):
        """Unirse a sala de chat"""
        async with self._lock:
            if chat_id not in self.chat_rooms:
                self.chat_rooms[chat_id] = {}
            self.chat_rooms[chat_id][user_id] = websocket
        
        # Notificar a otros
        await self.broadcast_to_chat(chat_id, {
            "type": "user_joined",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=user_id)
    
    async def leave_chat(self, chat_id: str, user_id: str):
        """Salir de sala de chat"""
        async with self._lock:
            if chat_id in self.chat_rooms and user_id in self.chat_rooms[chat_id]:
                del self.chat_rooms[chat_id][user_id]
                if not self.chat_rooms[chat_id]:
                    del self.chat_rooms[chat_id]
        
        await self.broadcast_to_chat(chat_id, {
            "type": "user_left",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def join_stream(self, stream_id: str, user_id: str, websocket: WebSocket):
        """Unirse a sala de stream"""
        async with self._lock:
            if stream_id not in self.stream_rooms:
                self.stream_rooms[stream_id] = {}
            self.stream_rooms[stream_id][user_id] = websocket
        
        await self.broadcast_to_stream(stream_id, {
            "type": "viewer_joined",
            "user_id": user_id,
            "viewer_count": len(self.stream_rooms.get(stream_id, {})),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def leave_stream(self, stream_id: str, user_id: str):
        """Salir de sala de stream"""
        async with self._lock:
            if stream_id in self.stream_rooms and user_id in self.stream_rooms[stream_id]:
                del self.stream_rooms[stream_id][user_id]
                if not self.stream_rooms[stream_id]:
                    del self.stream_rooms[stream_id]
        
        await self.broadcast_to_stream(stream_id, {
            "type": "viewer_left",
            "user_id": user_id,
            "viewer_count": len(self.stream_rooms.get(stream_id, {})),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Enviar mensaje a usuario específico"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error enviando mensaje personal a {user_id}: {e}")
                await self.disconnect(user_id)
    
    async def broadcast_to_chat(
        self,
        chat_id: str,
        message: dict,
        exclude_user: Optional[str] = None
    ):
        """Transmitir mensaje a todos en un chat"""
        if chat_id in self.chat_rooms:
            disconnected = []
            for user_id, websocket in self.chat_rooms[chat_id].items():
                if user_id != exclude_user:
                    try:
                        await websocket.send_json(message)
                    except Exception:
                        disconnected.append(user_id)
            
            # Limpiar conexiones muertas
            for user_id in disconnected:
                await self.disconnect(user_id)
    
    async def broadcast_to_stream(
        self,
        stream_id: str,
        message: dict,
        exclude_user: Optional[str] = None
    ):
        """Transmitir mensaje a todos en un stream"""
        if stream_id in self.stream_rooms:
            disconnected = []
            for user_id, websocket in self.stream_rooms[stream_id].items():
                if user_id != exclude_user:
                    try:
                        await websocket.send_json(message)
                    except Exception:
                        disconnected.append(user_id)
            
            for user_id in disconnected:
                await self.disconnect(user_id)
    
    async def broadcast_user_status(self, user_id: str, status: str):
        """Notificar cambio de estado a amigos"""
        # Implementar lógica para notificar solo a amigos
        pass
    
    async def update_typing_status(
        self,
        chat_id: str,
        user_id: str,
        username: str,
        is_typing: bool
    ):
        """Notificar estado de escritura"""
        await self.broadcast_to_chat(chat_id, {
            "type": "typing_status",
            "user_id": user_id,
            "username": username,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=user_id)
    
    def get_user_status(self, user_id: str) -> Optional[dict]:
        """Obtener estado de usuario"""
        return self.user_statuses.get(user_id)
    
    def get_online_count(self) -> int:
        """Obtener número de usuarios en línea"""
        return len(self.active_connections)
    
    def get_chat_viewers(self, chat_id: str) -> int:
        """Obtener número de usuarios en un chat"""
        return len(self.chat_rooms.get(chat_id, {}))
    
    def get_stream_viewers(self, stream_id: str) -> int:
        """Obtener número de espectadores en stream"""
        return len(self.stream_rooms.get(stream_id, {}))

# Instancia global
manager = ConnectionManager()