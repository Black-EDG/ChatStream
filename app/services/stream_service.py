"""
Servicio de streaming en vivo
"""
from typing import Optional, List, Dict
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.core.security import SecurityManager
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class StreamService:
    """Servicio completo de streaming"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.security = SecurityManager()
    
    async def create_stream(
        self,
        user_id: str,
        username: str,
        title: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: List[str] = [],
        language: Optional[str] = None,
        resolution: str = "1080p",
        fps: int = 30,
        bitrate: int = 6000,
        is_recorded: bool = False,
        chat_config: Optional[dict] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Optional[dict]:
        """Crear un nuevo stream"""
        try:
            # Generar IDs únicos
            stream_id = str(ObjectId())
            room_id = self.security.generate_room_id()
            stream_key = self.security.generate_stream_key(user_id, stream_id)
            
            stream_data = {
                "_id": ObjectId(stream_id),
                "user_id": user_id,
                "username": username,
                "title": title,
                "description": description,
                "category": category,
                "tags": tags,
                "language": language,
                "stream_key": stream_key,
                "rtmp_url": f"{settings.RTMP_SERVER_URL}/{stream_key}",
                "room_id": room_id,
                "resolution": resolution,
                "fps": fps,
                "bitrate": bitrate,
                "status": "scheduled" if scheduled_at else "created",
                "viewers": [],
                "current_viewers": 0,
                "metrics": {
                    "peak_viewers": 0,
                    "total_viewers": 0,
                    "average_watch_time": 0.0,
                    "total_watch_time": 0,
                    "likes_count": 0,
                    "comments_count": 0,
                    "shares_count": 0
                },
                "chat_config": chat_config or {
                    "enabled": True,
                    "slow_mode": 0,
                    "subscribers_only": False,
                    "followers_only": False,
                    "min_account_age_days": 0
                },
                "thumbnail_url": None,
                "is_recorded": is_recorded,
                "recording_url": None,
                "duration": 0,
                "is_monetized": False,
                "donations_enabled": False,
                "scheduled_at": scheduled_at,
                "started_at": None,
                "ended_at": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await self.db.streams.insert_one(stream_data)
            stream_data["_id"] = str(stream_data["_id"])
            
            # Actualizar contador de streams del usuario
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"stats.total_streams": 1}}
            )
            
            return stream_data
            
        except Exception as e:
            logger.error(f"Error creando stream: {e}")
            return None
    
    async def get_stream_by_id(self, stream_id: str) -> Optional[dict]:
        """Obtener stream por ID"""
        try:
            stream = await self.db.streams.find_one({"_id": ObjectId(stream_id)})
            if stream:
                stream["_id"] = str(stream["_id"])
                # No exponer stream_key completo
                stream["stream_key"] = stream["stream_key"][:8] + "..."
            return stream
        except:
            return None
    
    async def start_stream(self, stream_id: str, user_id: str) -> bool:
        """Iniciar transmisión en vivo"""
        try:
            result = await self.db.streams.update_one(
                {
                    "_id": ObjectId(stream_id),
                    "user_id": user_id,
                    "status": {"$in": ["created", "scheduled"]}
                },
                {
                    "$set": {
                        "status": "live",
                        "started_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error iniciando stream: {e}")
            return False
    
    async def end_stream(self, stream_id: str, user_id: str) -> bool:
        """Finalizar transmisión"""
        try:
            stream = await self.db.streams.find_one({"_id": ObjectId(stream_id)})
            if not stream:
                return False
            
            # Calcular duración
            duration = 0
            if stream.get("started_at"):
                duration = int((datetime.utcnow() - stream["started_at"]).total_seconds())
            
            result = await self.db.streams.update_one(
                {
                    "_id": ObjectId(stream_id),
                    "user_id": user_id,
                    "status": "live"
                },
                {
                    "$set": {
                        "status": "ended",
                        "ended_at": datetime.utcnow(),
                        "duration": duration,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Actualizar estadísticas del usuario
                hours = duration / 3600
                await self.db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$inc": {"stats.total_streaming_hours": hours}}
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error finalizando stream: {e}")
            return False
    
    async def update_stream(
        self,
        stream_id: str,
        user_id: str,
        update_data: dict
    ) -> Optional[dict]:
        """Actualizar configuración del stream"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.db.streams.find_one_and_update(
                {
                    "_id": ObjectId(stream_id),
                    "user_id": user_id
                },
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                result["stream_key"] = result["stream_key"][:8] + "..."
            
            return result
            
        except Exception as e:
            logger.error(f"Error actualizando stream: {e}")
            return None
    
    async def join_stream(self, stream_id: str, user_id: str) -> bool:
        """Unirse como espectador a un stream"""
        try:
            # Verificar que el stream está en vivo
            stream = await self.db.streams.find_one({
                "_id": ObjectId(stream_id),
                "status": "live"
            })
            
            if not stream:
                return False
            
            # Verificar si ya es espectador
            viewers = stream.get("viewers", [])
            if any(v["user_id"] == user_id for v in viewers):
                return True  # Ya está viendo
            
            # Agregar espectador
            viewer = {
                "user_id": user_id,
                "username": "viewer",  # Se actualizará después
                "joined_at": datetime.utcnow(),
                "left_at": None,
                "watch_time": 0,
                "is_subscribed": False
            }
            
            await self.db.streams.update_one(
                {"_id": ObjectId(stream_id)},
                {
                    "$push": {"viewers": viewer},
                    "$inc": {"current_viewers": 1},
                    "$max": {"metrics.peak_viewers": stream.get("current_viewers", 0) + 1}
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error uniéndose a stream: {e}")
            return False
    
    async def leave_stream(self, stream_id: str, user_id: str) -> bool:
        """Salir de un stream como espectador"""
        try:
            await self.db.streams.update_one(
                {"_id": ObjectId(stream_id)},
                {
                    "$set": {"viewers.$[elem].left_at": datetime.utcnow()},
                    "$inc": {"current_viewers": -1}
                },
                array_filters=[{"elem.user_id": user_id, "elem.left_at": None}]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error saliendo de stream: {e}")
            return False
    
    async def get_live_streams(
        self,
        page: int = 1,
        limit: int = 20,
        category: Optional[str] = None,
        language: Optional[str] = None,
        country: Optional[str] = None
    ) -> dict:
        """Obtener streams en vivo"""
        try:
            filter_query = {"status": "live"}
            
            if category:
                filter_query["category"] = category
            if language:
                filter_query["language"] = language
            
            skip = (page - 1) * limit
            
            cursor = self.db.streams.find(filter_query)\
                .sort([("current_viewers", -1), ("started_at", -1)])\
                .skip(skip)\
                .limit(limit)
            
            streams = []
            async for stream in cursor:
                stream["_id"] = str(stream["_id"])
                stream["stream_key"] = stream["stream_key"][:8] + "..."
                streams.append(stream)
            
            total = await self.db.streams.count_documents(filter_query)
            
            return {
                "streams": streams,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo streams en vivo: {e}")
            return {"streams": [], "total": 0, "page": page, "pages": 0}
    
    async def get_viewers(
        self,
        stream_id: str,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """Obtener espectadores de un stream"""
        try:
            stream = await self.db.streams.find_one(
                {"_id": ObjectId(stream_id)},
                {"viewers": 1}
            )
            
            if not stream:
                return {"viewers": [], "total": 0}
            
            viewers = stream.get("viewers", [])
            active_viewers = [v for v in viewers if v.get("left_at") is None]
            
            total = len(active_viewers)
            skip = (page - 1) * limit
            paginated = active_viewers[skip:skip + limit]
            
            return {
                "viewers": paginated,
                "total": total,
                "current_viewers": total
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo espectadores: {e}")
            return {"viewers": [], "total": 0}
    
    async def can_send_message(self, stream_id: str, user_id: str) -> bool:
        """Verificar si un usuario puede enviar mensajes en el chat del stream"""
        try:
            stream = await self.db.streams.find_one({"_id": ObjectId(stream_id)})
            if not stream:
                return False
            
            chat_config = stream.get("chat_config", {})
            
            # Verificar si el chat está habilitado
            if not chat_config.get("enabled", True):
                return False
            
            # Verificar followers only
            if chat_config.get("followers_only", False):
                is_follower = await self.db.followers.find_one({
                    "follower_id": user_id,
                    "following_id": stream["user_id"]
                })
                if not is_follower:
                    return False
            
            # Verificar edad de cuenta
            min_age = chat_config.get("min_account_age_days", 0)
            if min_age > 0:
                user = await self.db.users.find_one({"_id": ObjectId(user_id)})
                if user:
                    account_age = (datetime.utcnow() - user["created_at"]).days
                    if account_age < min_age:
                        return False
            
            return True
            
        except:
            return True  # En caso de error, permitir
    
    async def add_stream_reaction(
        self,
        stream_id: str,
        user_id: str,
        reaction_type: str
    ) -> bool:
        """Agregar reacción a un stream"""
        try:
            await self.db.streams.update_one(
                {"_id": ObjectId(stream_id)},
                {"$inc": {f"metrics.{reaction_type}s_count": 1}}
            )
            return True
        except:
            return False