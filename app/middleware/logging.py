"""
Middleware de logging
"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import time
import logging
import uuid

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Generar ID único para la request
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Tiempo de inicio
        start_time = time.time()
        
        # Log de request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            # Procesar request
            response = await call_next(request)
            
            # Calcular tiempo
            process_time = time.time() - start_time
            
            # Log de response
            logger.info(
                f"[{request_id}] {response.status_code} "
                f"completed in {process_time:.3f}s"
            )
            
            # Agregar headers de debug
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] Error: {str(e)} "
                f"after {process_time:.3f}s"
            )
            raise