"""
Servicio de autenticación y autorización
"""
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.core.security import SecurityManager
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)

class AuthService:
    """Servicio completo de autenticación"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.security = SecurityManager()
    
    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
        country: str,
        language: str = "es"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Registrar un nuevo usuario
        
        Args:
            username: Nombre de usuario único
            email: Correo electrónico
            password: Contraseña (ya validada)
            full_name: Nombre completo
            country: País del usuario
            language: Idioma preferido
            
        Returns:
            Tuple[éxito, mensaje, datos_usuario_con_tokens]
        """
        try:
            # Validar formato de email
            if not self._validate_email(email):
                return False, "Formato de email inválido", None
            
            # Validar fortaleza de contraseña
            is_valid_pwd, pwd_message = self._validate_password_strength(password)
            if not is_valid_pwd:
                return False, pwd_message, None
            
            # Validar username
            is_valid_username, username_message = self._validate_username(username)
            if not is_valid_username:
                return False, username_message, None
            
            # Verificar si el email ya existe
            existing_email = await self.db.users.find_one({"email": email})
            if existing_email:
                return False, "Este email ya está registrado", None
            
            # Verificar si el username ya existe
            existing_username = await self.db.users.find_one({"username": username})
            if existing_username:
                return False, "Este nombre de usuario no está disponible", None
            
            # Crear hash de la contraseña
            hashed_password = self.security.hash_password(password)
            
            # Preparar datos del usuario
            user_data = {
                "username": username,
                "email": email,
                "hashed_password": hashed_password,
                "full_name": full_name,
                "bio": "",
                "profile_picture": None,
                "cover_picture": None,
                
                # Ubicación
                "location": {
                    "country": country,
                    "city": None,
                    "state": None,
                    "timezone": None,
                    "coordinates": None
                },
                
                # Preferencias
                "preferences": {
                    "language": language,
                    "notifications_enabled": True,
                    "private_profile": False,
                    "show_online_status": True,
                    "dark_mode": False,
                    "email_notifications": True,
                    "push_notifications": True
                },
                
                # Redes sociales
                "social_links": {
                    "website": None,
                    "twitter": None,
                    "instagram": None,
                    "github": None,
                    "linkedin": None
                },
                
                # Contadores
                "followers_count": 0,
                "following_count": 0,
                "followers": [],
                "following": [],
                
                # Amigos
                "friends_count": 0,
                "friends": [],
                
                # Likes
                "likes_received": 0,
                "liked_users": [],
                
                # Estado
                "is_active": True,
                "is_verified": False,
                "is_online": False,
                "last_seen": None,
                "last_login": None,
                
                # Roles
                "roles": ["user"],
                "permissions": ["basic"],
                
                # Estadísticas iniciales
                "stats": {
                    "total_posts": 0,
                    "total_likes_received": 0,
                    "total_comments": 0,
                    "total_streams": 0,
                    "total_streaming_hours": 0.0,
                    "account_age_days": 0
                },
                
                # Fechas
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "deleted_at": None
            }
            
            # Insertar en base de datos
            result = await self.db.users.insert_one(user_data)
            user_id = str(result.inserted_id)
            
            # Actualizar el ID en los datos
            user_data["_id"] = user_id
            
            # Crear chat global por defecto para su país/idioma
            await self._setup_default_chats(user_id, country, language)
            
            # Generar tokens
            tokens = self._generate_tokens(user_id)
            
            # Crear usuario sanitizado (sin datos sensibles)
            safe_user = self._sanitize_user(user_data)
            
            logger.info(f"✅ Nuevo usuario registrado: {username} ({email})")
            
            return True, "Usuario registrado exitosamente", {
                "user": safe_user,
                **tokens
            }
            
        except Exception as e:
            logger.error(f"❌ Error en registro: {e}")
            return False, "Error del servidor al registrar usuario", None
    
    async def login_user(
        self,
        email: str,
        password: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Iniciar sesión de usuario
        
        Args:
            email: Correo electrónico
            password: Contraseña en texto plano
            
        Returns:
            Tuple[éxito, mensaje, datos_usuario_con_tokens]
        """
        try:
            # Buscar usuario por email
            user = await self.db.users.find_one({"email": email.lower().strip()})
            
            if not user:
                return False, "Credenciales inválidas", None
            
            # Verificar si la cuenta está activa
            if not user.get("is_active", True):
                return False, "Esta cuenta ha sido desactivada. Contacta con soporte.", None
            
            # Verificar si la cuenta está eliminada
            if user.get("deleted_at"):
                return False, "Esta cuenta ya no existe", None
            
            # Verificar contraseña
            if not self.security.verify_password(password, user["hashed_password"]):
                # Registrar intento fallido
                await self._log_failed_login(user["_id"])
                return False, "Credenciales inválidas", None
            
            # Actualizar último inicio de sesión
            await self.db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "last_login": datetime.utcnow(),
                        "is_online": True,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Generar tokens
            user_id = str(user["_id"])
            tokens = self._generate_tokens(user_id)
            
            # Sanitizar datos del usuario
            safe_user = self._sanitize_user(user)
            
            logger.info(f"✅ Usuario logueado: {user.get('username')} ({email})")
            
            return True, "Inicio de sesión exitoso", {
                "user": safe_user,
                **tokens
            }
            
        except Exception as e:
            logger.error(f"❌ Error en login: {e}")
            return False, "Error del servidor al iniciar sesión", None
    
    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Refrescar access token usando refresh token
        
        Args:
            refresh_token: Token de refresco válido
            
        Returns:
            Tuple[éxito, mensaje, nuevos_tokens]
        """
        try:
            # Validar refresh token
            payload = self.security.validate_refresh_token(refresh_token)
            
            if not payload:
                return False, "Token de refresco inválido o expirado", None
            
            # Obtener user_id del token
            user_id = payload.get("sub")
            if not user_id:
                return False, "Token inválido: falta identificador de usuario", None
            
            # Verificar que el usuario existe y está activo
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                return False, "Usuario no encontrado", None
            
            if not user.get("is_active", True):
                return False, "Cuenta desactivada", None
            
            # Generar nuevo access token
            access_token = self.security.create_access_token(
                data={
                    "sub": user_id,
                    "username": user.get("username"),
                    "roles": user.get("roles", ["user"])
                }
            )
            
            # Opcional: generar también nuevo refresh token (rotación)
            new_refresh_token = self.security.create_refresh_token(
                data={
                    "sub": user_id,
                    "username": user.get("username")
                }
            )
            
            return True, "Token actualizado exitosamente", {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
            
        except Exception as e:
            logger.error(f"❌ Error refrescando token: {e}")
            return False, "Error al refrescar token", None
    
    async def logout_user(self, user_id: str, access_token: str) -> bool:
        """
        Cerrar sesión de usuario
        
        Args:
            user_id: ID del usuario
            access_token: Token de acceso a invalidar
            
        Returns:
            True si se cerró sesión correctamente
        """
        try:
            # Actualizar estado del usuario
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "is_online": False,
                        "last_seen": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # En una implementación completa, se agregaría el token a una blacklist en Redis
            # await RedisClient.add_to_set("token_blacklist", access_token)
            
            logger.info(f"✅ Usuario {user_id} cerró sesión")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en logout: {e}")
            return False
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Cambiar contraseña del usuario
        
        Args:
            user_id: ID del usuario
            current_password: Contraseña actual
            new_password: Nueva contraseña
            
        Returns:
            Tuple[éxito, mensaje]
        """
        try:
            # Obtener usuario
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return False, "Usuario no encontrado"
            
            # Verificar contraseña actual
            if not self.security.verify_password(current_password, user["hashed_password"]):
                return False, "Contraseña actual incorrecta"
            
            # Validar nueva contraseña
            is_valid, message = self._validate_password_strength(new_password)
            if not is_valid:
                return False, message
            
            # Verificar que no sea igual a la actual
            if self.security.verify_password(new_password, user["hashed_password"]):
                return False, "La nueva contraseña no puede ser igual a la actual"
            
            # Hashear y actualizar
            new_hash = self.security.hash_password(new_password)
            
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "hashed_password": new_hash,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"✅ Contraseña cambiada para usuario {user_id}")
            return True, "Contraseña actualizada exitosamente"
            
        except Exception as e:
            logger.error(f"❌ Error cambiando contraseña: {e}")
            return False, "Error al cambiar contraseña"
    
    async def verify_email(self, token: str) -> Tuple[bool, str]:
        """
        Verificar email del usuario
        
        Args:
            token: Token de verificación
            
        Returns:
            Tuple[éxito, mensaje]
        """
        try:
            # Decodificar token de verificación
            payload = self.security.decode_token(token)
            
            if not payload or payload.get("type") != "email_verification":
                return False, "Token de verificación inválido"
            
            user_id = payload.get("sub")
            
            # Actualizar usuario como verificado
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "is_verified": True,
                        "verified_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                return True, "Email verificado exitosamente"
            
            return False, "No se pudo verificar el email"
            
        except Exception as e:
            logger.error(f"❌ Error verificando email: {e}")
            return False, "Error al verificar email"
    
    async def deactivate_account(self, user_id: str, password: str) -> Tuple[bool, str]:
        """
        Desactivar cuenta de usuario
        
        Args:
            user_id: ID del usuario
            password: Contraseña para confirmar
            
        Returns:
            Tuple[éxito, mensaje]
        """
        try:
            # Verificar contraseña
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                return False, "Usuario no encontrado"
            
            if not self.security.verify_password(password, user["hashed_password"]):
                return False, "Contraseña incorrecta"
            
            # Desactivar cuenta
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "is_active": False,
                        "deactivated_at": datetime.utcnow(),
                        "is_online": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"⚠️ Cuenta desactivada: {user_id}")
            return True, "Cuenta desactivada. Puedes reactivarla iniciando sesión nuevamente."
            
        except Exception as e:
            logger.error(f"❌ Error desactivando cuenta: {e}")
            return False, "Error al desactivar cuenta"
    
    async def reactivate_account(self, email: str, password: str) -> Tuple[bool, str]:
        """
        Reactivar cuenta desactivada
        
        Args:
            email: Email de la cuenta
            password: Contraseña
            
        Returns:
            Tuple[éxito, mensaje]
        """
        try:
            user = await self.db.users.find_one({
                "email": email,
                "is_active": False,
                "deleted_at": None
            })
            
            if not user:
                return False, "No se encontró una cuenta desactivada con ese email"
            
            if not self.security.verify_password(password, user["hashed_password"]):
                return False, "Contraseña incorrecta"
            
            # Reactivar
            await self.db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "is_active": True,
                        "deactivated_at": None,
                        "updated_at": datetime.utcnow()
                    },
                    "$unset": {"deactivated_at": ""}
                }
            )
            
            return True, "Cuenta reactivada exitosamente"
            
        except Exception as e:
            logger.error(f"❌ Error reactivando cuenta: {e}")
            return False, "Error al reactivar cuenta"
    
    def _generate_tokens(self, user_id: str) -> Dict[str, str]:
        """
        Generar access token y refresh token
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Diccionario con tokens
        """
        # Access token (corta duración)
        access_token = self.security.create_access_token(
            data={
                "sub": user_id,
                "type": "access"
            }
        )
        
        # Refresh token (larga duración)
        refresh_token = self.security.create_refresh_token(
            data={
                "sub": user_id,
                "type": "refresh"
            }
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def _validate_email(self, email: str) -> bool:
        """Validar formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validar fortaleza de contraseña
        
        Requisitos:
        - Mínimo 8 caracteres
        - Al menos 1 mayúscula
        - Al menos 1 minúscula
        - Al menos 1 número
        - Al menos 1 carácter especial (opcional pero recomendado)
        """
        if len(password) < 8:
            return False, "La contraseña debe tener al menos 8 caracteres"
        
        if not re.search(r'[A-Z]', password):
            return False, "La contraseña debe contener al menos una letra mayúscula"
        
        if not re.search(r'[a-z]', password):
            return False, "La contraseña debe contener al menos una letra minúscula"
        
        if not re.search(r'\d', password):
            return False, "La contraseña debe contener al menos un número"
        
        # Opcional: carácter especial
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "La contraseña debe contener al menos un carácter especial"
        
        if len(password) > 128:
            return False, "La contraseña no puede exceder los 128 caracteres"
        
        return True, "Contraseña válida"
    
    def _validate_username(self, username: str) -> Tuple[bool, str]:
        """
        Validar nombre de usuario
        
        Requisitos:
        - Entre 3 y 30 caracteres
        - Solo letras, números y guiones bajos
        - No puede comenzar con número
        """
        if len(username) < 3:
            return False, "El nombre de usuario debe tener al menos 3 caracteres"
        
        if len(username) > 30:
            return False, "El nombre de usuario no puede exceder los 30 caracteres"
        
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', username):
            return False, "El nombre de usuario solo puede contener letras, números y guiones bajos, y debe comenzar con letra"
        
        # Lista de usernames prohibidos
        forbidden_usernames = [
            'admin', 'root', 'system', 'moderator', 'administrator',
            'null', 'undefined', 'api', 'test', 'user', 'support',
            'help', 'info', 'contact', 'about', 'privacy', 'terms'
        ]
        
        if username.lower() in forbidden_usernames:
            return False, "Este nombre de usuario no está permitido"
        
        return True, "Nombre de usuario válido"
    
    def _sanitize_user(self, user: dict) -> dict:
        """
        Remover datos sensibles del objeto usuario
        
        Args:
            user: Objeto usuario completo
            
        Returns:
            Usuario sin datos sensibles
        """
        # Crear copia para no modificar el original
        safe_user = {k: v for k, v in user.items() if k not in [
            'hashed_password',
            'deleted_at',
            'deactivated_at'
        ]}
        
        # Convertir ObjectId a string
        if '_id' in safe_user:
            safe_user['_id'] = str(safe_user['_id'])
        
        return safe_user
    
    async def _setup_default_chats(self, user_id: str, country: str, language: str):
        """
        Configurar chats por defecto para nuevo usuario
        
        Args:
            user_id: ID del nuevo usuario
            country: País del usuario
            language: Idioma del usuario
        """
        try:
            # Unir al chat global de su país/idioma
            chat = await self.db.chats.find_one({
                "type": "global",
                "country": country,
                "language": language
            })
            
            if chat:
                await self.db.chats.update_one(
                    {"_id": chat["_id"]},
                    {
                        "$addToSet": {
                            "participants_ids": user_id,
                            "participants": {
                                "user_id": user_id,
                                "joined_at": datetime.utcnow(),
                                "is_admin": False,
                                "is_muted": False
                            }
                        }
                    }
                )
            
        except Exception as e:
            logger.error(f"Error configurando chats por defecto: {e}")
    
    async def _log_failed_login(self, user_id: str):
        """
        Registrar intento fallido de inicio de sesión
        
        Args:
            user_id: ID del usuario
        """
        try:
            await self.db.users.update_one(
                {"_id": user_id},
                {
                    "$inc": {"failed_login_attempts": 1},
                    "$set": {"last_failed_login": datetime.utcnow()}
                }
            )
        except:
            pass
    
    async def get_user_by_token(self, token: str) -> Optional[dict]:
        """
        Obtener usuario desde un token JWT
        
        Args:
            token: Token JWT de acceso
            
        Returns:
            Datos del usuario o None
        """
        try:
            # Decodificar token
            payload = self.security.validate_access_token(token)
            
            if not payload:
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            # Buscar usuario
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            
            if user and user.get("is_active"):
                return self._sanitize_user(user)
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo usuario por token: {e}")
            return None
    
    async def is_token_valid(self, token: str) -> bool:
        """
        Verificar si un token es válido
        
        Args:
            token: Token JWT
            
        Returns:
            True si el token es válido
        """
        payload = self.security.validate_access_token(token)
        
        if not payload:
            return False
        
        # Verificar que el usuario existe y está activo
        user_id = payload.get("sub")
        if user_id:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            return user is not None and user.get("is_active", False)
        
        return False