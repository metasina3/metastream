"""
Admin panel endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User, Channel, Video, StreamSchedule, Viewer
from app.models.approval import Approval
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.security import hash_password
import os
from app.core.config import settings
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(request: Request, db: Session = Depends(get_db)):
    """Require admin role"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user


class CreateUserRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None
    role: str = "user"
    days: Optional[int] = None
    is_active: Optional[bool] = True

class UpdateUserRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    days: Optional[int] = None


# Approvals models for responses
class ApprovalItem(BaseModel):
    id: int
    type: str
    entity_id: int
    user_id: Optional[int]
    status: str
    requested_at: datetime
    reason: Optional[str] = None


@router.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    List all users (admin only)
    """
    offset = (page - 1) * per_page
    # Order: non-admin first by expires_at ascending (NULLs last) then admins
    # SQLAlchemy NULLS LAST portability via case/boolean ordering
    from sqlalchemy import case
    users = (
        db.query(User)
        .order_by(
            case((User.role == "admin", 1), else_=0),  # users first, admins later
            case((User.expires_at == None, 1), else_=0),  # non-null expiry first
            User.expires_at.asc()
        )
        .offset(offset)
        .limit(per_page)
        .all()
    )
    total = db.query(User).count()
    
    return {
        "users": [
            {
                "id": u.id,
                "phone": u.phone,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "is_active": u.is_active,
                "expires_at": u.expires_at.isoformat() if u.expires_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.post("/users/{user_id}/impersonate")
async def impersonate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Impersonate another user (admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Store original user
    request.session["original_user_id"] = admin.id
    request.session["user_id"] = user_id
    
    return {"success": True, "user_id": user_id}


@router.get("/stats")
async def get_statistics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Get platform statistics
    """
    total_users = db.query(User).count()
    total_channels = db.query(Channel).count()
    total_videos = db.query(Video).count()
    live_streams = db.query(StreamSchedule).filter(StreamSchedule.status == "live").count()
    
    # Calculate total viewers
    total_viewers = db.query(Viewer).count()
    
    # Average viewers per stream
    streams_with_viewers = db.query(StreamSchedule).join(Viewer).distinct().count()
    avg_viewers = total_viewers / streams_with_viewers if streams_with_viewers > 0 else 0
    
    return {
        "total_users": total_users,
        "total_channels": total_channels,
        "total_videos": total_videos,
        "live_streams": live_streams,
        "total_viewers": total_viewers,
        "average_viewers_per_stream": round(avg_viewers, 2)
    }


@router.post("/impersonate/revert")
async def revert_impersonation(
    request: Request,
    db: Session = Depends(get_db),
):
    original_user_id = request.session.get("original_user_id")
    if not original_user_id:
        return {"success": True}
    # Ensure original is actually an admin
    original = db.query(User).filter(User.id == original_user_id).first()
    if not original or original.role != "admin":
        # Safety: clear session
        request.session.clear()
        raise HTTPException(status_code=403, detail="Original admin not found")
    request.session["user_id"] = original_user_id
    request.session.pop("original_user_id", None)
    return {"success": True}

