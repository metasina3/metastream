"""
Comment moderation endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Comment, StreamSchedule, User
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


def require_moderator(request: Request, db: Session = Depends(get_db)) -> User:
    """Require moderator/admin"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Moderator access required")
    
    return user


def require_stream_owner_or_moderator(
    stream_id: int,
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Require user to be stream owner or admin/moderator"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Admin can access all streams
    if user.role == "admin":
        return user
    
    # Check if user owns the stream
    from app.models import StreamSchedule, Channel
    stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Check if user owns the stream directly
    if stream.user_id == user.id:
        return user
    
    # Check if user owns the channel
    if stream.channel_id:
        channel = db.query(Channel).filter(Channel.id == stream.channel_id).first()
        if channel and channel.user_id == user.id:
            return user
    
    raise HTTPException(status_code=403, detail="Access denied: You can only moderate your own streams")


@router.get("/{stream_id}/comments")
async def get_comments_for_moderation(
    stream_id: int,
    status: str = "pending",  # pending | approved
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get comments for moderation (two-column layout)
    """
    # Check permission: user must be stream owner or admin
    if request is None:
        raise HTTPException(status_code=400, detail="Request is required")
    user = require_stream_owner_or_moderator(stream_id, request, db)
    
    stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Get pending comments
    pending = db.query(Comment).filter(
        Comment.stream_id == stream_id,
        Comment.approved == False,
        Comment.deleted_at.is_(None)
    ).order_by(Comment.created_at.desc()).all()
    
    # Get approved comments
    approved = db.query(Comment).filter(
        Comment.stream_id == stream_id,
        Comment.approved == True,
        Comment.deleted_at.is_(None)
    ).order_by(Comment.created_at.desc()).limit(100).all()
    
    return {
        "pending": [
            {
                "id": c.id,
                "username": c.username,
                "message": c.message,
                "phone": c.phone,
                "ip_address": c.ip_address,
                "created_at": c.created_at.isoformat()
            }
            for c in pending
        ],
        "approved": [
            {
                "id": c.id,
                "username": c.username,
                "message": c.message,
                "phone": c.phone,
                "ip_address": c.ip_address,
                "created_at": c.created_at.isoformat()
            }
            for c in approved
        ],
        "total_pending": len(pending),
        "total_approved": len(approved)
    }


@router.delete("/{stream_id}/comments/{comment_id}")
async def delete_comment(
    stream_id: int,
    comment_id: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Delete a comment (soft delete) - instant, no confirmation needed
    """
    # Check permission: user must be stream owner or admin
    if request is None:
        raise HTTPException(status_code=400, detail="Request is required")
    user = require_stream_owner_or_moderator(stream_id, request, db)
    
    from app.utils.datetime_utils import now_tehran
    
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.stream_id == stream_id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Soft delete
    comment.deleted_at = now_tehran()
    db.commit()
    
    # Remove from Redis if exists
    try:
        import redis
        from app.core.config import settings
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
        sid = str(stream_id)
        idxKey = f"comments:index:{sid}"
        dataKey = f"comments:data:{sid}"
        redis_client.zrem(idxKey, str(comment_id))
        redis_client.hdel(dataKey, str(comment_id))
    except Exception as e:
        print(f"[MODERATION] Error removing from Redis: {e}")
    
    # Notify WebSocket connections
    try:
        from app.routers.websocket import broadcast_to_stream
        import asyncio
        asyncio.create_task(broadcast_to_stream(stream_id, {
            "type": "comment_deleted",
            "comment_id": comment_id
        }))
    except Exception as e:
        print(f"[MODERATION] Error notifying WebSocket: {e}")
    
    return {"success": True}


@router.post("/{stream_id}/comments/{comment_id}/approve")
async def approve_comment(
    stream_id: int,
    comment_id: int,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Approve a comment - will be published after 15 seconds delay
    """
    # Check permission: user must be stream owner or admin
    if request is None:
        raise HTTPException(status_code=400, detail="Request is required")
    user = require_stream_owner_or_moderator(stream_id, request, db)
    
    from app.utils.datetime_utils import now_tehran
    import redis
    import json
    from app.core.config import settings
    
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.stream_id == stream_id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Approve comment
    comment.approved = True
    
    # Calculate published_at (15 seconds from now)
    published_at = now_tehran()
    from datetime import timedelta
    published_at_timestamp = int((published_at + timedelta(seconds=15)).timestamp() * 1000)
    
    comment.published_at = published_at + timedelta(seconds=15)
    db.commit()
    
    # Store in Redis for Go service (will be published after 15 seconds)
    try:
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
        sid = str(stream_id)
        idxKey = f"comments:index:{sid}"
        dataKey = f"comments:data:{sid}"
        
        # Store comment data
        comment_data = {
            "id": comment.id,
            "username": comment.username,
            "message": comment.message,
            "timestamp": published_at_timestamp
        }
        
        comment_json = json.dumps(comment_data)
        redis_client.hset(dataKey, str(comment.id), comment_json)
        
        # Add to sorted set with timestamp as score (for 15 second delay)
        redis_client.zadd(idxKey, {str(comment.id): published_at_timestamp})
        
    except Exception as e:
        print(f"[MODERATION] Error storing comment in Redis: {e}")
    
    return {"success": True, "published_at": comment.published_at.isoformat()}

