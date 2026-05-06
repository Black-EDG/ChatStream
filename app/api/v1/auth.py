"""
Endpoints de autenticación
"""
from fastapi import APIRouter, HTTPException, Depends, status, Body
from app.services.auth_service import AuthService
from app.core.dependencies import get_auth_service, get_current_user
from app.schemas.user import (
    UserRegister, UserLogin, TokenResponse,
    RefreshTokenRequest, UserResponse
)

router = APIRouter(prefix="/auth", tags=["🔐 Autenticación"])

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario"
)
async def register(
    user_data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service)
):
    success, message, data = await auth_service.register_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name or user_data.username,
        country=user_data.country,
        language=user_data.language
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT if "existe" in message.lower()
            else status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return data


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión"
)
async def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    success, message, data = await auth_service.login_user(
        email=login_data.email,
        password=login_data.password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )
    
    return data


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refrescar token"
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    success, message, data = await auth_service.refresh_access_token(
        refresh_token=refresh_data.refresh_token
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )
    
    return data


@router.post("/logout", summary="Cerrar sesión")
async def logout(
    current_user: dict = Depends(get_current_user)
):
    return {
        "message": "Sesión cerrada exitosamente",
        "user_id": current_user.get("_id", "unknown")
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener usuario actual"
)
async def get_me(
    current_user: dict = Depends(get_current_user)
):
    return current_user