@router.post("/users")
async def create_user(
    request: Request,
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Create a new user (admin only). Allows phone/email (one required), password, role, expiry.
    """
    from app.utils.phone_validator import validate_phone
    phone = (payload.phone or '').strip()
    email = (payload.email or '').strip()
    name = payload.name
    password = payload.password
    role = payload.role or 'user'
    days = payload.days
    is_active = True if payload.is_active is None else payload.is_active

    has_phone = bool(phone)
    has_email = bool(email)
    if not has_phone and not has_email:
        raise HTTPException(status_code=400, detail="شماره یا ایمیل اجباری است")
    formatted_phone = None
    if has_phone:
        is_valid, formatted_phone = validate_phone(phone)
        if not is_valid:
            raise HTTPException(status_code=400, detail="شماره موبایل معتبر نیست")
    if has_phone and db.query(User).filter(User.phone == formatted_phone).first():
        raise HTTPException(status_code=400, detail="User with this phone exists")
    if has_email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="User with this email exists")
    expires_at = None
    if role != "admin":
        if days is not None and days > 0:
            expires_at = datetime.utcnow() + timedelta(days=days)
    user = User(
        phone=formatted_phone if has_phone else None,
        email=email if has_email else None,
        name=name or "کاربر",
        role=role,
        phone_verified=bool(has_phone),
        is_active=bool(is_active),
        expires_at=expires_at,
    )
    if password:
        user.password_hash = hash_password(password)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="شماره یا ایمیل تکراری است")
    db.refresh(user)
    return {"success": True, "user_id": user.id, "expires_at": user.expires_at, "is_active": user.is_active}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    from app.utils.phone_validator import validate_phone
    phone = (payload.phone or '').strip() if payload.phone is not None else None
    email = (payload.email or '').strip() if payload.email is not None else None
    if phone is not None:
        if phone:
            is_valid, formatted_phone = validate_phone(phone)
            if not is_valid:
                raise HTTPException(status_code=400, detail="شماره موبایل معتبر نیست")
            other = db.query(User).filter(User.phone == formatted_phone).filter(User.id != user_id).first()
            if other:
                raise HTTPException(status_code=400, detail="User with this phone exists")
            user.phone = formatted_phone
        else:
            user.phone = None
    if email is not None:
        if email:
            other = db.query(User).filter(User.email == email).filter(User.id != user_id).first()
            if other:
                raise HTTPException(status_code=400, detail="User with this email exists")
            user.email = email
        else:
            user.email = None
    if payload.name is not None:
        user.name = payload.name
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        user.role = payload.role
        if payload.role == "admin":
            user.expires_at = None
    if payload.is_active is not None:
        user.is_active = payload.is_active
    effective_role = payload.role if payload.role is not None else user.role
    if effective_role != "admin":
        if payload.days is not None:
            if payload.days > 0:
                user.expires_at = datetime.utcnow() + timedelta(days=payload.days)
            else:
                user.expires_at = None
    db.commit()
    return {"success": True, "user_id": user_id, "expires_at": user.expires_at, "is_active": user.is_active}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Soft-delete a user while keeping all related content (videos, channels, streams, approvals).
    We anonymize credentials and deactivate the account to avoid FK issues.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Anonymize and deactivate
    user.email = None
    user.phone = None
    user.password_hash = None
    user.is_active = False
    user.expires_at = None
    user.name = user.name or "کاربر"

    db.commit()
    return {"success": True}

@router.get("/approvals")
async def list_approvals(
    type: Optional[str] = None,
    status: Optional[str] = None,  # 'pending' | 'approved' | 'rejected' | None (all)
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    q = db.query(Approval)
    if type:
        q = q.filter(Approval.type == type)
    if status:
        q = q.filter(Approval.status == status)
    total = q.count()
    items = q.order_by(Approval.requested_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    
    result = []
    for a in items:
        item_data = {
            "id": a.id,
            "type": a.type,
            "entity_id": a.entity_id,
            "user_id": a.user_id,
            "status": a.status,
            "requested_at": a.requested_at.isoformat(),
            "approved_at": a.approved_at.isoformat() if a.approved_at else None,
            "approved_by": a.approved_by,
            "reason": a.reason,
        }
        # Get user info
        if a.user_id:
            user_obj = db.query(User).filter(User.id == a.user_id).first()
            if user_obj:
                item_data["user"] = {
                    "id": user_obj.id,
                    "name": user_obj.name,
                    "email": user_obj.email,
                    "phone": user_obj.phone,
                }
        
        # Add entity details
        if a.type == "video":
            v = db.query(Video).filter(Video.id == a.entity_id).first()
            if v:
                item_data["entity"] = {
                    "id": v.id,
                    "title": v.title,
                    "status": v.status,
                    "file_size": v.file_size,
                    "processed_file": v.processed_file,
                    "original_file": v.original_file,
                    "duration": v.duration,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
        elif a.type == "channel":
            c = db.query(Channel).filter(Channel.id == a.entity_id).first()
            if c:
                # Generate Aparat link
                aparat_link = f"https://www.aparat.com/{c.aparat_username}"
                item_data["entity"] = {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "status": c.status,
                    "aparat_username": c.aparat_username,
                    "aparat_link": aparat_link,
                    "rtmp_url": c.rtmp_url,
                    "rtmp_key": c.rtmp_key,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
        result.append(item_data)
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": result
    }

@router.post("/approvals/{approval_id}/approve")
async def approve_item(
    approval_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a or a.status != "pending":
        raise HTTPException(status_code=404, detail="Approval not found")
    if a.type == "video":
        v = db.query(Video).filter(Video.id == a.entity_id).first()
        if not v:
            raise HTTPException(status_code=404, detail="Video not found")
        v.status = "ready"
        v.approved_at = datetime.utcnow()
        v.approved_by = admin.id
    elif a.type == "channel":
        c = db.query(Channel).filter(Channel.id == a.entity_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Channel not found")
        c.status = "approved"
    a.status = "approved"
    a.approved_at = datetime.utcnow()
    a.approved_by = admin.id
    db.commit()
    return {"success": True}

@router.post("/approvals/{approval_id}/reject")
async def reject_item(
    approval_id: int,
    request: Request,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a or a.status != "pending":
        raise HTTPException(status_code=404, detail="Approval not found")
    if a.type == "video":
        v = db.query(Video).filter(Video.id == a.entity_id).first()
        if v:
            v.status = "rejected"
            v.processed_at = datetime.utcnow()
            db.commit()
            # Note: cleanup_rejected_videos runs hourly via Celery Beat and will delete rejected videos older than 24 hours
    elif a.type == "channel":
        c = db.query(Channel).filter(Channel.id == a.entity_id).first()
        if c:
            c.status = "rejected"
    a.status = "rejected"
    a.approved_at = datetime.utcnow()
    a.approved_by = admin.id
    a.reason = reason
    db.commit()
    return {"success": True}

@router.get("/approvals/{approval_id}/video")
async def get_approval_video(
    approval_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Get video file for preview (admin only)"""
    a = db.query(Approval).filter(Approval.id == approval_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Approval not found")
    if a.type != "video":
        raise HTTPException(status_code=400, detail="Not a video approval")
    v = db.query(Video).filter(Video.id == a.entity_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    # Use processed file if available, otherwise original
    video_file = v.processed_file if v.processed_file and os.path.exists(v.processed_file) else v.original_file
    if not video_file or not os.path.exists(video_file):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Determine media type from extension
    ext = video_file.split('.')[-1].lower() if '.' in video_file else 'mp4'
    media_types = {
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
    }
    media_type = media_types.get(ext, 'video/mp4')
    
    return FileResponse(video_file, media_type=media_type, filename=f"video_{v.id}.{ext}")

@router.post("/videos/{video_id}/update-duration")
async def update_video_duration(
    video_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Update video duration by extracting from file (admin only, for fixing old videos)
    """
    import subprocess
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Find video file
    video_file = None
    if video.processed_file and os.path.exists(video.processed_file):
        video_file = video.processed_file
    elif video.original_file and os.path.exists(video.original_file):
        video_file = video.original_file
    
    if not video_file:
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Extract duration
    duration_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_file
    ]
    try:
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=10)
        if duration_result.returncode == 0:
            duration_str = duration_result.stdout.strip()
            if duration_str:
                video.duration = int(float(duration_str))
                db.commit()
                return {"success": True, "duration": video.duration, "video_id": video_id}
        return {"success": False, "error": "Could not extract duration"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/cleanup/orphaned-files")
async def cleanup_orphaned_files(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Clean up orphaned video files (files on disk that don't exist in database)
    """
    import glob
    import os
    
    # Get all video files from database
    all_videos = db.query(Video).all()
    db_files = set()
    for v in all_videos:
        if v.original_file and os.path.exists(v.original_file):
            db_files.add(os.path.abspath(v.original_file))
        if v.processed_file and os.path.exists(v.processed_file):
            db_files.add(os.path.abspath(v.processed_file))
    
    # Scan upload directory for video files
    from app.core.config import settings
    upload_dir = settings.UPLOAD_DIR
    if not os.path.exists(upload_dir):
        return {"success": True, "deleted": 0, "message": "Upload directory does not exist"}
    
    orphaned_files = []
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v']
    
    # Walk through upload directory
    for root, dirs, files in os.walk(upload_dir):
        # Skip chunks directory
        if 'chunks' in root:
            continue
        for file in files:
            file_path = os.path.join(root, file)
            abs_path = os.path.abspath(file_path)
            # Check if it's a video file
            if any(file.lower().endswith(ext) for ext in video_extensions):
                # Check if it's not in database
                if abs_path not in db_files:
                    orphaned_files.append(abs_path)
    
    # Delete orphaned files
    deleted_count = 0
    errors = []
    for file_path in orphaned_files:
        try:
            os.remove(file_path)
            deleted_count += 1
            print(f"[CLEANUP] Removed orphaned file: {file_path}")
        except Exception as e:
            errors.append(f"{file_path}: {str(e)}")
            print(f"[CLEANUP] Error removing {file_path}: {e}")
    
    return {
        "success": True,
        "deleted": deleted_count,
        "total_orphaned": len(orphaned_files),
        "errors": errors if errors else None,
        "message": f"Cleaned up {deleted_count} orphaned file(s)"
    }
