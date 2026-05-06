"""
Conexión y gestión de MongoDB
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    """
    Singleton para manejar la conexión a MongoDB
    """
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect_db(cls, mongodb_url: str, db_name: str):
        """
        Establecer conexión con MongoDB
        
        Args:
            mongodb_url: URL de conexión
            db_name: Nombre de la base de datos
        """
        try:
            # Crear cliente con configuración optimizada
            cls.client = AsyncIOMotorClient(
                mongodb_url,
                maxPoolSize=100,
                minPoolSize=10,
                maxIdleTimeMS=10000,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                retryWrites=True,
                w='majority'
            )
            
            # Obtener referencia a la base de datos
            cls.db = cls.client[db_name]
            
            # Verificar conexión
            await cls.client.admin.command('ping')
            logger.info("✅ Conexión a MongoDB establecida exitosamente")
            
            # Crear índices necesarios
            await cls._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ Error conectando a MongoDB: {e}")
            raise
    
    @classmethod
    async def _create_indexes(cls):
        """
        Crear todos los índices necesarios para optimizar consultas
        """
        if cls.db is None:
            return
        
        try:
            # Índices para users
            await cls.db.users.create_index("email", unique=True, sparse=True)
            await cls.db.users.create_index("username", unique=True, sparse=True)
            await cls.db.users.create_index([("location.country", 1), ("preferences.language", 1)])
            await cls.db.users.create_index("followers_count")
            await cls.db.users.create_index("created_at")
            
            # Índices compuestos para búsquedas frecuentes
            await cls.db.users.create_index([
                ("location.country", 1),
                ("preferences.language", 1),
                ("is_active", 1)
            ])
            
            # Índices para followers
            await cls.db.followers.create_index(
                [("follower_id", 1), ("following_id", 1)],
                unique=True
            )
            await cls.db.followers.create_index("following_id")
            
            # Índices para chats
            await cls.db.chats.create_index("participants")
            await cls.db.chats.create_index([
                ("type", 1), 
                ("country", 1), 
                ("language", 1)
            ])
            await cls.db.chats.create_index("updated_at")
            
            # Índices para messages
            await cls.db.messages.create_index([
                ("chat_id", 1), 
                ("timestamp", -1)
            ])
            await cls.db.messages.create_index("sender_id")
            await cls.db.messages.create_index("timestamp")
            
            # Índices para posts
            await cls.db.posts.create_index([
                ("user_id", 1), 
                ("created_at", -1)
            ])
            await cls.db.posts.create_index("created_at")
            await cls.db.posts.create_index([
                ("visibility", 1),
                ("created_at", -1)
            ])
            # Índice de texto para búsqueda
            await cls.db.posts.create_index([
                ("content", "text"),
                ("tags", "text")
            ])
            
            # Índices para notifications
            await cls.db.notifications.create_index([
                ("user_id", 1), 
                ("created_at", -1)
            ])
            await cls.db.notifications.create_index(
                "created_at",
                expireAfterSeconds=30 * 24 * 3600  # TTL de 30 días
            )
            
            # Índices para streams
            await cls.db.streams.create_index("user_id")
            await cls.db.streams.create_index([
                ("status", 1),
                ("started_at", -1)
            ])
            await cls.db.streams.create_index("stream_key", unique=True)
            
            # Índices para friend_requests
            await cls.db.friend_requests.create_index([
                ("from_user_id", 1),
                ("to_user_id", 1)
            ], unique=True)
            await cls.db.friend_requests.create_index("to_user_id")
            
            logger.info("📊 Índices de MongoDB creados exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error creando índices: {e}")
            raise
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """
        Obtener instancia de la base de datos
        
        Returns:
            Instancia de la base de datos
            
        Raises:
            Exception: Si la base de datos no está inicializada
        """
        if cls.db is None:
            raise Exception(
                "Base de datos no inicializada. "
                "Llama a Database.connect_db() primero."
            )
        return cls.db
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """
        Obtener una colección específica
        
        Args:
            collection_name: Nombre de la colección
            
        Returns:
            Colección de MongoDB
        """
        db = cls.get_db()
        return db[collection_name]
    
    @classmethod
    async def close_db(cls):
        """
        Cerrar conexión a MongoDB
        """
        if cls.client:
            cls.client.close()
            logger.info("🔒 Conexión a MongoDB cerrada")
    
    @classmethod
    async def get_collection_stats(cls, collection_name: str) -> dict:
        """
        Obtener estadísticas de una colección
        
        Args:
            collection_name: Nombre de la colección
            
        Returns:
            Diccionario con estadísticas
        """
        db = cls.get_db()
        collection = db[collection_name]
        
        try:
            count = await collection.count_documents({})
            size = await db.command("collStats", collection_name)
            
            return {
                "name": collection_name,
                "document_count": count,
                "size_bytes": size.get("size", 0),
                "indexes": size.get("nindexes", 0),
                "total_index_size": size.get("totalIndexSize", 0)
            }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}