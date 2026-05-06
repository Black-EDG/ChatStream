"""
Servicio de publicaciones y feed
"""
from typing import Optional, List, Dict
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from fastapi import UploadFile
import logging
import os
import aiofiles

logger = logging.getLogger(__name__)

class PostService:
    """Servicio completo de publicaciones"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_post(
        self,
        user_id: str,
        username: str,
        profile_picture: Optional[str],
        content: str,
        media: List[dict] = [],
        visibility: str = "public",
        tags: List[str] = [],
        hashtags: List[str] = [],
        location: Optional[dict] = None,
        is_nsfw: bool = False,
        has_spoiler: bool = False,
        scheduled_at: Optional[datetime] = None
    ) -> Optional[dict]:
        """Crear una nueva publicación"""
        try:
            post_data = {
                "user_id": user_id,
                "username": username,
                "profile_picture": profile_picture,
                "content": content,
                "media": media,
                "location": location,
                "visibility": visibility,
                "tags": tags,
                "hashtags": hashtags,
                "likes": [],
                "likes_count": 0,
                "comments": [],
                "comments_count": 0,
                "shares_count": 0,
                "views_count": 0,
                "bookmarks_count": 0,
                "is_nsfw": is_nsfw,
                "has_spoiler": has_spoiler,
                "is_pinned": False,
                "is_shared": False,
                "language": "es",
                "scheduled_at": scheduled_at,
                "created_at": datetime.utcnow() if not scheduled_at else scheduled_at,
                "updated_at": None
            }
            
            result = await self.db.posts.insert_one(post_data)
            post_data["_id"] = str(result.inserted_id)
            
            # Actualizar contador de posts del usuario
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"stats.total_posts": 1}}
            )
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error creando publicación: {e}")
            return None
    
    async def get_post_by_id(self, post_id: str) -> Optional[dict]:
        """Obtener publicación por ID"""
        try:
            post = await self.db.posts.find_one({"_id": ObjectId(post_id)})
            if post:
                post["_id"] = str(post["_id"])
            return post
        except:
            return None
    
    async def get_feed(
        self,
        user_id: Optional[str] = None,
        feed_type: str = "following",
        page: int = 1,
        limit: int = 20,
        country: Optional[str] = None,
        language: Optional[str] = None
    ) -> dict:
        """Obtener feed de publicaciones"""
        try:
            skip = (page - 1) * limit
            filter_query = {"visibility": "public", "is_nsfw": False}
            
            if feed_type == "following" and user_id:
                # Obtener IDs de usuarios que sigue
                following_cursor = self.db.followers.find({"follower_id": user_id})
                following_ids = []
                async for follow in following_cursor:
                    following_ids.append(follow["following_id"])
                
                following_ids.append(user_id)  # Incluir propias publicaciones
                filter_query["user_id"] = {"$in": following_ids}
            
            elif feed_type == "explore":
                # Publicaciones populares recientes
                pass
            
            elif feed_type == "trending":
                # Publicaciones con más likes en últimas 24h
                filter_query["created_at"] = {
                    "$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)
                }
                sort_by = [("likes_count", -1)]
            
            if country:
                filter_query["location.country"] = country
            
            if language:
                filter_query["language"] = language
            
            # Ordenar por fecha por defecto
            sort_by = sort_by if 'sort_by' in locals() else [("created_at", -1)]
            
            cursor = self.db.posts.find(filter_query)\
                .sort(sort_by)\
                .skip(skip)\
                .limit(limit)
            
            posts = []
            async for post in cursor:
                post["_id"] = str(post["_id"])
                
                # Verificar si el usuario dio like
                if user_id and user_id in post.get("likes", []):
                    post["is_liked"] = True
                else:
                    post["is_liked"] = False
                
                posts.append(post)
            
            total = await self.db.posts.count_documents(filter_query)
            
            return {
                "posts": posts,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit,
                "feed_type": feed_type
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo feed: {e}")
            return {"posts": [], "total": 0, "page": page, "pages": 0}
    
    async def update_post(
        self,
        post_id: str,
        user_id: str,
        update_data: dict
    ) -> Optional[dict]:
        """Actualizar una publicación"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.db.posts.find_one_and_update(
                {
                    "_id": ObjectId(post_id),
                    "user_id": user_id
                },
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
            
            return result
            
        except Exception as e:
            logger.error(f"Error actualizando post: {e}")
            return None
    
    async def delete_post(self, post_id: str, user_id: str) -> bool:
        """Eliminar una publicación (soft delete)"""
        try:
            result = await self.db.posts.update_one(
                {
                    "_id": ObjectId(post_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "is_deleted": True,
                        "deleted_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Actualizar contador
                await self.db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$inc": {"stats.total_posts": -1}}
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error eliminando post: {e}")
            return False
    
    async def toggle_like(self, post_id: str, user_id: str) -> bool:
        """Dar/quitar like a una publicación"""
        try:
            post = await self.db.posts.find_one({"_id": ObjectId(post_id)})
            if not post:
                return False
            
            likes = post.get("likes", [])
            
            if user_id in likes:
                # Quitar like
                await self.db.posts.update_one(
                    {"_id": ObjectId(post_id)},
                    {
                        "$pull": {"likes": user_id},
                        "$inc": {"likes_count": -1}
                    }
                )
                return False  # Like removido
            else:
                # Dar like
                await self.db.posts.update_one(
                    {"_id": ObjectId(post_id)},
                    {
                        "$addToSet": {"likes": user_id},
                        "$inc": {"likes_count": 1}
                    }
                )
                return True  # Like agregado
                
        except Exception as e:
            logger.error(f"Error toggling like: {e}")
            return False
    
    async def add_comment(
        self,
        post_id: str,
        user_id: str,
        username: str,
        profile_picture: Optional[str],
        content: str,
        reply_to: Optional[str] = None
    ) -> Optional[dict]:
        """Agregar comentario a una publicación"""
        try:
            comment = {
                "id": str(ObjectId()),
                "user_id": user_id,
                "username": username,
                "profile_picture": profile_picture,
                "content": content,
                "likes": [],
                "likes_count": 0,
                "replies": [],
                "replies_count": 0,
                "is_edited": False,
                "created_at": datetime.utcnow()
            }
            
            if reply_to:
                # Agregar como respuesta a otro comentario
                await self.db.posts.update_one(
                    {
                        "_id": ObjectId(post_id),
                        "comments.id": reply_to
                    },
                    {
                        "$push": {"comments.$.replies": comment},
                        "$inc": {
                            "comments.$.replies_count": 1,
                            "comments_count": 1
                        }
                    }
                )
            else:
                # Agregar como comentario principal
                await self.db.posts.update_one(
                    {"_id": ObjectId(post_id)},
                    {
                        "$push": {"comments": comment},
                        "$inc": {"comments_count": 1}
                    }
                )
            
            return comment
            
        except Exception as e:
            logger.error(f"Error agregando comentario: {e}")
            return None
    
    async def get_comments(
        self,
        post_id: str,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """Obtener comentarios de una publicación"""
        try:
            post = await self.db.posts.find_one(
                {"_id": ObjectId(post_id)},
                {"comments": 1}
            )
            
            if not post:
                return {"comments": [], "total": 0}
            
            comments = post.get("comments", [])
            total = len(comments)
            
            # Paginación manual (los comentarios están embebidos)
            skip = (page - 1) * limit
            paginated = comments[skip:skip + limit]
            
            return {
                "comments": paginated,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo comentarios: {e}")
            return {"comments": [], "total": 0}
    
    async def get_user_posts(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """Obtener publicaciones de un usuario"""
        try:
            skip = (page - 1) * limit
            
            filter_query = {
                "user_id": user_id,
                "is_deleted": {"$ne": True}
            }
            
            cursor = self.db.posts.find(filter_query)\
                .sort("created_at", -1)\
                .skip(skip)\
                .limit(limit)
            
            posts = []
            async for post in cursor:
                post["_id"] = str(post["_id"])
                posts.append(post)
            
            total = await self.db.posts.count_documents(filter_query)
            
            return {
                "posts": posts,
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo posts de usuario: {e}")
            return {"posts": [], "total": 0}
    
    async def increment_views(self, post_id: str, user_id: str) -> None:
        """Incrementar contador de vistas"""
        try:
            await self.db.posts.update_one(
                {"_id": ObjectId(post_id)},
                {"$inc": {"views_count": 1}}
            )
        except:
            pass
    
    async def upload_media(self, user_id: str, files: List[UploadFile]) -> List[str]:
        """Subir archivos multimedia para publicaciones"""
        urls = []
        
        for file in files:
            try:
                # Crear directorio
                upload_dir = f"uploads/posts/{user_id}"
                os.makedirs(upload_dir, exist_ok=True)
                
                # Guardar archivo
                file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
                filename = f"{datetime.utcnow().timestamp()}_{ObjectId()}.{file_extension}"
                file_path = f"{upload_dir}/{filename}"
                
                async with aiofiles.open(file_path, 'wb') as out_file:
                    content = await file.read()
                    await out_file.write(content)
                
                url = f"/media/posts/{user_id}/{filename}"
                urls.append(url)
                
            except Exception as e:
                logger.error(f"Error subiendo archivo: {e}")
        
        return urls