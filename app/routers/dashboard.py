"""
User Dashboard endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
import os
from fastapi import Header
from app.models import User, Channel, Video, StreamSchedule, Comment
from typing import List
from datetime import datetime
from app.utils.datetime_utils import now_tehran, to_tehran, format_datetime_persian
import time

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current logged-in user"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.get("/test")
async def test_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Test endpoint to debug video loading"""
    session_user_id = request.session.get("user_id")
    videos_count = db.query(Video).filter(Video.user_id == user.id).count()
    all_videos = db.query(Video).filter(Video.user_id == user.id).all()
    return {
        "session_user_id": session_user_id,
        "current_user_id": user.id,
        "current_user_name": user.name,
        "videos_count": videos_count,
        "videos": [
            {"id": v.id, "title": v.title, "status": v.status, "user_id": v.user_id}
            for v in all_videos
        ]
    }

@router.get("/")
async def dashboard_data(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get dashboard data for current user
    """
    # Get session user_id for debugging
    session_user_id = request.session.get("user_id")
    impersonating = bool(request.session.get("original_user_id"))
    
    # Get ALL channels for this user, regardless of status
    channels = db.query(Channel).filter(Channel.user_id == user.id).order_by(Channel.created_at.desc()).all()
    channels_count = len(channels)
    
    # Get ALL videos for this user, regardless of status
    videos_query = db.query(Video).filter(Video.user_id == user.id)
    videos_count = videos_query.count()
    videos = videos_query.order_by(Video.created_at.desc()).all()
    streams = db.query(StreamSchedule).filter(StreamSchedule.user_id == user.id).all()
    
    # Force print to stderr so it appears in logs
    import sys
    sys.stderr.write(f"[DASHBOARD] User {user.id} ({user.name}): session_user_id={session_user_id}, impersonating={impersonating}\n")
    sys.stderr.write(f"[DASHBOARD] Found {channels_count} channels, {videos_count} videos for user {user.id}\n")
    for c in channels:
        sys.stderr.write(f"  ✓ Channel {c.id}: '{c.name}' (status={c.status}, user_id={c.user_id})\n")
    for v in videos:
        sys.stderr.write(f"  ✓ Video {v.id}: '{v.title}' (status={v.status}, duration={v.duration}, user_id={v.user_id})\n")
    
    # Build response with ALL fields
    videos_list = []
    for v in videos:
        videos_list.append({
            "id": v.id,
            "title": v.title,
            "status": v.status,
            "created_at": to_tehran(v.created_at).isoformat() if v.created_at else None,
            "processed_file": v.processed_file,
            "original_file": v.original_file,
            "duration": v.duration or 0,
            "file_size": v.file_size or 0,
        })
    
    channels_list = []
    for c in channels:
        channels_list.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "status": c.status,
            "aparat_username": c.aparat_username,
            "aparat_link": f"https://www.aparat.com/{c.aparat_username}",
            "created_at": to_tehran(c.created_at).isoformat() if c.created_at else None,
        })
    
    response_data = {
        "user": {"id": user.id, "phone": user.phone, "name": user.name, "email": user.email},
        "channels": channels_list,
        "videos": videos_list,
        "streams": [{"id": s.id, "title": s.title, "status": s.status} for s in streams],
    }
    


    return response_data


# ============================================================================
# Stream Management
# ============================================================================

@router.post("/streams")
async def create_stream(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Create a new scheduled stream
    """
    from datetime import timedelta
    from app.utils.datetime_utils import to_tehran
    import uuid
    
    try:
        data = await request.json()
        if data is None:
            raise HTTPException(status_code=400, detail="Request body is empty")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
    # Validate required fields
    video_id = data.get("video_id")
    channel_id = data.get("channel_id")
    title = data.get("title", "").strip()
    caption = data.get("caption", "").strip()
    start_time_str = data.get("start_time")
    allow_comments = data.get("allow_comments", True)
    
    if not all([video_id, channel_id, title, start_time_str]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Parse start_time
    # Input should be ISO string, possibly with timezone
    # If no timezone, assume it's already in Tehran timezone (from frontend)
    try:
        from dateutil import parser
        from zoneinfo import ZoneInfo
        
        # Parse the ISO string
        start_time = parser.isoparse(start_time_str)
        
        # If timezone is not specified, assume it's in Tehran timezone
        if start_time.tzinfo is None:
            # Treat as Tehran time
            tehran_tz = ZoneInfo("Asia/Tehran")
            start_time = start_time.replace(tzinfo=tehran_tz)
        else:
            # Convert to Tehran timezone
            start_time = to_tehran(start_time)
        
        # Ensure we have timezone-aware datetime in Tehran
        if start_time.tzinfo != ZoneInfo("Asia/Tehran"):
            start_time = to_tehran(start_time)
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid start_time: {e}")
    
    # Check minimum 2 minutes from now
    now = now_tehran()
    min_start_time = now + timedelta(minutes=2)
    if start_time < min_start_time:
        raise HTTPException(
            status_code=400,
            detail=f"Start time must be at least 2 minutes from now"
        )
    
    # Verify video
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == user.id,
        Video.status == "ready"
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found or not ready")
    
    # Verify channel
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.user_id == user.id,
        Channel.status == "approved"
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found or not approved")
    
    # Check if there's a recently ended stream (within 5 minutes)
    now = now_tehran()
    recent_ended = db.query(StreamSchedule).filter(
        StreamSchedule.channel_id == channel_id,
        StreamSchedule.status == "ended",
        StreamSchedule.ended_at.isnot(None)
    ).order_by(StreamSchedule.ended_at.desc()).first()
    
    if recent_ended and recent_ended.ended_at:
        ended_at_tehran = to_tehran(recent_ended.ended_at)
        time_since_end = (now - ended_at_tehran).total_seconds()
        if time_since_end < 300:  # Less than 5 minutes
            remaining_seconds = int(300 - time_since_end)
            remaining_minutes = remaining_seconds // 60
            remaining_secs = remaining_seconds % 60
            next_available = ended_at_tehran + timedelta(seconds=300)
            jalali_time = next_available.strftime("%H:%M:%S")
            jalali_date = next_available.strftime("%Y/%m/%d")
            raise HTTPException(
                status_code=400,
                detail=f"کانال مشغول است. لطفاً {remaining_minutes} دقیقه و {remaining_secs} ثانیه صبر کنید. زمان مجاز بعدی: {jalali_time} - {jalali_date}"
            )
    
    # Calculate end time
    video_duration = video.duration or 0
    end_time = start_time + timedelta(seconds=video_duration)
    buffer_time = end_time + timedelta(minutes=5)
    
    # Check for overlapping streams
    overlapping = db.query(StreamSchedule).filter(
        StreamSchedule.channel_id == channel_id,
        StreamSchedule.status.in_(["scheduled", "live"])
    ).all()
    
    for existing in overlapping:
        existing_start = to_tehran(existing.start_time)
        existing_end = existing_start + timedelta(seconds=existing.duration) + timedelta(minutes=5)
        
        # Check if new stream overlaps
        if start_time < existing_end and buffer_time > existing_start:
            raise HTTPException(
                status_code=400,
                detail=f"Channel is busy. Next available: {existing_end.isoformat()}"
            )
    
    # Generate unique slug
    unique_slug = f"{channel.slug}-{uuid.uuid4().hex[:8]}"
    
    # Create stream
    stream = StreamSchedule(
        user_id=user.id,
        channel_id=channel_id,
        video_id=video_id,
        title=title,
        caption=caption or None,
        start_time=start_time,
        duration=video_duration,
        status="scheduled",
        allow_comments=allow_comments,
        slug=unique_slug
    )
    
    db.add(stream)
    db.commit()
    db.refresh(stream)
    
    play_link = f"{settings.LIVE_URL}/c/{channel.aparat_username}"
    
    return {
        "id": stream.id,
        "slug": stream.slug,
        "title": stream.title,
        "play_link": play_link
    }


@router.get("/streams")
async def get_streams(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get all streams for current user
    """
    streams = db.query(StreamSchedule).filter(
        StreamSchedule.user_id == user.id
    ).order_by(StreamSchedule.start_time.desc()).all()
    
    result = []
    for s in streams:
        channel = db.query(Channel).filter(Channel.id == s.channel_id).first()
        video = db.query(Video).filter(Video.id == s.video_id).first()
        
        play_link = f"{settings.LIVE_URL}/c/{channel.aparat_username}" if channel else ""
        
        result.append({
            "id": s.id,
            "slug": s.slug,
            "title": s.title,
            "caption": s.caption,
            "start_time": to_tehran(s.start_time).isoformat(),
            "duration": s.duration,
            "status": s.status,
            "error_message": s.error_message,  # Include error message if exists
            "allow_comments": s.allow_comments,
            "viewers_count": s.viewers_count,
            "max_viewers": s.max_viewers,
            "play_link": play_link,
            "started_at": to_tehran(s.started_at).isoformat() if s.started_at else None,
            "ended_at": to_tehran(s.ended_at).isoformat() if s.ended_at else None,
            "channel": {
                "id": channel.id,
                "name": channel.name,
                "slug": channel.slug
            } if channel else None,
            "video": {
                "id": video.id,
                "title": video.title,
                "duration": video.duration
            } if video else None,
            "created_at": to_tehran(s.created_at).isoformat()
        })
    
    return {"streams": result}


@router.post("/streams/{stream_id}/cancel")
async def cancel_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Cancel a scheduled stream (only for scheduled status)
    """
    stream = db.query(StreamSchedule).filter(
        StreamSchedule.id == stream_id,
        StreamSchedule.user_id == user.id
    ).first()
    
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Allow canceling scheduled and live streams
    if stream.status not in ["scheduled", "live"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel stream with status: {stream.status}. Only scheduled or live streams can be cancelled."
        )
    
    # If stream is live, we need to kill the FFmpeg process
    if stream.status == "live":
        print(f"[DASHBOARD] Cancelling live stream {stream_id}, killing FFmpeg process...")
        try:
            import redis
            import signal
            import os
            redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            pid_key = f"stream:pid:{stream_id}"
            pid_str = redis_client.get(pid_key)
            
            if pid_str:
                pid = int(pid_str)
                print(f"[DASHBOARD] Found FFmpeg PID {pid} in Redis, killing process...")
                try:
                    # Try to kill the process group (FFmpeg and its children)
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    print(f"[DASHBOARD] Sent SIGTERM to process group {pid}")
                    # Wait a bit, then force kill if still alive
                    time.sleep(2)
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                        print(f"[DASHBOARD] Sent SIGKILL to process group {pid}")
                    except ProcessLookupError:
                        print(f"[DASHBOARD] Process {pid} already terminated")
                except ProcessLookupError:
                    print(f"[DASHBOARD] Process {pid} not found (may have already terminated)")
                except PermissionError:
                    print(f"[DASHBOARD] Permission denied killing process {pid}")
                except Exception as kill_error:
                    print(f"[DASHBOARD] Error killing process {pid}: {kill_error}")
                
                # Remove PID from Redis
                redis_client.delete(pid_key)
                print(f"[DASHBOARD] Removed PID from Redis")
            else:
                print(f"[DASHBOARD] No PID found in Redis for stream {stream_id}")
        except Exception as redis_error:
            print(f"[DASHBOARD] Warning: Could not kill FFmpeg process: {redis_error}")
            # Continue anyway - mark as cancelled
    
    stream.status = "cancelled"
    stream.ended_at = now_tehran()
    db.commit()
    
    return {"success": True, "message": "Stream cancelled successfully"}


@router.post("/streams/{stream_id}/toggle-comments")
async def toggle_stream_comments(
    stream_id: int,
    enabled: bool = Query(True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Toggle comments for a stream (enable/disable)
    Can be toggled for scheduled, live, and ended streams
    """
    stream = db.query(StreamSchedule).filter(
        StreamSchedule.id == stream_id,
        StreamSchedule.user_id == user.id
    ).first()
    
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Allow toggling for scheduled, live, and ended streams (not cancelled)
    if stream.status == "cancelled":
        raise HTTPException(
            status_code=400, 
            detail="Cannot toggle comments for cancelled streams"
        )
    
    stream.allow_comments = enabled
    db.commit()
    db.refresh(stream)
    
    # Update Redis cache for Go service - IMPORTANT: must be set correctly
    try:
        import redis
        from app.core.config import settings
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as e:
        print(f"[DASHBOARD] ⚠️ Could not create Redis client: {e}")
        redis_client = None
    
    if redis_client:
        try:
            cache_key = f"stream:allow_comments:{stream_id}"
            # Use "1" for true, "0" for false
            value = "1" if enabled else "0"
            redis_client.setex(cache_key, 3600 * 24, value)  # Cache for 24 hours (longer expiry)
            print(f"[DASHBOARD] ✅ Updated Redis cache: {cache_key} = {value} (enabled={enabled})")
            
            # Verify it was set correctly
            verify_value = redis_client.get(cache_key)
            print(f"[DASHBOARD] ✅ Verified Redis value: {cache_key} = {verify_value}")
        except Exception as e:
            print(f"[DASHBOARD] ❌ Error updating Redis cache for allow_comments: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"[DASHBOARD] ⚠️ Redis client not available!")
    
    return {"success": True, "allow_comments": enabled}


@router.post("/channels")
async def create_channel(
    request: Request,
    name: str,
    aparat_input: str,  # Can be URL or username
    rtmp_url: str,
    rtmp_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Create a new channel
    Parse Aparat username from URL or use provided username
    """
    import re
    
    # Parse Aparat username from input
    aparat_username = None
    
    # Check if it's a URL
    if "aparat.com" in aparat_input:
        # Extract username from URL patterns:
        # https://www.aparat.com/metasina3/live
        # https://www.aparat.com/metasina3
        # http://aparat.com/metasina3
        match = re.search(r'aparat\.com/([^/]+)', aparat_input)
        if match:
            aparat_username = match.group(1)
    else:
        # It's just a username
        aparat_username = aparat_input.strip()
    
    if not aparat_username:
        raise HTTPException(status_code=400, detail="نام کاربری آپارات معتبر نیست")
    
    # Validate RTMP URL starts with rtmp://
    if not rtmp_url.startswith("rtmp://"):
        raise HTTPException(status_code=400, detail="آدرس RTMP باید با rtmp:// شروع شود")
    
    # Generate slug
    slug = name.lower().replace(" ", "-")
    
    # Check if aparat_username already exists (must be unique)
    existing_aparat = db.query(Channel).filter(Channel.aparat_username == aparat_username).first()
    if existing_aparat:
        raise HTTPException(status_code=400, detail=f"این نام کاربری آپارات قبلاً توسط کاربر دیگری استفاده شده است")
    
    # Check if slug already exists
    existing = db.query(Channel).filter(Channel.slug == slug).first()
    if existing:
        # Append random suffix
        import uuid
        slug = f"{slug}-{uuid.uuid4().hex[:8]}"
    
    channel = Channel(
        user_id=user.id,
        name=name,
        slug=slug,
        aparat_username=aparat_username,
        rtmp_url=rtmp_url,
        rtmp_key=rtmp_key,
        status="pending"
    )
    
    db.add(channel)
    db.commit()
    db.refresh(channel)
    # Create approval request for channel
    try:
        from app.models.approval import Approval
        a = Approval(type="channel", entity_id=channel.id, user_id=user.id, status="pending")
        db.add(a)
        db.commit()
    except Exception:
        db.rollback()
    
    return {"success": True, "channel_id": channel.id, "slug": channel.slug}


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Delete a channel
    """
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.user_id == user.id
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    db.delete(channel)
    db.commit()
    
    return {"success": True}


@router.post("/videos")
async def upload_video(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Simple upload: receive file and save in one request (no resume). For large files use chunked API.
    """
    try:
        # Ensure upload dir exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        filename = file.filename
        ext = filename.split('.')[-1] if '.' in filename else 'bin'
        import uuid
        out_name = f"{uuid.uuid4()}.{ext}"
        out_path = os.path.join(settings.UPLOAD_DIR, out_name)
        content = await file.read()
        with open(out_path, 'wb') as f:
            f.write(content)
        video = Video(
            user_id=user.id,
            title=title,
            original_file=out_path,
            status="pending",
            file_size=len(content)
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        # Kick off processing
        try:
            from app.tasks.video import prepare_video
            prepare_video.delay(video.id)
        except Exception:
            pass
        return {"success": True, "video_id": video.id}
    except HTTPException:
        raise
    except Exception as e:
        # Bubble clear message to client
        raise HTTPException(status_code=500, detail=f"upload_error: {type(e).__name__}: {str(e)}")


@router.post("/videos/upload-chunk")
async def upload_video_chunk(
    request: Request,
    upload_id: str = Header(..., alias="Upload-Id"),
    content_range: str | None = Header(None, alias="Content-Range"),
    file_name_header: str | None = Header(None, alias="X-File-Name"),
    file_total: int = Header(..., alias="X-File-Size"),
    chunk_index: int | None = Header(None, alias="X-Chunk-Index"),
    total_chunks: int | None = Header(None, alias="X-Total-Chunks"),
    filename_q: str | None = Query(None, alias="filename"),
    title: str | None = Query(None),  # عنوان ویدیو از query parameter
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Parallel chunked upload with support for multiple simultaneous connections.
    Optimized for slow networks with adaptive chunk size and QUIC/HTTP3 support.
    Headers:
      - Upload-Id: stable id for this file
      - Content-Range: bytes start-end/total (optional, for backward compatibility)
      - X-Chunk-Index: chunk index (0-based) for parallel upload
      - X-Total-Chunks: total number of chunks
      - X-File-Name, X-File-Size
    Body is raw binary for the chunk.
    """
    import json
    import uuid
    
    try:
        file_name = file_name_header or filename_q or "upload.bin"
        total = int(file_total)
        
        # Support both old sequential and new parallel mode
        if chunk_index is not None and total_chunks is not None:
            # Parallel mode: use chunk_index
            chunk_idx = int(chunk_index)
            total_chunks_count = int(total_chunks)
            
            if chunk_idx < 0 or chunk_idx >= total_chunks_count:
                raise HTTPException(status_code=400, detail=f"Invalid chunk_index: {chunk_idx}")
            
            # Calculate chunk size
            chunk_size = total // total_chunks_count
            start = chunk_idx * chunk_size
            end = start + chunk_size if chunk_idx < total_chunks_count - 1 else total
            
        elif content_range:
            # Sequential mode (backward compatibility)
            try:
                units, rng = content_range.split(' ')
                start_end, total_from_range = rng.split('/')
                start, end = start_end.split('-')
                start = int(start)
                end = int(end)
                total_from_range = int(total_from_range)
                if total_from_range != total:
                    raise HTTPException(status_code=400, detail="Size mismatch in Content-Range")
                chunk_idx = None
                total_chunks_count = None
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid Content-Range: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Either Content-Range or X-Chunk-Index required")
        
        # Paths for parallel chunks
        chunk_dir = os.path.join(settings.UPLOAD_DIR, 'chunks')
        os.makedirs(chunk_dir, exist_ok=True)
        
        if chunk_idx is not None:
            # Parallel mode: save each chunk separately
            chunk_file = os.path.join(chunk_dir, f"{upload_id}.chunk.{chunk_idx}")
            metadata_file = os.path.join(chunk_dir, f"{upload_id}.meta")
            
            # Read chunk data with timeout protection
            try:
                body = await request.body()
                received_size = len(body)
            except Exception as e:
                print(f"[UPLOAD] Error reading chunk body: {e}")
                raise HTTPException(status_code=400, detail=f"Error reading chunk data: {str(e)}")
            
            # Validate chunk size (allow small tolerance for last chunk)
            expected_size = end - start
            size_tolerance = 1024  # 1KB tolerance for last chunk
            if abs(received_size - expected_size) > size_tolerance:
                # Check if this is the last chunk (might be smaller)
                if chunk_idx == total_chunks_count - 1:
                    # Last chunk can be smaller
                    if received_size > expected_size:
                        raise HTTPException(status_code=400, detail=f"Chunk size mismatch: expected max {expected_size}, got {received_size}")
                else:
                    raise HTTPException(status_code=400, detail=f"Chunk size mismatch: expected {expected_size}, got {received_size}")
            
            # Save chunk with error handling
            try:
                with open(chunk_file, 'wb') as f:
                    f.write(body)
            except Exception as e:
                print(f"[UPLOAD] Error saving chunk {chunk_idx}: {e}")
                raise HTTPException(status_code=500, detail=f"Error saving chunk: {str(e)}")
            
            # Update metadata with file locking for concurrent access
            metadata = {}
            if os.path.exists(metadata_file):
                try:
                    # Retry reading metadata in case of concurrent access
                    for retry in range(3):
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            break
                        except (json.JSONDecodeError, IOError) as e:
                            if retry < 2:
                                import time
                                time.sleep(0.1)  # Wait 100ms before retry
                            else:
                                print(f"[UPLOAD] Error reading metadata after retries: {e}")
                                metadata = {}
                except Exception as e:
                    print(f"[UPLOAD] Error reading metadata: {e}")
                    metadata = {}
            
            if 'chunks' not in metadata:
                metadata['chunks'] = {}
                metadata['file_name'] = file_name
                metadata['title'] = title
                metadata['total_size'] = total
                metadata['total_chunks'] = total_chunks_count
                metadata['user_id'] = user.id
            
            metadata['chunks'][str(chunk_idx)] = {
                'received': True,
                'size': received_size,
                'start': start,
                'end': end
            }
            
            # Save metadata with error handling
            try:
                # Use atomic write (write to temp file then rename)
                temp_metadata_file = metadata_file + '.tmp'
                with open(temp_metadata_file, 'w') as f:
                    json.dump(metadata, f)
                os.replace(temp_metadata_file, metadata_file)
            except Exception as e:
                print(f"[UPLOAD] Error saving metadata: {e}")
                # Try to clean up temp file
                try:
                    if os.path.exists(metadata_file + '.tmp'):
                        os.remove(metadata_file + '.tmp')
                except:
                    pass
                # Don't fail the request if metadata save fails
                # The chunk is already saved, metadata can be reconstructed
            
            # Check if all chunks received
            # First check metadata, then verify chunk files exist
            received_chunks = len([c for c in metadata['chunks'].values() if c.get('received')])
            
            # Also check if chunk files exist (in case metadata wasn't saved properly)
            missing_chunks = []
            for i in range(total_chunks_count):
                chunk_file_path = os.path.join(chunk_dir, f"{upload_id}.chunk.{i}")
                if not os.path.exists(chunk_file_path):
                    missing_chunks.append(i)
                else:
                    # If file exists but not in metadata, mark it as received
                    if str(i) not in metadata['chunks'] or not metadata['chunks'][str(i)].get('received'):
                        metadata['chunks'][str(i)] = {
                            'received': True,
                            'size': os.path.getsize(chunk_file_path),
                            'start': i * (total // total_chunks_count),
                            'end': (i + 1) * (total // total_chunks_count) if i < total_chunks_count - 1 else total
                        }
                        # Try to save updated metadata
                        try:
                            temp_metadata_file = metadata_file + '.tmp'
                            with open(temp_metadata_file, 'w') as f:
                                json.dump(metadata, f)
                            os.replace(temp_metadata_file, metadata_file)
                        except Exception:
                            pass
            
            all_received = len(missing_chunks) == 0
            received_chunks = len([c for c in metadata['chunks'].values() if c.get('received')])
            
            if missing_chunks:
                print(f"[UPLOAD] Missing chunks: {missing_chunks[:10]}... (total missing: {len(missing_chunks)})")
            
            if all_received:
                # Merge all chunks
                print(f"[UPLOAD] All chunks received for {upload_id}, merging...")
                final_name = f"{uuid.uuid4()}.{file_name.split('.')[-1] if '.' in file_name else 'bin'}"
                final_path = os.path.join(settings.UPLOAD_DIR, final_name)
                
                # Merge chunks in order with error handling
                try:
                    with open(final_path, 'wb') as final_file:
                        for i in range(total_chunks_count):
                            chunk_file_path = os.path.join(chunk_dir, f"{upload_id}.chunk.{i}")
                            if not os.path.exists(chunk_file_path):
                                # Try to wait a bit for chunk to be written (concurrent access)
                                import time
                                waited = 0
                                while not os.path.exists(chunk_file_path) and waited < 5:
                                    time.sleep(0.5)
                                    waited += 0.5
                                
                                if not os.path.exists(chunk_file_path):
                                    raise HTTPException(status_code=500, detail=f"Missing chunk {i} after waiting")
                            
                            with open(chunk_file_path, 'rb') as cf:
                                chunk_data = cf.read()
                                if not chunk_data:
                                    raise HTTPException(status_code=500, detail=f"Empty chunk {i}")
                                final_file.write(chunk_data)
                            
                            # Clean up chunk file
                            try:
                                os.remove(chunk_file_path)
                            except Exception as e:
                                print(f"[UPLOAD] Warning: Could not remove chunk {i}: {e}")
                except Exception as e:
                    # Clean up partial file
                    try:
                        if os.path.exists(final_path):
                            os.remove(final_path)
                    except:
                        pass
                    raise HTTPException(status_code=500, detail=f"Error merging chunks: {str(e)}")
                
                # Clean up metadata
                try:
                    os.remove(metadata_file)
                except:
                    pass
                
                # Create video and trigger processing
                video = Video(
                    user_id=user.id,
                    title=title if title else file_name,
                    original_file=final_path,
                    status="pending",
                    file_size=total
                )
                db.add(video)
                db.commit()
                db.refresh(video)
                try:
                    from app.tasks.video import prepare_video
                    prepare_video.delay(video.id)
                except Exception:
                    pass
                
                print(f"[UPLOAD] Video {video.id} created from parallel upload")
                return {"success": True, "completed": True, "video_id": video.id, "chunk_index": chunk_idx}
            
            return {
                "success": True,
                "completed": False,
                "chunk_index": chunk_idx,
                "received_chunks": received_chunks,
                "total_chunks": total_chunks_count
            }
        
        else:
            # Sequential mode (backward compatibility)
            tmp_path = os.path.join(chunk_dir, upload_id + '.part')
            current_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
            
            if start != current_size:
                return {"success": False, "received": current_size, "detail": "Offset mismatch"}
            
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            body = await request.body()
            
            with open(tmp_path, 'ab') as f:
                f.write(body)
            
            current_size = os.path.getsize(tmp_path)
            completed = current_size >= total
            
            if completed:
                ext = file_name.split('.')[-1] if '.' in file_name else 'bin'
                final_name = f"{uuid.uuid4()}.{ext}"
                final_path = os.path.join(settings.UPLOAD_DIR, final_name)
                os.replace(tmp_path, final_path)
                
                video = Video(
                    user_id=user.id,
                    title=title if title else file_name,
                    original_file=final_path,
                    status="pending",
                    file_size=total
                )
                db.add(video)
                db.commit()
                db.refresh(video)
                try:
                    from app.tasks.video import prepare_video
                    prepare_video.delay(video.id)
                except Exception:
                    pass
                return {"success": True, "completed": True, "video_id": video.id}
            
            return {"success": True, "completed": False, "received": current_size}
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"chunk_error: {type(e).__name__}: {str(e)}")


@router.get("/videos/upload-status")
async def upload_status(upload_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Get upload status for resume capability.
    Supports both sequential and parallel modes.
    """
    import json
    
    chunk_dir = os.path.join(settings.UPLOAD_DIR, 'chunks')
    
    # Check for parallel mode metadata
    metadata_file = os.path.join(chunk_dir, f"{upload_id}.meta")
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            received_chunks = [int(k) for k, v in metadata.get('chunks', {}).items() if v.get('received')]
            total_chunks = metadata.get('total_chunks', 0)
            total_size = metadata.get('total_size', 0)
            
            # Calculate total received bytes
            received_bytes = sum(
                metadata['chunks'][str(i)].get('size', 0)
                for i in received_chunks
            )
            
            return {
                "exists": True,
                "received": received_bytes,
                "total_size": total_size,
                "received_chunks": received_chunks,
                "total_chunks": total_chunks,
                "mode": "parallel"
            }
        except Exception as e:
            print(f"[UPLOAD] Error reading metadata: {e}")
    
    # Check for sequential mode
    tmp_path = os.path.join(chunk_dir, upload_id + '.part')
    if os.path.exists(tmp_path):
        return {
            "exists": True,
            "received": os.path.getsize(tmp_path),
            "mode": "sequential"
        }
    
    return {"exists": False, "received": 0, "mode": "none"}


@router.put("/videos/{video_id}")
async def update_video_title(
    video_id: int,
    title: str = Form(..., min_length=1, max_length=255),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Update video title (no approval needed)
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Update title
    video.title = title
    db.commit()
    db.refresh(video)
    
    return {
        "success": True,
        "video": {
            "id": video.id,
            "title": video.title
        }
    }


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Delete a video and its physical files
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete physical files before deleting from database
    files_deleted = []
    try:
        # Delete original file
        if video.original_file and os.path.exists(video.original_file):
            try:
                os.remove(video.original_file)
                files_deleted.append(video.original_file)
                print(f"[DELETE] Removed original file: {video.original_file}")
            except Exception as e:
                print(f"[DELETE] Error removing original file {video.original_file}: {e}")
        
        # Delete processed file (if different from original)
        if video.processed_file and video.processed_file != video.original_file:
            if os.path.exists(video.processed_file):
                try:
                    os.remove(video.processed_file)
                    files_deleted.append(video.processed_file)
                    print(f"[DELETE] Removed processed file: {video.processed_file}")
                except Exception as e:
                    print(f"[DELETE] Error removing processed file {video.processed_file}: {e}")
    except Exception as e:
        print(f"[DELETE] Error during file deletion: {e}")
        # Continue with database deletion even if file deletion fails
    
    # Delete from database
    db.delete(video)
    db.commit()
    
    return {
        "success": True,
        "files_deleted": len(files_deleted),
        "message": f"Video deleted. {len(files_deleted)} file(s) removed."
    }


@router.get("/videos/{video_id}/play")
async def play_video(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Serve video file for playback with Range support (for seeking)
    """
    from fastapi.responses import FileResponse, StreamingResponse
    
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Use processed file if available, otherwise original
    video_file = None
    if video.processed_file and os.path.exists(video.processed_file):
        video_file = video.processed_file
    elif video.original_file and os.path.exists(video.original_file):
        video_file = video.original_file
    
    if not video_file:
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Determine media type from extension
    ext = video_file.split('.')[-1].lower() if '.' in video_file else 'mp4'
    media_types = {
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'mkv': 'video/x-matroska',
        'flv': 'video/x-flv',
    }
    media_type = media_types.get(ext, 'video/mp4')
    
    # Get file size
    file_size = os.path.getsize(video_file)
    
    # Check for Range header (for video seeking)
    range_header = request.headers.get('range')
    
    if range_header:
        # Parse range header: "bytes=start-end"
        range_match = range_header.replace('bytes=', '').split('-')
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
        
        # Ensure valid range
        if start >= file_size or end >= file_size or start > end:
            raise HTTPException(status_code=416, detail="Range not satisfiable")
        
        # Calculate chunk size
        chunk_size = end - start + 1
        
        # Create generator to read the chunk
        def iterfile():
            with open(video_file, 'rb') as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    chunk = f.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(chunk_size),
            'Content-Type': media_type,
        }
        
        return StreamingResponse(
            iterfile(),
            status_code=206,
            headers=headers,
            media_type=media_type
        )
    else:
        # No range, return full file with Accept-Ranges header
        return FileResponse(
            video_file,
            media_type=media_type,
            headers={'Accept-Ranges': 'bytes'}
        )


@router.post("/streams")
async def create_stream(
    request: Request,
    title: str,
    channel_id: int,
    video_id: int = None,
    start_time: str = None,
    allow_comments: bool = True,
    requires_otp: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Schedule a new stream
    """
    from datetime import datetime
    import uuid
    
    # Generate share link
    share_link = f"{settings.LIVE_URL}/c/{channel_id}/{uuid.uuid4().hex[:8]}"
    
    # Parse start_time
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    else:
        start_dt = datetime.utcnow()
    
    stream = StreamSchedule(
        user_id=user.id,
        channel_id=channel_id,
        video_id=video_id,
        title=title,
        start_time=start_dt,
        status="scheduled",
        allow_comments=allow_comments,
        requires_otp=requires_otp,
        share_link=share_link
    )
    
    db.add(stream)
    db.commit()
    db.refresh(stream)
    
    return {"success": True, "stream_id": stream.id, "share_link": share_link}


@router.get("/streams/{stream_id}/share-link")
async def get_share_link(
    stream_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get share link for stream
    """
    stream = db.query(StreamSchedule).filter(
        StreamSchedule.id == stream_id,
        StreamSchedule.user_id == user.id
    ).first()
    
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    return {"share_link": stream.share_link}

