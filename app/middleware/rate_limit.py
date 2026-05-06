"""
Middleware de rate limiting
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis_client import RedisClient
from app.core.config import settings
import time
import hashlib

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para limitar peticiones por IP/usuario"""
    
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Obtener identificador del cliente
        client_id = self._get_client_id(request)
        
        # Verificar rate limit
        redis = RedisClient.get_redis()
        if redis:
            key = f"rate_limit:{client_id}"
            
            # Verificar límite
            allowed = await RedisClient.rate_limit_check(
                key,
                settings.RATE_LIMIT_REQUESTS,
                settings.RATE_LIMIT_PERIOD
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Demasiadas peticiones. Intenta de nuevo más tarde.",
                    headers={"Retry-After": str(settings.RATE_LIMIT_PERIOD)}
                )
        
        # Procesar request
        response = await call_next(request)
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Obtener identificador único del cliente"""
        # Intentar obtener de header personalizado o usar IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Agregar user-agent para más unicidad
        user_agent = request.headers.get("User-Agent", "")
        identifier = f"{client_ip}:{user_agent}"
        
        return hashlib.md5(identifier.encode()).hexdigest()