"""
Live Player endpoints (channel-based routing)
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Channel, StreamSchedule, Comment, Viewer
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter(tags=["player"])


@router.get("/api/c/{aparat_username}")
async def player_api(aparat_username: str, request: Request):
    """
    API endpoint for player data - returns JSON
    Channel-based player page using aparat_username
    Shows current live or next scheduled stream
    """
    from app.utils.datetime_utils import now_tehran, to_tehran
    
    db: Session = next(get_db())
    
    # Get channel by aparat_username
    channel = db.query(Channel).filter(Channel.aparat_username == aparat_username).first()
    if not channel:
        return JSONResponse({"error": "Channel not found"}, status_code=404)
    
    # Get user name for channel owner
    user_name = channel.name  # Fallback to channel name
    if channel.user_id:
        from app.models import User
        user = db.query(User).filter(User.id == channel.user_id).first()
        if user:
            user_name = user.name
    
    # Check if viewer is the owner (for cancel button)
    is_owner = False
    # We can't reliably check this without authentication in player
    # So we'll skip this for now
    
    # Return channel info even if no stream
    response_data = {
        "channel": {
            "aparat_username": channel.aparat_username,
            "name": channel.name,
            "user_id": channel.user_id,
            "owner_name": user_name
        },
        "viewer": {
            "name": None,
            "phone": None,
            "needs_registration": True
        },
        "is_owner": is_owner
    }
    
    # Get current live stream or next scheduled stream
    now = now_tehran()
    
    # Try live stream first
    live_stream = db.query(StreamSchedule).filter(
        StreamSchedule.channel_id == channel.id,
        StreamSchedule.status == "live"
    ).first()
    
    # If no live, get next scheduled stream (including ones that should have started)
    if not live_stream:
        # Get scheduled streams (including ones past start_time that haven't started yet)
        scheduled_stream = db.query(StreamSchedule).filter(
            StreamSchedule.channel_id == channel.id,
            StreamSchedule.status == "scheduled"
        ).order_by(StreamSchedule.start_time.asc()).first()
        
        if scheduled_stream:
            live_stream = scheduled_stream
    
    # If still no stream, check for recently ended (within 5 minutes) for "ended" message
    if not live_stream:
        ended_stream = db.query(StreamSchedule).filter(
            StreamSchedule.channel_id == channel.id,
            StreamSchedule.status == "ended"
        ).order_by(StreamSchedule.ended_at.desc()).first()
        
        if ended_stream and ended_stream.ended_at:
            ended_time = to_tehran(ended_stream.ended_at)
            time_since_end = (now - ended_time).total_seconds()
            
            # Show ended message for 5 minutes
            if time_since_end < 300:  # 5 minutes
                live_stream = ended_stream
    
    # Check if user needs to register (check cookie first)
    viewer_name = None
    viewer_phone = None
    needs_registration = True
    
    # Try to get from GLOBAL cookie (not per-channel)
    viewer_cookie = request.cookies.get("viewer_data")  # Global cookie
    if viewer_cookie:
        try:
            import json
            viewer_data = json.loads(viewer_cookie)
            viewer_name = viewer_data.get("name")
            viewer_phone = viewer_data.get("phone")
            if viewer_name and viewer_phone:
                needs_registration = False
        except:
            pass
    
    # Update response_data with viewer info
    response_data["viewer"] = {
        "name": viewer_name,
        "phone": viewer_phone,
        "needs_registration": needs_registration
    }
    
    # Add stream info if exists
    if live_stream:
        response_data["stream"] = {
            "id": live_stream.id,
            "title": live_stream.title,
            "caption": live_stream.caption,
            "start_time": to_tehran(live_stream.start_time).isoformat(),
            "status": live_stream.status,
            "allow_comments": live_stream.allow_comments,
            "duration": live_stream.duration,
            "started_at": to_tehran(live_stream.started_at).isoformat() if live_stream.started_at else None,
            "ended_at": to_tehran(live_stream.ended_at).isoformat() if live_stream.ended_at else None
        }
        
        # Check for next stream if current is ended
        if live_stream.status == "ended":
            next_stream = db.query(StreamSchedule).filter(
                StreamSchedule.channel_id == channel.id,
                StreamSchedule.status == "scheduled",
                StreamSchedule.start_time > now
            ).order_by(StreamSchedule.start_time.asc()).first()
            
            if next_stream:
                response_data["next_stream"] = {
                    "id": next_stream.id,
                    "title": next_stream.title,
                    "start_time": to_tehran(next_stream.start_time).isoformat()
                }
    
    return JSONResponse(response_data)


@router.post("/api/c/{aparat_username}/enter")
async def enter_stream(aparat_username: str, request: Request, name: str, phone: str):
    """
    Register viewer info and store in cookie
    """
    from fastapi import Response
    import json
    from app.core.config import settings
    
    db: Session = next(get_db())
    
    # Get channel
    channel = db.query(Channel).filter(Channel.aparat_username == aparat_username).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Store in GLOBAL cookie (not per-channel)
    viewer_data = json.dumps({"name": name, "phone": phone})
    
    response = JSONResponse({"success": True})
    
    # Set GLOBAL cookie (valid for 4 months) - not per-channel
    # httponly=False so JavaScript can read it for display purposes
    response.set_cookie(
        key="viewer_data",  # Global cookie name
        value=viewer_data,
        max_age=settings.COOKIE_EXPIRY,
        domain=settings.COOKIE_DOMAIN if not settings.DEV_MODE else None,
        secure=settings.COOKIE_SECURE,
        httponly=False,  # Allow JavaScript to read for display
        samesite=settings.COOKIE_SAME_SITE,
        path="/"  # Available for all paths
    )
    
    return response


@router.get("/api/stats/{stream_id}")
async def get_stream_stats(stream_id: int, db: Session = Depends(get_db)):
    """
    Get stream statistics
    """
    stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    online_count = db.query(Viewer).filter(
        Viewer.stream_id == stream_id,
        Viewer.left_at.is_(None)
    ).count()
    
    total_viewers = db.query(Viewer).filter(Viewer.stream_id == stream_id).count()
    
    return {
        "stream_id": stream_id,
        "online": online_count,
        "total": total_viewers,
        "status": stream.status
    }


@router.post("/api/c/{aparat_username}/comments")
async def submit_comment(
    aparat_username: str,
    request: Request,
    message: str,
    db: Session = Depends(get_db)
):
    """
    Submit a comment to live stream
    Requires viewer registration (cookie)
    """
    import json
    from app.utils.datetime_utils import now_tehran
    
    # Get channel
    channel = db.query(Channel).filter(Channel.aparat_username == aparat_username).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get current or scheduled stream (allow comments 30 min before start to 5 min after end)
    from datetime import timedelta
    from app.utils.datetime_utils import to_tehran
    
    now = now_tehran()
    
    # Try to find stream in valid time window
    # 30 minutes before start to 5 minutes after end
    stream = db.query(StreamSchedule).filter(
        StreamSchedule.channel_id == channel.id,
        StreamSchedule.status.in_(["scheduled", "live", "ended"])
    ).order_by(StreamSchedule.start_time.desc()).first()
    
    if not stream:
        raise HTTPException(status_code=404, detail="No stream found")
    
    # Check time window: 30 minutes before start to 5 minutes after end
    stream_start = to_tehran(stream.start_time)
    time_before_start = (stream_start - now).total_seconds()
    
    if stream.status == "ended":
        # For ended streams, check if within 5 minutes after end
        if stream.ended_at:
            stream_end = to_tehran(stream.ended_at)
            time_after_end = (now - stream_end).total_seconds()
            if time_after_end > 300:  # More than 5 minutes
                raise HTTPException(status_code=400, detail="Comments closed: stream ended more than 5 minutes ago")
        else:
            # Fallback: check if more than duration + 5 minutes has passed
            if stream.duration:
                estimated_end = stream_start + timedelta(seconds=stream.duration)
                time_after_end = (now - estimated_end).total_seconds()
                if time_after_end > 300:
                    raise HTTPException(status_code=400, detail="Comments closed: stream ended")
    elif stream.status == "scheduled":
        # For scheduled streams, check if within 30 minutes before start
        if time_before_start > 1800:  # More than 30 minutes
            raise HTTPException(status_code=400, detail="Comments not yet open: too early (must be within 30 minutes of start)")
        if time_before_start < 0:
            # Stream should have started but status not updated yet
            pass
    
    if not stream.allow_comments:
        raise HTTPException(status_code=403, detail="Comments are disabled")
    
    # Get viewer from GLOBAL cookie (not per-channel)
    viewer_cookie = request.cookies.get("viewer_data")  # Global cookie
    if not viewer_cookie:
        raise HTTPException(status_code=401, detail="Please register first")
    
    try:
        viewer_data = json.loads(viewer_cookie)
        username = viewer_data.get("name", "ناشناس")
        phone = viewer_data.get("phone")
    except:
        raise HTTPException(status_code=400, detail="Invalid viewer data")
    
    # Create comment (pending approval - will be published after 15 seconds if approved)
    from datetime import timedelta
    comment = Comment(
        stream_id=stream.id,
        username=username,
        phone=phone,
        message=message,
        approved=False,  # Requires moderation
        ip_address=request.client.host if request.client else None,
        published_at=now + timedelta(seconds=15)  # Auto-approve after 15 seconds
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Schedule auto-approval after 15 seconds
    try:
        import redis
        from app.core.config import settings
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
        import json
        
        # Store comment in Redis for auto-approval
        sid = str(stream.id)
        idxKey = f"comments:index:{sid}"
        dataKey = f"comments:data:{sid}"
        
        published_at_timestamp = int(comment.published_at.timestamp() * 1000)
        
        comment_data = {
            "id": comment.id,
            "username": comment.username,
            "message": comment.message,
            "timestamp": published_at_timestamp
        }
        
        comment_json = json.dumps(comment_data)
        redis_client.hset(dataKey, str(comment.id), comment_json)
        redis_client.zadd(idxKey, {str(comment.id): published_at_timestamp})
        
        print(f"[COMMENT] Comment {comment.id} scheduled for auto-approval at {comment.published_at}")
    except Exception as e:
        print(f"[COMMENT] Error scheduling auto-approval: {e}")
    
    # Notify WebSocket connections about new comment
    try:
        from app.routers.websocket import notify_new_comment
        import asyncio
        asyncio.create_task(notify_new_comment(stream.id, comment))
    except Exception as e:
        print(f"[COMMENT] Error notifying WebSocket: {e}")
    
    # Return comment data so user can see it immediately
    return {
        "success": True,
        "comment": {
            "id": comment.id,
            "username": comment.username,
            "message": comment.message,
            "timestamp": int(comment.created_at.timestamp() * 1000),
            "approved": False,
            "status": "pending"
        },
        "message": "Comment submitted, will be published after 15 seconds"
    }

