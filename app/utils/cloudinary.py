import cloudinary
import cloudinary.uploader
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

async def upload_to_cloudinary(file, folder="posts"):
    content = await file.read()
    result = cloudinary.uploader.upload(
        content,
        folder=f"chatstream/{folder}",
        resource_type="auto"
    )
    return result["secure_url"]
