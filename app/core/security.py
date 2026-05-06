"""
Módulo de seguridad: JWT, hashing de contraseñas, etc.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
import secrets
import hashlib
import base64

from app.core.config import settings

# Contexto de bcrypt para hashing de contraseñas
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS
)

class SecurityManager:
    """Gestor centralizado de seguridad"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hashear contraseña usando bcrypt
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            Hash de la contraseña
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verificar contraseña contra su hash
        
        Args:
            plain_password: Contraseña en texto plano
            hashed_password: Hash almacenado
            
        Returns:
            True si la contraseña coincide
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Crear token JWT de acceso
        
        Args:
            data: Datos a incluir en el payload
            expires_delta: Tiempo de expiración personalizado
            
        Returns:
            Token JWT firmado
        """
        to_encode = data.copy()
        
        # Establecer tiempo de expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        # Agregar claims estándar
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": secrets.token_hex(16)  # ID único del token
        })
        
        # Firmar y codificar
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Crear token JWT de refresco
        
        Args:
            data: Datos a incluir en el payload
            
        Returns:
            Token JWT de refresco
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_hex(16)
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decodificar y validar token JWT
        
        Args:
            token: Token JWT a decodificar
            
        Returns:
            Payload decodificado o None si es inválido
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": True}
            )
            return payload
        except JWTError as e:
            return None
        except Exception as e:
            return None
    
    @staticmethod
    def validate_access_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Validar token de acceso específicamente
        
        Args:
            token: Token JWT
            
        Returns:
            Payload si es válido y es de tipo 'access'
        """
        payload = SecurityManager.decode_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None
    
    @staticmethod
    def validate_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Validar token de refresco
        
        Args:
            token: Token JWT
            
        Returns:
            Payload si es válido y es de tipo 'refresh'
        """
        payload = SecurityManager.decode_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None
    
    @staticmethod
    def get_token_from_header(authorization: str) -> Optional[str]:
        """
        Extraer token del header de autorización
        
        Args:
            authorization: Header Authorization completo
            
        Returns:
            Token extraído o None
        """
        if not authorization:
            return None
        
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                return token
        except ValueError:
            return None
        
        return None
    
    @staticmethod
    def generate_stream_key(user_id: str, stream_id: str) -> str:
        """
        Generar clave única para streaming
        
        Args:
            user_id: ID del usuario
            stream_id: ID del stream
            
        Returns:
            Stream key hasheada
        """
        raw_key = f"{user_id}:{stream_id}:{settings.STREAM_KEY_SECRET}"
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    @staticmethod
    def generate_room_id() -> str:
        """
        Generar ID único para sala de WebRTC
        
        Returns:
            ID de sala aleatorio
        """
        return secrets.token_urlsafe(16)
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Sanitizar texto para prevenir XSS
        
        Args:
            text: Texto a sanitizar
            
        Returns:
            Texto sanitizado
        """
        import html
        return html.escape(text)