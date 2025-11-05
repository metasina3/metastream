"""
Analytics and export endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Viewer, StreamSchedule, User
from app.utils.excel import export_viewers_to_excel
from typing import Optional
import os
import tempfile

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def require_analytics_access(request: Request, db: Session = Depends(get_db)) -> User:
    """Require user or admin access"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.get("/streams/{stream_id}/viewers/export")
async def export_stream_viewers(
    stream_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_analytics_access)
):
    """
    Export stream viewers to Excel (admin or stream owner)
    """
    stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Check permission
    if user.role != "admin" and stream.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get viewers
    viewers = db.query(Viewer).filter(Viewer.stream_id == stream_id).all()
    
    # Generate Excel file
    file_path = export_viewers_to_excel(viewers, stream_id)
    
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"stream_{stream_id}_viewers.xlsx"
    )


@router.get("/users/{user_id}/stats")
async def get_user_stats(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_analytics_access)
):
    """
    Get user statistics (admin or self)
    """
    if user.role != "admin" and user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's streams
    streams = db.query(StreamSchedule).filter(StreamSchedule.user_id == user_id).all()
    total_streams = len(streams)
    live_streams = len([s for s in streams if s.status == "live"])
    
    # Get total viewers
    total_viewers = sum(s.viewers_count for s in streams)
    
    return {
        "user_id": user_id,
        "total_streams": total_streams,
        "live_streams": live_streams,
        "total_viewers": total_viewers,
        "streams": [
            {
                "id": s.id,
                "title": s.title,
                "status": s.status,
                "viewers_count": s.viewers_count,
                "start_time": s.start_time.isoformat()
            }
            for s in streams[:10]  # Last 10 streams
        ]
    }


@router.get("/general/stats")
async def get_general_stats(
    db: Session = Depends(get_db),
    user: User = Depends(require_analytics_access)
):
    """
    Get general platform statistics (admin only)
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.models import Channel, Video
    
    total_streams = db.query(StreamSchedule).count()
    live_streams = db.query(StreamSchedule).filter(StreamSchedule.status == "live").count()
    total_videos = db.query(Video).count()
    total_channels = db.query(Channel).count()
    total_users = db.query(User).filter(User.role == "user").count()
    
    return {
        "streams": {"total": total_streams, "live": live_streams},
        "videos": total_videos,
        "channels": total_channels,
        "users": total_users
    }

