"""
Servicio de gestión de usuarios
"""
from typing import Optional, Dict, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging
import os
import aiofiles
from fastapi import UploadFile

logger = logging.getLogger(__name__)

class UserService:
    """Servicio de usuarios"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Obtener usuario por ID"""
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                user.pop("hashed_password", None)
            return user
        except Exception as e:
            logger.error(f"Error obteniendo usuario: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """Obtener usuario por username"""
        user = await self.db.users.find_one({"username": username})
        if user:
            user["_id"] = str(user["_id"])
            user.pop("hashed_password", None)
        return user
    
    async def update_user(self, user_id: str, update_data: dict) -> Optional[dict]:
        """Actualizar datos del usuario"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return await self.get_user_by_id(user_id)
            return None
            
        except Exception as e:
            logger.error(f"Error actualizando usuario: {e}")
            return None
    
    async def upload_avatar(self, user_id: str, file: UploadFile) -> dict:
        """Subir avatar del usuario"""
        try:
            upload_dir = f"uploads/avatars/{user_id}"
            os.makedirs(upload_dir, exist_ok=True)
            
            file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
            filename = f"avatar_{datetime.utcnow().timestamp()}.{file_extension}"
            file_path = f"{upload_dir}/{filename}"
            
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
            
            avatar_url = f"/media/avatars/{user_id}/{filename}"
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "profile_picture": avatar_url,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            return {"url": avatar_url}
            
        except Exception as e:
            logger.error(f"Error subiendo avatar: {e}")
            raise
    
    async def upload_cover(self, user_id: str, file: UploadFile) -> dict:
        """Subir portada del usuario"""
        try:
            upload_dir = f"uploads/covers/{user_id}"
            os.makedirs(upload_dir, exist_ok=True)
            
            file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
            filename = f"cover_{datetime.utcnow().timestamp()}.{file_extension}"
            file_path = f"{upload_dir}/{filename}"
            
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
            
            cover_url = f"/media/covers/{user_id}/{filename}"
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "cover_picture": cover_url,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            return {"url": cover_url}
        except Exception as e:
            logger.error(f"Error subiendo portada: {e}")
            raise
    
    async def follow_user(self, follower_id: str, following_id: str) -> bool:
        """Seguir a un usuario"""
        try:
            if follower_id == following_id:
                return False
            
            existing = await self.db.followers.find_one({
                "follower_id": follower_id,
                "following_id": following_id
            })
            
            if existing:
                return False
            
            await self.db.followers.insert_one({
                "follower_id": follower_id,
                "following_id": following_id,
                "created_at": datetime.utcnow()
            })
            
            await self.db.users.update_one(
                {"_id": ObjectId(follower_id)},
                {"$inc": {"following_count": 1}}
            )
            await self.db.users.update_one(
                {"_id": ObjectId(following_id)},
                {"$inc": {"followers_count": 1}}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error siguiendo usuario: {e}")
            return False
    
    async def unfollow_user(self, follower_id: str, following_id: str) -> bool:
        """Dejar de seguir a un usuario"""
        try:
            result = await self.db.followers.delete_one({
                "follower_id": follower_id,
                "following_id": following_id
            })
            
            if result.deleted_count > 0:
                await self.db.users.update_one(
                    {"_id": ObjectId(follower_id)},
                    {"$inc": {"following_count": -1}}
                )
                await self.db.users.update_one(
                    {"_id": ObjectId(following_id)},
                    {"$inc": {"followers_count": -1}}
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error dejando de seguir: {e}")
            return False
    
    async def like_user(self, user_id: str, liked_user_id: str) -> bool:
        """Dar like al perfil de un usuario"""
        try:
            user = await self.db.users.find_one({
                "_id": ObjectId(liked_user_id),
                "liked_users": user_id
            })
            
            if user:
                return False
            
            await self.db.users.update_one(
                {"_id": ObjectId(liked_user_id)},
                {
                    "$addToSet": {"liked_users": user_id},
                    "$inc": {"likes_received": 1}
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error dando like: {e}")
            return False
    
    async def get_followers(self, user_id: str, page: int = 1, limit: int = 20) -> dict:
        """Obtener seguidores de un usuario"""
        skip = (page - 1) * limit
        
        cursor = self.db.followers.find(
            {"following_id": user_id}
        ).skip(skip).limit(limit)
        
        followers = []
        async for follower in cursor:
            user = await self.get_user_by_id(follower["follower_id"])
            if user:
                followers.append(user)
        
        total = await self.db.followers.count_documents({"following_id": user_id})
        
        return {
            "followers": followers,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
    
    async def get_following(self, user_id: str, page: int = 1, limit: int = 20) -> dict:
        """Obtener usuarios que sigue"""
        skip = (page - 1) * limit
        
        cursor = self.db.followers.find(
            {"follower_id": user_id}
        ).skip(skip).limit(limit)
        
        following = []
        async for follow in cursor:
            user = await self.get_user_by_id(follow["following_id"])
            if user:
                following.append(user)
        
        total = await self.db.followers.count_documents({"follower_id": user_id})
        
        return {
            "following": following,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
    
    async def search_users(
        self,
        query: str,
        country: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """Buscar usuarios"""
        search_filter = {
            "$or": [
                {"username": {"$regex": query, "$options": "i"}},
                {"full_name": {"$regex": query, "$options": "i"}},
                {"bio": {"$regex": query, "$options": "i"}}
            ]
        }
        
        if country:
            search_filter["location.country"] = country
        
        skip = (page - 1) * limit
        
        cursor = self.db.users.find(
            search_filter,
            {"hashed_password": 0}
        ).skip(skip).limit(limit)
        
        users = []
        async for user in cursor:
            user["_id"] = str(user["_id"])
            users.append(user)
        
        total = await self.db.users.count_documents(search_filter)
        
        return {
            "users": users,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }