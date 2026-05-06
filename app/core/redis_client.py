"""
Cliente de Redis para caché y pub/sub
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

class RedisClient:
    """
    Singleton para manejar la conexión a Redis
    """
    _instance: Optional[redis.Redis] = None
    _pubsub: Optional[redis.client.PubSub] = None
    
    @classmethod
    async def connect_redis(cls, redis_url: str):
        """
        Establecer conexión con Redis
        
        Args:
            redis_url: URL de conexión a Redis
        """
        try:
            cls._instance = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )
            
            # Verificar conexión
            await cls._instance.ping()
            logger.info("✅ Conexión a Redis establecida exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Redis: {e}")
            # No lanzar excepción, Redis es opcional
            cls._instance = None
    
    @classmethod
    def get_redis(cls) -> Optional[redis.Redis]:
        """
        Obtener instancia de Redis
        
        Returns:
            Instancia de Redis o None si no está disponible
        """
        return cls._instance
    
    @classmethod
    async def close_redis(cls):
        """
        Cerrar conexión a Redis
        """
        if cls._instance:
            await cls._instance.close()
            logger.info("🔒 Conexión a Redis cerrada")
    
    @classmethod
    async def set_cache(
        cls,
        key: str,
        value: Any,
        expire: int = 3600
    ) -> bool:
        """
        Guardar valor en caché
        
        Args:
            key: Clave del caché
            value: Valor a guardar (se serializa a JSON)
            expire: Tiempo de expiración en segundos
            
        Returns:
            True si se guardó correctamente
        """
        if not cls._instance:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            await cls._instance.setex(key, expire, serialized)
            return True
        except Exception as e:
            logger.error(f"Error guardando en caché: {e}")
            return False
    
    @classmethod
    async def get_cache(cls, key: str) -> Optional[Any]:
        """
        Obtener valor de caché
        
        Args:
            key: Clave del caché
            
        Returns:
            Valor deserializado o None si no existe
        """
        if not cls._instance:
            return None
        
        try:
            data = await cls._instance.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error obteniendo de caché: {e}")
            return None
    
    @classmethod
    async def delete_cache(cls, key: str) -> bool:
        """
        Eliminar clave del caché
        
        Args:
            key: Clave a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        if not cls._instance:
            return False
        
        try:
            await cls._instance.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error eliminando de caché: {e}")
            return False
    
    @classmethod
    async def increment_counter(
        cls,
        key: str,
        amount: int = 1,
        expire: Optional[int] = None
    ) -> int:
        """
        Incrementar contador en Redis
        
        Args:
            key: Clave del contador
            amount: Cantidad a incrementar
            expire: Tiempo de expiración opcional
            
        Returns:
            Nuevo valor del contador
        """
        if not cls._instance:
            return 0
        
        try:
            value = await cls._instance.incrby(key, amount)
            if expire:
                await cls._instance.expire(key, expire)
            return value
        except Exception as e:
            logger.error(f"Error incrementando contador: {e}")
            return 0
    
    @classmethod
    async def publish_message(cls, channel: str, message: dict) -> bool:
        """
        Publicar mensaje en canal de Redis Pub/Sub
        
        Args:
            channel: Nombre del canal
            message: Mensaje a publicar
            
        Returns:
            True si se publicó correctamente
        """
        if not cls._instance:
            return False
        
        try:
            serialized = json.dumps(message, default=str)
            await cls._instance.publish(channel, serialized)
            return True
        except Exception as e:
            logger.error(f"Error publicando mensaje: {e}")
            return False
    
    @classmethod
    async def add_to_set(cls, key: str, *values) -> int:
        """
        Agregar valores a un set de Redis
        
        Args:
            key: Clave del set
            values: Valores a agregar
            
        Returns:
            Número de elementos agregados
        """
        if not cls._instance:
            return 0
        
        try:
            return await cls._instance.sadd(key, *values)
        except Exception as e:
            logger.error(f"Error agregando a set: {e}")
            return 0
    
    @classmethod
    async def rate_limit_check(
        cls,
        key: str,
        max_requests: int,
        period: int
    ) -> bool:
        """
        Verificar rate limiting
        
        Args:
            key: Clave para el rate limit
            max_requests: Máximo de peticiones permitidas
            period: Período en segundos
            
        Returns:
            True si la petición está permitida
        """
        if not cls._instance:
            return True  # Si Redis no está disponible, permitir
        
        try:
            current = await cls._instance.get(key)
            
            if current is None:
                # Primera petición en el período
                await cls._instance.setex(key, period, 1)
                return True
            
            current = int(current)
            if current >= max_requests:
                return False
            
            await cls._instance.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Error en rate limit: {e}")
            return True  # Si hay error, permitir para no bloquear