"""
Servicio de gestión de amigos
"""
from typing import Optional, List, Tuple
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class FriendService:
    """Servicio completo de amigos"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def send_friend_request(
        self,
        from_user_id: str,
        to_user_id: str,
        message: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Enviar solicitud de amistad"""
        try:
            # Validaciones
            if from_user_id == to_user_id:
                return False, "No puedes enviarte una solicitud a ti mismo"
            
            # Verificar que el destinatario existe
            to_user = await self.db.users.find_one({"_id": ObjectId(to_user_id)})
            if not to_user:
                return False, "Usuario no encontrado"
            
            # Verificar que no sean amigos ya
            from_user = await self.db.users.find_one({"_id": ObjectId(from_user_id)})
            if from_user and to_user_id in from_user.get("friends", []):
                return False, "Ya son amigos"
            
            # Verificar si ya existe una solicitud pendiente
            existing = await self.db.friend_requests.find_one({
                "$or": [
                    {
                        "from_user_id": from_user_id,
                        "to_user_id": to_user_id,
                        "status": "pending"
                    },
                    {
                        "from_user_id": to_user_id,
                        "to_user_id": from_user_id,
                        "status": "pending"
                    }
                ]
            })
            
            if existing:
                if existing["from_user_id"] == from_user_id:
                    return False, "Ya enviaste una solicitud a este usuario"
                else:
                    # El otro usuario ya envió solicitud, aceptar automáticamente
                    await self.accept_friend_request(str(existing["_id"]), from_user_id)
                    return True, "Solicitud aceptada automáticamente"
            
            # Verificar límite de solicitudes diarias
            today = datetime.utcnow().replace(hour=0, minute=0, second=0)
            daily_count = await self.db.friend_requests.count_documents({
                "from_user_id": from_user_id,
                "created_at": {"$gte": today}
            })
            
            if daily_count >= 50:  # Máximo 50 solicitudes por día
                return False, "Has alcanzado el límite diario de solicitudes"
            
            # Verificar máximo de amigos
            if from_user and len(from_user.get("friends", [])) >= 5000:
                return False, "Has alcanzado el límite máximo de amigos"
            
            if to_user and len(to_user.get("friends", [])) >= 5000:
                return False, "El usuario ha alcanzado el límite máximo de amigos"
            
            # Crear solicitud
            request_data = {
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "status": "pending",
                "message": message,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await self.db.friend_requests.insert_one(request_data)
            
            # Enviar notificación
            await self._send_notification(
                to_user_id=to_user_id,
                from_user_id=from_user_id,
                notification_type="friend_request",
                message=f"Tienes una nueva solicitud de amistad"
            )
            
            return True, "Solicitud enviada correctamente"
            
        except Exception as e:
            logger.error(f"Error enviando solicitud: {e}")
            return False, "Error al enviar la solicitud"
    
    async def accept_friend_request(self, request_id: str, user_id: str) -> bool:
        """Aceptar solicitud de amistad"""
        try:
            # Buscar la solicitud
            request = await self.db.friend_requests.find_one({
                "_id": ObjectId(request_id),
                "to_user_id": user_id,
                "status": "pending"
            })
            
            if not request:
                return False
            
            # Actualizar solicitud
            await self.db.friend_requests.update_one(
                {"_id": ObjectId(request_id)},
                {
                    "$set": {
                        "status": "accepted",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Agregar a listas de amigos
            from_user_id = request["from_user_id"]
            to_user_id = request["to_user_id"]
            
            await self.db.users.update_one(
                {"_id": ObjectId(from_user_id)},
                {
                    "$addToSet": {"friends": to_user_id},
                    "$inc": {"friends_count": 1}
                }
            )
            
            await self.db.users.update_one(
                {"_id": ObjectId(to_user_id)},
                {
                    "$addToSet": {"friends": from_user_id},
                    "$inc": {"friends_count": 1}
                }
            )
            
            # Notificar
            await self._send_notification(
                to_user_id=from_user_id,
                from_user_id=to_user_id,
                notification_type="friend_accepted",
                message="Tu solicitud de amistad fue aceptada"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error aceptando solicitud: {e}")
            return False
    
    async def reject_friend_request(self, request_id: str, user_id: str) -> bool:
        """Rechazar solicitud de amistad"""
        try:
            result = await self.db.friend_requests.update_one(
                {
                    "_id": ObjectId(request_id),
                    "to_user_id": user_id,
                    "status": "pending"
                },
                {
                    "$set": {
                        "status": "rejected",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error rechazando solicitud: {e}")
            return False
    
    async def remove_friend(self, user_id: str, friend_id: str) -> bool:
        """Eliminar amigo"""
        try:
            # Remover de ambas listas
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$pull": {"friends": friend_id},
                    "$inc": {"friends_count": -1}
                }
            )
            
            await self.db.users.update_one(
                {"_id": ObjectId(friend_id)},
                {
                    "$pull": {"friends": user_id},
                    "$inc": {"friends_count": -1}
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando amigo: {e}")
            return False
    
    async def get_friends(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """Obtener lista de amigos"""
        try:
            user = await self.db.users.find_one(
                {"_id": ObjectId(user_id)},
                {"friends": 1}
            )
            
            if not user:
                return {"friends": [], "total": 0}
            
            friends_ids = user.get("friends", [])
            total = len(friends_ids)
            
            # Paginar
            skip = (page - 1) * limit
            paginated_ids = friends_ids[skip:skip + limit]
            
            # Obtener datos de amigos
            friends = []
            for friend_id in paginated_ids:
                friend = await self.db.users.find_one(
                    {"_id": ObjectId(friend_id)},
                    {"hashed_password": 0}
                )
                if friend:
                    friend["_id"] = str(friend["_id"])
                    friends.append(friend)
            
            return {
                "friends": friends,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo amigos: {e}")
            return {"friends": [], "total": 0}
    
    async def get_pending_requests(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """Obtener solicitudes pendientes recibidas"""
        try:
            skip = (page - 1) * limit
            
            cursor = self.db.friend_requests.find(
                {
                    "to_user_id": user_id,
                    "status": "pending"
                }
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            requests = []
            async for req in cursor:
                req["_id"] = str(req["_id"])
                
                # Obtener datos del remitente
                sender = await self.db.users.find_one(
                    {"_id": ObjectId(req["from_user_id"])},
                    {"hashed_password": 0}
                )
                if sender:
                    sender["_id"] = str(sender["_id"])
                    req["from_user"] = sender
                
                requests.append(req)
            
            total = await self.db.friend_requests.count_documents({
                "to_user_id": user_id,
                "status": "pending"
            })
            
            return {
                "requests": requests,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo solicitudes: {e}")
            return {"requests": [], "total": 0}
    
    async def get_sent_requests(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """Obtener solicitudes enviadas"""
        try:
            skip = (page - 1) * limit
            
            cursor = self.db.friend_requests.find(
                {
                    "from_user_id": user_id,
                    "status": "pending"
                }
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            requests = []
            async for req in cursor:
                req["_id"] = str(req["_id"])
                requests.append(req)
            
            total = await self.db.friend_requests.count_documents({
                "from_user_id": user_id,
                "status": "pending"
            })
            
            return {
                "requests": requests,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo solicitudes enviadas: {e}")
            return {"requests": [], "total": 0}
    
    async def get_friend_suggestions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[dict]:
        """Obtener sugerencias de amigos"""
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return []
            
            friends = set(user.get("friends", []))
            friends.add(user_id)  # Excluirse a sí mismo
            
            # Buscar amigos de amigos
            pipeline = [
                {
                    "$match": {
                        "_id": {"$in": [ObjectId(fid) for fid in friends if fid != user_id]}
                    }
                },
                {"$unwind": "$friends"},
                {
                    "$match": {
                        "friends": {"$nin": list(friends)}
                    }
                },
                {"$group": {"_id": "$friends", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            
            cursor = self.db.users.aggregate(pipeline)
            
            suggestions = []
            async for doc in cursor:
                suggested_user = await self.db.users.find_one(
                    {"_id": ObjectId(doc["_id"])},
                    {"hashed_password": 0}
                )
                if suggested_user:
                    suggested_user["_id"] = str(suggested_user["_id"])
                    suggested_user["mutual_friends"] = doc["count"]
                    suggestions.append(suggested_user)
            
            # Si no hay suficientes, agregar usuarios populares
            if len(suggestions) < limit:
                popular_users = await self.db.users.find(
                    {
                        "_id": {
                            "$nin": [ObjectId(fid) for fid in friends]
                        }
                    },
                    {"hashed_password": 0}
                ).sort("followers_count", -1).limit(limit - len(suggestions)).to_list(None)
                
                for user in popular_users:
                    user["_id"] = str(user["_id"])
                    if user not in suggestions:
                        suggestions.append(user)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error obteniendo sugerencias: {e}")
            return []
    
    async def _send_notification(
        self,
        to_user_id: str,
        from_user_id: str,
        notification_type: str,
        message: str
    ):
        """Enviar notificación (método interno)"""
        try:
            from_user = await self.db.users.find_one(
                {"_id": ObjectId(from_user_id)},
                {"username": 1}
            )
            
            notification = {
                "user_id": to_user_id,
                "from_user_id": from_user_id,
                "from_username": from_user["username"] if from_user else "Usuario",
                "type": notification_type,
                "title": notification_type.replace("_", " ").title(),
                "message": message,
                "is_read": False,
                "is_seen": False,
                "priority": 0,
                "created_at": datetime.utcnow()
            }
            
            await self.db.notifications.insert_one(notification)
            
        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")