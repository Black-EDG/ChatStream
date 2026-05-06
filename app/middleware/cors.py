"""
Configuración CORS (ya incluida en main.py, aquí como referencia)
"""
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

def setup_cors(app):
    """Configurar CORS para la aplicación"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "Accept",
            "Origin",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers"
        ],
        expose_headers=[
            "Content-Length",
            "Content-Range",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ],
        max_age=600  # Cache preflight por 10 minutos
    )