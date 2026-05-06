"""
Endpoints de publicaciones y feed
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File
from typing import Optional, List
from app.services.post_service import PostService
from app.core.dependencies import get_post_service, get_current_user, get_optional_current_user
from app.schemas.post import (
    CreatePostRequest, UpdatePostRequest, PostResponse,
    CommentRequest, FeedRequest
)

router = APIRouter(prefix="/posts", tags=["📝 Publicaciones"])

@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear publicación",
    description="Crea una nueva publicación con texto, media y configuraciones."
)
async def create_post(
    post_data: CreatePostRequest,
    current_user: dict = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service)
):
    """Crear nueva publicación"""
    # ✅ Convertir objetos Pydantic de media a diccionarios
    media_dicts = []
    for m in post_data.media:
        if hasattr(m, 'model_dump'):
            media_dicts.append(m.model_dump())
        elif hasattr(m, 'dict'):
            media_dicts.append(m.dict())
        else:
            media_dicts.append(m)
    
    post = await post_service.create_post(
        user_id=current_user["_id"],
        username=current_user["username"],
        profile_picture=current_user.get("profile_picture"),
        content=post_data.content,
        media=media_dicts,
        visibility=post_data.visibility,
        tags=post_data.tags,
        hashtags=post_data.hashtags,
        location=post_data.location.model_dump() if post_data.location and hasattr(post_data.location, 'model_dump') else post_data.location,
        is_nsfw=post_data.is_nsfw,
        has_spoiler=post_data.has_spoiler
    )
    
    if not post:
        raise HTTPException(status_code=400, detail="Error al crear publicación")
    
    return post


@router.get(
    "/feed",
    response_model=dict,
    summary="Obtener feed de noticias",
    description="Obtiene el feed personalizado del usuario."
)
async def get_feed(
    feed_type: str = Query("following", pattern="^(following|explore|trending)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    country: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    post_service: PostService = Depends(get_post_service)
):
    """Obtener feed de publicaciones"""
    user_id = current_user["_id"] if current_user else None
    
    posts = await post_service.get_feed(
        user_id=user_id,
        feed_type=feed_type,
        page=page,
        limit=limit,
        country=country
    )
    
    return posts


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Obtener publicación",
    description="Obtiene una publicación específica por ID."
)
async def get_post(
    post_id: str,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    post_service: PostService = Depends(get_post_service)
):
    """Obtener publicación por ID"""
    post = await post_service.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    
    if current_user:
        await post_service.increment_views(post_id, current_user["_id"])
    
    return post


@router.put(
    "/{post_id}",
    response_model=PostResponse,
    summary="Editar publicación",
    description="Edita una publicación propia."
)
async def update_post(
    post_id: str,
    update_data: UpdatePostRequest,
    current_user: dict = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service)
):
    """Actualizar publicación"""
    update_dict = update_data.model_dump(exclude_unset=True)
    
    post = await post_service.update_post(
        post_id=post_id,
        user_id=current_user["_id"],
        update_data=update_dict
    )
    
    if not post:
        raise HTTPException(status_code=404, detail="Publicación no encontrada o no autorizado")
    
    return post


@router.delete(
    "/{post_id}",
    summary="Eliminar publicación",
    description="Elimina una publicación propia."
)
async def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service)
):
    """Eliminar publicación"""
    success = await post_service.delete_post(post_id, current_user["_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    
    return {"message": "Publicación eliminada"}


@router.post(
    "/{post_id}/like",
    summary="Dar like a publicación",
    description="Agrega o quita like de una publicación."
)
async def like_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service)
):
    """Dar/quitar like a publicación"""
    liked = await post_service.toggle_like(post_id, current_user["_id"])
    action = "agregado" if liked else "eliminado"
    return {"message": f"Like {action}", "liked": liked}


@router.post(
    "/{post_id}/comment",
    response_model=dict,
    summary="Comentar publicación",
    description="Agrega un comentario a una publicación."
)
async def comment_post(
    post_id: str,
    comment_data: CommentRequest,
    current_user: dict = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service)
):
    """Comentar en publicación"""
    comment = await post_service.add_comment(
        post_id=post_id,
        user_id=current_user["_id"],
        username=current_user["username"],
        profile_picture=current_user.get("profile_picture"),
        content=comment_data.content,
        reply_to=comment_data.reply_to_comment_id
    )
    
    if not comment:
        raise HTTPException(status_code=400, detail="Error al agregar comentario")
    
    return comment


@router.get(
    "/{post_id}/comments",
    summary="Obtener comentarios",
    description="Obtiene los comentarios de una publicación."
)
async def get_post_comments(
    post_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    post_service: PostService = Depends(get_post_service)
):
    """Obtener comentarios"""
    comments = await post_service.get_comments(post_id, page, limit)
    return comments


@router.get(
    "/user/{user_id}",
    response_model=dict,
    summary="Publicaciones de usuario",
    description="Obtiene las publicaciones de un usuario específico."
)
async def get_user_posts(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    post_service: PostService = Depends(get_post_service)
):
    """Obtener publicaciones de un usuario"""
    posts = await post_service.get_user_posts(user_id, page, limit)
    return posts


@router.post(
    "/upload-media",
    summary="Subir media para publicación",
    description="Sube imágenes o videos para usar en publicaciones."
)
async def upload_media(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    post_service: PostService = Depends(get_post_service)
):
    """Subir archivos multimedia"""
    urls = await post_service.upload_media(current_user["_id"], files)
    return {"urls": urls}