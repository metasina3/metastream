"""
External API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import ApiKey, User, Video
from app.core.config import settings
import uuid
import os

router = APIRouter(prefix="/api/v1", tags=["api"])


def verify_api_key(api_key: str = Header(...), db: Session = Depends(get_db)):
    """Verify API key"""
    key_obj = db.query(ApiKey).filter(
        ApiKey.key == api_key,
        ApiKey.is_active == True
    ).first()
    
    if not key_obj:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return key_obj


@router.post("/videos/upload")
async def upload_video_external(
    file: UploadFile = File(...),
    api_key_obj: ApiKey = Depends(verify_api_key),
    user_id: int = None,
    video_title: str = None,
    db: Session = Depends(get_db)
):
    """
    Upload video via API with API key
    """
    # Check feature enabled
    if not settings.FEATURE_API_UPLOAD:
        raise HTTPException(status_code=403, detail="API upload disabled")
    
    # Get user_id from header or use API key owner
    target_user_id = user_id or api_key_obj.user_id
    
    # Save file
    filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Create video record
    video = Video(
        user_id=target_user_id,
        title=video_title or file.filename,
        original_file=filepath,
        status="uploading",
        file_size=len(content)
    )
    
    db.add(video)
    db.commit()
    db.refresh(video)
    
    return {"success": True, "video_id": video.id, "status": "uploading"}


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "version": "2.0",
        "features": {
            "otp": settings.FEATURE_OTP_ENABLED,
            "telegram": settings.TELEGRAM_ENABLED,
            "api_upload": settings.FEATURE_API_UPLOAD
        }
    }


@router.get("/analytics/viewers/{stream_id}")
async def get_viewer_analytics(
    stream_id: int,
    api_key_obj: ApiKey = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Get viewer analytics for a stream (admin only)
    """
    user = db.query(User).filter(User.id == api_key_obj.user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.models import Viewer
    
    viewers = db.query(Viewer).filter(Viewer.stream_id == stream_id).all()
    
    return {
        "stream_id": stream_id,
        "total_viewers": len(viewers),
        "viewers": [
            {
                "name": v.name,
                "phone": v.phone,
                "joined_at": v.joined_at.isoformat() if v.joined_at else None,
                "left_at": v.left_at.isoformat() if v.left_at else None
            }
            for v in viewers
        ]
    }


@router.post("/backup/trigger")
async def trigger_backup(
    api_key_obj: ApiKey = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Trigger database backup (admin only)
    """
    user = db.query(User).filter(User.id == api_key_obj.user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Trigger backup task
    from app.tasks.backup import backup_database
    backup_database.delay()
    
    return {"success": True, "message": "Backup triggered"}

