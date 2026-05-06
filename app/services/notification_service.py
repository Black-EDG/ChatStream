"""
Servicio de notificaciones
"""
from typing import Optional, List
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Servicio completo de notificaciones"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        from_user_id: Optional[str] = None,
        from_username: Optional[str] = None,
        action: Optional[dict] = None,
        priority: int = 0,
        image_url: Optional[str] = None
    ) -> Optional[str]:
        """Crear una notificación"""
        try:
            notification = {
                "user_id": user_id,
                "from_user_id": from_user_id,
                "from_username": from_username,
                "type": type,
                "title": title,
                "message": message,
                "icon": None,
                "image_url": image_url,
                "action": action,
                "is_read": False,
                "is_seen": False,
                "read_at": None,
                "priority": priority,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=30)
            }
            
            result = await self.db.notifications.insert_one(notification)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creando notificación: {e}")
            return None
    
    async def get_notifications(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False,
        type: Optional[str] = None
    ) -> dict:
        """Obtener notificaciones del usuario"""
        try:
            filter_query = {
                "user_id": user_id,
                "created_at": {
                    "$gte": datetime.utcnow() - timedelta(days=30)
                }
            }
            
            if unread_only:
                filter_query["is_read"] = False
            
            if type:
                filter_query["type"] = type
            
            skip = (page - 1) * limit
            
            cursor = self.db.notifications.find(filter_query)\
                .sort("created_at", -1)\
                .skip(skip)\
                .limit(limit)
            
            notifications = []
            async for notif in cursor:
                notif["_id"] = str(notif["_id"])
                notifications.append(notif)
            
            total = await self.db.notifications.count_documents(filter_query)
            
            return {
                "notifications": notifications,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo notificaciones: {e}")
            return {"notifications": [], "total": 0, "page": page, "pages": 0}
    
    async def get_unread_count(self, user_id: str) -> int:
        """Obtener contador de notificaciones no leídas"""
        try:
            count = await self.db.notifications.count_documents({
                "user_id": user_id,
                "is_read": False,
                "created_at": {
                    "$gte": datetime.utcnow() - timedelta(days=30)
                }
            })
            
            return count
            
        except:
            return 0
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Marcar notificación como leída"""
        try:
            result = await self.db.notifications.update_one(
                {
                    "_id": ObjectId(notification_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "is_read": True,
                        "is_seen": True,
                        "read_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except:
            return False
    
    async def mark_all_as_read(self, user_id: str) -> bool:
        """Marcar todas las notificaciones como leídas"""
        try:
            await self.db.notifications.update_many(
                {
                    "user_id": user_id,
                    "is_read": False
                },
                {
                    "$set": {
                        "is_read": True,
                        "is_seen": True,
                        "read_at": datetime.utcnow()
                    }
                }
            )
            
            return True
            
        except:
            return False
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Eliminar una notificación"""
        try:
            result = await self.db.notifications.delete_one({
                "_id": ObjectId(notification_id),
                "user_id": user_id
            })
            
            return result.deleted_count > 0
            
        except:
            return False
    
    async def delete_old_notifications(self, days: int = 30) -> int:
        """Eliminar notificaciones antiguas (limpieza)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.db.notifications.delete_many({
                "created_at": {"$lt": cutoff_date}
            })
            
            return result.deleted_count
            
        except:
            return 0
    
    async def notify_followers(
        self,
        user_id: str,
        username: str,
        notification_type: str,
        message: str,
        exclude_ids: List[str] = []
    ) -> None:
        """Notificar a todos los seguidores de un usuario"""
        try:
            # Obtener IDs de seguidores
            cursor = self.db.followers.find(
                {"following_id": user_id},
                {"follower_id": 1}
            )
            
            follower_ids = []
            async for follower in cursor:
                fid = follower["follower_id"]
                if fid not in exclude_ids:
                    follower_ids.append(fid)
            
            # Crear notificaciones en lote
            notifications = []
            now = datetime.utcnow()
            
            for fid in follower_ids:
                notifications.append({
                    "user_id": fid,
                    "from_user_id": user_id,
                    "from_username": username,
                    "type": notification_type,
                    "title": notification_type.replace("_", " ").title(),
                    "message": message,
                    "is_read": False,
                    "is_seen": False,
                    "priority": 1,
                    "created_at": now,
                    "expires_at": now + timedelta(days=30)
                })
            
            if notifications:
                await self.db.notifications.insert_many(notifications)
                
        except Exception as e:
            logger.error(f"Error notificando seguidores: {e}")