"""
Servicio de recomendaciones de usuarios
"""
from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class RecommendationService:
    """Servicio de recomendaciones"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_recommended_users(
        self,
        user_id: str,
        limit: int = 20,
        exclude_following: bool = True,
        same_country: bool = True,
        same_language: bool = True
    ) -> List[dict]:
        """
        Obtener usuarios recomendados basado en:
        - Mismo país
        - Mismo idioma
        - Intereses similares
        - Popularidad
        """
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return []
            
            # IDs a excluir
            exclude_ids = [ObjectId(user_id)]
            
            if exclude_following:
                following_cursor = self.db.followers.find({"follower_id": user_id})
                async for follow in following_cursor:
                    exclude_ids.append(ObjectId(follow["following_id"]))
            
            # Construir filtro base
            filter_query = {
                "_id": {"$nin": exclude_ids},
                "is_active": True
            }
            
            # Preferir mismo país e idioma
            if same_country and user.get("location", {}).get("country"):
                filter_query["location.country"] = user["location"]["country"]
            
            if same_language and user.get("preferences", {}).get("language"):
                filter_query["preferences.language"] = user["preferences"]["language"]
            
            # Buscar usuarios
            cursor = self.db.users.find(
                filter_query,
                {"hashed_password": 0, "email": 0}
            ).sort("followers_count", -1).limit(limit * 2)
            
            recommendations = []
            async for rec in cursor:
                rec["_id"] = str(rec["_id"])
                
                # Calcular score de recomendación
                score = self._calculate_recommendation_score(user, rec)
                rec["recommendation_score"] = score
                
                recommendations.append(rec)
            
            # Ordenar por score y limitar
            recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error obteniendo recomendaciones: {e}")
            return []
    
    def _calculate_recommendation_score(
        self,
        current_user: dict,
        target_user: dict
    ) -> float:
        """
        Calcular puntuación de recomendación basado en similitudes
        
        Factores:
        - Misma ubicación: +30 puntos
        - Mismo idioma: +20 puntos
        - Intereses similares: +15 puntos
        - Popularidad: hasta +25 puntos
        - Actividad reciente: +10 puntos
        """
        score = 0.0
        
        # Misma ubicación
        if (current_user.get("location", {}).get("country") == 
            target_user.get("location", {}).get("country")):
            score += 30
        
        # Mismo idioma
        if (current_user.get("preferences", {}).get("language") == 
            target_user.get("preferences", {}).get("language")):
            score += 20
        
        # Popularidad (seguidores)
        followers = target_user.get("followers_count", 0)
        if followers > 0:
            popularity_score = min(followers / 100, 25)
            score += popularity_score
        
        # Actividad reciente
        if target_user.get("last_login"):
            days_since_last_login = (datetime.utcnow() - target_user["last_login"]).days
            if days_since_last_login < 7:
                score += 10
            elif days_since_last_login < 30:
                score += 5
        
        # Amigos en común (opcional)
        # mutual_friends = len(set(current_user.get("friends", [])) & 
        #                     set(target_user.get("friends", [])))
        # score += min(mutual_friends * 5, 15)
        
        return score
    
    async def get_trending_users(
        self,
        limit: int = 10,
        country: Optional[str] = None
    ) -> List[dict]:
        """Obtener usuarios trending (más likes/seguidores recientes)"""
        try:
            filter_query = {"is_active": True}
            
            if country:
                filter_query["location.country"] = country
            
            cursor = self.db.users.find(
                filter_query,
                {"hashed_password": 0, "email": 0}
            ).sort([
                ("followers_count", -1),
                ("likes_received", -1)
            ]).limit(limit)
            
            trending = []
            async for user in cursor:
                user["_id"] = str(user["_id"])
                trending.append(user)
            
            return trending
            
        except Exception as e:
            logger.error(f"Error obteniendo trending: {e}")
            return []
    
    async def get_similar_users(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[dict]:
        """
        Encontrar usuarios similares basado en:
        - Seguidores en común
        - Intereses similares
        - Patrones de actividad
        """
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return []
            
            # Usuarios con seguidores en común
            user_follower_ids = set()
            followers_cursor = self.db.followers.find({"following_id": user_id})
            async for follower in followers_cursor:
                user_follower_ids.add(follower["follower_id"])
            
            # Encontrar usuarios que siguen las mismas personas
            common_follows = {}
            async for follower_id in user_follower_ids:
                following_cursor = self.db.followers.find({"follower_id": follower_id})
                async for follow in following_cursor:
                    target = follow["following_id"]
                    if target != user_id:
                        common_follows[target] = common_follows.get(target, 0) + 1
            
            # Ordenar por coincidencias
            sorted_users = sorted(common_follows.items(), key=lambda x: x[1], reverse=True)
            similar_ids = [uid for uid, _ in sorted_users[:limit]]
            
            # Obtener datos de usuarios similares
            similar_users = []
            for uid in similar_ids:
                similar_user = await self.db.users.find_one(
                    {"_id": ObjectId(uid)},
                    {"hashed_password": 0}
                )
                if similar_user:
                    similar_user["_id"] = str(similar_user["_id"])
                    similar_user["common_followers"] = common_follows[uid]
                    similar_users.append(similar_user)
            
            return similar_users
            
        except Exception as e:
            logger.error(f"Error encontrando usuarios similares: {e}")
            return []