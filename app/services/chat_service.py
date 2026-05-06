"""
Servicio de chat y mensajería
"""
from typing import Optional, List, Dict
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.models.message import Message, Chat, MessageMedia, MessageReaction
import logging

logger = logging.getLogger(__name__)

class ChatService:
    """Servicio completo de gestión de chats y mensajes"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_or_create_global_chat(self, country: str, language: str) -> dict:
        """Obtener o crear chat global por país e idioma"""
        try:
            chat = await self.db.chats.find_one({
                "type": "global",
                "country": country,
                "language": language
            })
            
            if not chat:
                chat_data = {
                    "type": "global",
                    "name": f"Global {country} - {language}",
                    "language": language,
                    "country": country,
                    "participants": [],
                    "participants_ids": [],
                    "message_count": 0,
                    "unread_count": {},
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_active": True
                }
                result = await self.db.chats.insert_one(chat_data)
                chat = await self.db.chats.find_one({"_id": result.inserted_id})
            
            if chat:
                chat["_id"] = str(chat["_id"])
            
            return chat
            
        except Exception as e:
            logger.error(f"Error obteniendo chat global: {e}")
            return None
    
    async def get_or_create_private_chat(self, user1_id: str, user2_id: str) -> dict:
        """Obtener o crear chat privado entre dos usuarios"""
        try:
            participants = sorted([user1_id, user2_id])
            
            # Buscar chat existente
            chat = await self.db.chats.find_one({
                "type": "private",
                "participants_ids": {"$all": participants, "$size": 2}
            })
            
            if not chat:
                # Obtener datos de usuarios
                user1 = await self.db.users.find_one({"_id": ObjectId(user1_id)})
                user2 = await self.db.users.find_one({"_id": ObjectId(user2_id)})
                
                chat_data = {
                    "type": "private",
                    "name": f"{user1['username']} & {user2['username']}" if user1 and user2 else "Chat Privado",
                    "participants": [
                        {
                            "user_id": user1_id,
                            "username": user1["username"] if user1 else "Unknown",
                            "profile_picture": user1.get("profile_picture") if user1 else None,
                            "joined_at": datetime.utcnow(),
                            "is_admin": False
                        },
                        {
                            "user_id": user2_id,
                            "username": user2["username"] if user2 else "Unknown",
                            "profile_picture": user2.get("profile_picture") if user2 else None,
                            "joined_at": datetime.utcnow(),
                            "is_admin": False
                        }
                    ],
                    "participants_ids": participants,
                    "message_count": 0,
                    "unread_count": {user1_id: 0, user2_id: 0},
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_active": True
                }
                result = await self.db.chats.insert_one(chat_data)
                chat = await self.db.chats.find_one({"_id": result.inserted_id})
            
            if chat:
                chat["_id"] = str(chat["_id"])
            
            return chat
            
        except Exception as e:
            logger.error(f"Error creando chat privado: {e}")
            return None
    
    async def get_chat_by_id(self, chat_id: str) -> Optional[dict]:
        """Obtener chat por ID"""
        try:
            chat = await self.db.chats.find_one({"_id": ObjectId(chat_id)})
            if chat:
                chat["_id"] = str(chat["_id"])
            return chat
        except:
            return None
    
    async def get_user_chats(self, user_id: str, page: int = 1, limit: int = 20) -> dict:
        """Obtener todos los chats de un usuario"""
        try:
            skip = (page - 1) * limit
            
            # Buscar chats donde el usuario es participante o son globales
            filter_query = {
                "$or": [
                    {"participants_ids": user_id},
                    {"type": "global"},
                    {"type": "group", "participants_ids": user_id}
                ],
                "is_active": True
            }
            
            cursor = self.db.chats.find(filter_query)\
                .sort("updated_at", -1)\
                .skip(skip)\
                .limit(limit)
            
            chats = []
            async for chat in cursor:
                chat["_id"] = str(chat["_id"])
                
                # Calcular unread count para este usuario
                unread = chat.get("unread_count", {}).get(user_id, 0)
                chat["unread_messages"] = unread
                
                chats.append(chat)
            
            total = await self.db.chats.count_documents(filter_query)
            
            return {
                "chats": chats,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo chats: {e}")
            return {"chats": [], "total": 0, "page": page, "pages": 0}
    
    async def send_message(
        self,
        chat_id: str,
        sender_id: str,
        sender_username: str,
        content: str,
        message_type: str = "text",
        media_url: Optional[str] = None,
        reply_to: Optional[str] = None,
        thumbnail_url: Optional[str] = None
    ) -> Optional[dict]:
        """Enviar un mensaje a un chat"""
        try:
            # Verificar que el chat existe
            chat = await self.db.chats.find_one({"_id": ObjectId(chat_id)})
            if not chat:
                return None
            
            # Crear contenido del mensaje
            message_content = {
                "type": message_type,
                "content": content,
                "thumbnail_url": thumbnail_url
            }
            
            if media_url:
                message_content["content"] = media_url
            
            # Preparar reply si existe
            reply_data = None
            if reply_to:
                replied_msg = await self.db.messages.find_one({"_id": ObjectId(reply_to)})
                if replied_msg:
                    reply_data = {
                        "message_id": reply_to,
                        "content_preview": replied_msg.get("content", {}).get("content", "")[:50],
                        "sender_username": replied_msg.get("sender_username", "")
                    }
            
            # Crear mensaje
            message = {
                "chat_id": chat_id,
                "sender_id": sender_id,
                "sender_username": sender_username,
                "content": message_content,
                "reply_to": reply_data,
                "reactions": [],
                "reactions_count": 0,
                "is_edited": False,
                "is_deleted": False,
                "is_read": False,
                "read_by": [sender_id],
                "delivered_to": [],
                "timestamp": datetime.utcnow()
            }
            
            result = await self.db.messages.insert_one(message)
            message["_id"] = str(result.inserted_id)
            
            # Actualizar chat
            update_data = {
                "last_message": message,
                "updated_at": datetime.utcnow(),
                "$inc": {"message_count": 1}
            }
            
            # Incrementar unread count para todos excepto el sender
            for participant_id in chat.get("participants_ids", []):
                if participant_id != sender_id:
                    update_data[f"unread_count.{participant_id}"] = \
                        chat.get("unread_count", {}).get(participant_id, 0) + 1
            
            await self.db.chats.update_one(
                {"_id": ObjectId(chat_id)},
                {
                    "$set": {
                        "last_message": message,
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {
                        "message_count": 1,
                        **{f"unread_count.{p}": 1 for p in chat.get("participants_ids", []) if p != sender_id}
                    }
                }
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
            return None
    
    async def get_chat_messages(
        self,
        chat_id: str,
        page: int = 1,
        limit: int = 50
    ) -> dict:
        """Obtener mensajes de un chat con paginación"""
        try:
            skip = (page - 1) * limit
            
            cursor = self.db.messages.find(
                {"chat_id": chat_id, "is_deleted": False}
            ).sort("timestamp", -1).skip(skip).limit(limit)
            
            messages = []
            async for msg in cursor:
                msg["_id"] = str(msg["_id"])
                messages.append(msg)
            
            total = await self.db.messages.count_documents(
                {"chat_id": chat_id, "is_deleted": False}
            )
            
            return {
                "messages": messages,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return {"messages": [], "total": 0, "page": page, "pages": 0}
    
    async def add_reaction(
        self,
        message_id: str,
        user_id: str,
        reaction_type: str
    ) -> bool:
        """Agregar reacción a un mensaje"""
        try:
            # Verificar si ya reaccionó
            message = await self.db.messages.find_one({
                "_id": ObjectId(message_id),
                "reactions.user_id": user_id
            })
            
            if message:
                # Actualizar reacción existente
                await self.db.messages.update_one(
                    {
                        "_id": ObjectId(message_id),
                        "reactions.user_id": user_id
                    },
                    {
                        "$set": {
                            "reactions.$.reaction_type": reaction_type,
                            "reactions.$.updated_at": datetime.utcnow()
                        }
                    }
                )
                return True
            
            # Agregar nueva reacción
            result = await self.db.messages.update_one(
                {"_id": ObjectId(message_id)},
                {
                    "$push": {
                        "reactions": {
                            "user_id": user_id,
                            "reaction_type": reaction_type,
                            "created_at": datetime.utcnow()
                        }
                    },
                    "$inc": {"reactions_count": 1}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error agregando reacción: {e}")
            return False
    
    async def edit_message(
        self,
        message_id: str,
        user_id: str,
        new_content: str
    ) -> Optional[dict]:
        """Editar un mensaje propio"""
        try:
            result = await self.db.messages.find_one_and_update(
                {
                    "_id": ObjectId(message_id),
                    "sender_id": user_id,
                    "is_deleted": False
                },
                {
                    "$set": {
                        "content.content": new_content,
                        "is_edited": True,
                        "edited_at": datetime.utcnow()
                    }
                },
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
            
            return result
            
        except Exception as e:
            logger.error(f"Error editando mensaje: {e}")
            return None
    
    async def delete_message(self, message_id: str, user_id: str) -> bool:
        """Eliminar un mensaje (soft delete)"""
        try:
            result = await self.db.messages.update_one(
                {
                    "_id": ObjectId(message_id),
                    "sender_id": user_id
                },
                {
                    "$set": {
                        "is_deleted": True,
                        "deleted_at": datetime.utcnow(),
                        "content.content": "Mensaje eliminado"
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error eliminando mensaje: {e}")
            return False
    
    async def mark_messages_read(
        self,
        chat_id: str,
        user_id: str,
        message_ids: List[str]
    ) -> bool:
        """Marcar mensajes como leídos"""
        try:
            object_ids = [ObjectId(mid) for mid in message_ids]
            
            await self.db.messages.update_many(
                {
                    "_id": {"$in": object_ids},
                    "chat_id": chat_id
                },
                {
                    "$addToSet": {"read_by": user_id},
                    "$set": {"is_read": True}
                }
            )
            
            # Resetear unread count del usuario en el chat
            await self.db.chats.update_one(
                {"_id": ObjectId(chat_id)},
                {"$set": {f"unread_count.{user_id}": 0}}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error marcando mensajes leídos: {e}")
            return False
    
    async def create_group_chat(
        self,
        name: str,
        participant_ids: List[str],
        created_by: str,
        description: Optional[str] = None
    ) -> Optional[dict]:
        """Crear un chat grupal"""
        try:
            # Obtener datos de participantes
            participants = []
            for user_id in participant_ids:
                user = await self.db.users.find_one({"_id": ObjectId(user_id)})
                if user:
                    participants.append({
                        "user_id": user_id,
                        "username": user["username"],
                        "profile_picture": user.get("profile_picture"),
                        "joined_at": datetime.utcnow(),
                        "is_admin": user_id == created_by,
                        "is_muted": False
                    })
            
            chat_data = {
                "type": "group",
                "name": name,
                "description": description,
                "participants": participants,
                "participants_ids": participant_ids,
                "created_by": created_by,
                "message_count": 0,
                "unread_count": {uid: 0 for uid in participant_ids},
                "max_participants": 100,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True
            }
            
            result = await self.db.chats.insert_one(chat_data)
            
            chat = await self.db.chats.find_one({"_id": result.inserted_id})
            if chat:
                chat["_id"] = str(chat["_id"])
            
            return chat
            
        except Exception as e:
            logger.error(f"Error creando grupo: {e}")
            return None
    
    async def search_messages(
        self,
        query: str,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """Buscar mensajes por contenido"""
        try:
            filter_query = {
                "content.content": {"$regex": query, "$options": "i"},
                "is_deleted": False
            }
            
            if chat_id:
                filter_query["chat_id"] = chat_id
            
            if user_id:
                filter_query["sender_id"] = user_id
            
            skip = (page - 1) * limit
            
            cursor = self.db.messages.find(filter_query)\
                .sort("timestamp", -1)\
                .skip(skip)\
                .limit(limit)
            
            messages = []
            async for msg in cursor:
                msg["_id"] = str(msg["_id"])
                messages.append(msg)
            
            total = await self.db.messages.count_documents(filter_query)
            
            return {
                "messages": messages,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error buscando mensajes: {e}")
            return {"messages": [], "total": 0, "page": page, "pages": 0}