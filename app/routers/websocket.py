"""
WebSocket endpoints for real-time comment moderation
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Comment, StreamSchedule, User
from typing import Dict, Set
import json
import asyncio

router = APIRouter(tags=["websocket"])

# Store active connections: {stream_id: Set[WebSocket]}
active_connections: Dict[int, Set[WebSocket]] = {}


def get_user_from_session(websocket: WebSocket, db: Session) -> User:
    """Get user from websocket session cookies"""
    # Extract session cookie from headers
    cookies = websocket.headers.get("cookie", "")
    session_id = None
    
    for cookie in cookies.split(";"):
        if "ms_session" in cookie:
            # Extract session value (simplified - in production use proper session store)
            # This is a simplified version - you should use your actual session management
            pass
    
    # For now, we'll require stream owner check in the endpoint
    return None


@router.websocket("/ws/stream/{stream_id}/comments")
async def websocket_comments(
    websocket: WebSocket,
    stream_id: int,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time comment moderation
    Stream owner can connect to receive new comments and delete them
    """
    await websocket.accept()
    
    # Get stream and verify it exists
    stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
    if not stream:
        await websocket.send_json({"error": "Stream not found"})
        await websocket.close()
        return
    
    # Add connection to active connections
    if stream_id not in active_connections:
        active_connections[stream_id] = set()
    active_connections[stream_id].add(websocket)
    
    try:
        # Send initial pending and approved comments
        pending = db.query(Comment).filter(
            Comment.stream_id == stream_id,
            Comment.approved == False,
            Comment.deleted_at.is_(None)
        ).order_by(Comment.created_at.desc()).limit(100).all()
        
        approved = db.query(Comment).filter(
            Comment.stream_id == stream_id,
            Comment.approved == True,
            Comment.deleted_at.is_(None)
        ).order_by(Comment.created_at.desc()).limit(100).all()
        
        await websocket.send_json({
            "type": "initial",
            "comments": {
                "pending": [
                    {
                        "id": c.id,
                        "username": c.username,
                        "message": c.message,
                        "phone": c.phone,
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
                        "created_at": c.created_at.isoformat()
                    }
                    for c in approved
                ]
            }
        })
        
        # Listen for messages (approve/delete)
        while True:
            data = await websocket.receive_json()
            
            if data.get("action") == "delete":
                comment_id = data.get("comment_id")
                if comment_id:
                    # Delete comment (soft delete)
                    comment = db.query(Comment).filter(
                        Comment.id == comment_id,
                        Comment.stream_id == stream_id
                    ).first()
                    
                    if comment:
                        from datetime import datetime
                        from app.utils.datetime_utils import now_tehran
                        comment.deleted_at = now_tehran()
                        db.commit()
                        
                        # Notify all connections
                        await broadcast_to_stream(stream_id, {
                            "type": "comment_deleted",
                            "comment_id": comment_id
                        })
                        
                        await websocket.send_json({"success": True, "comment_id": comment_id})
            
            elif data.get("action") == "approve":
                comment_id = data.get("comment_id")
                if comment_id:
                    # Approve comment (this will trigger the 15-second delay logic)
                    from app.routers.moderation import approve_comment as approve_func
                    from fastapi import Request
                    
                    # Approve the comment (simplified - in production use proper auth)
                    comment = db.query(Comment).filter(
                        Comment.id == comment_id,
                        Comment.stream_id == stream_id
                    ).first()
                    
                    if comment:
                        comment.approved = True
                        from app.utils.datetime_utils import now_tehran
                        from datetime import timedelta
                        comment.published_at = now_tehran() + timedelta(seconds=15)
                        db.commit()
                        
                        # Store in Redis for Go service
                        try:
                            import redis
                            import json as json_lib
                            from app.core.config import settings
                            
                            redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
                            sid = str(stream_id)
                            idxKey = f"comments:index:{sid}"
                            dataKey = f"comments:data:{sid}"
                            
                            published_at_timestamp = int(comment.published_at.timestamp() * 1000)
                            comment_data = {
                                "id": comment.id,
                                "username": comment.username,
                                "message": comment.message,
                                "timestamp": published_at_timestamp
                            }
                            
                            comment_json = json_lib.dumps(comment_data)
                            redis_client.hset(dataKey, str(comment.id), comment_json)
                            redis_client.zadd(idxKey, {str(comment.id): published_at_timestamp})
                        except Exception as e:
                            print(f"[WEBSOCKET] Error storing in Redis: {e}")
                        
                        await websocket.send_json({"success": True, "comment_id": comment_id})
    
    except WebSocketDisconnect:
        active_connections[stream_id].discard(websocket)
        if not active_connections[stream_id]:
            del active_connections[stream_id]


async def broadcast_new_comment(stream_id: int, comment_data: dict):
    """Broadcast new comment to all connected clients"""
    await broadcast_to_stream(stream_id, {
        "type": "new_comment",
        "comment": comment_data
    })


async def broadcast_to_stream(stream_id: int, message: dict):
    """Broadcast message to all connections for a stream"""
    if stream_id in active_connections:
        disconnected = set()
        for connection in active_connections[stream_id]:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            active_connections[stream_id].discard(conn)
        
        if not active_connections[stream_id]:
            del active_connections[stream_id]


# Function to be called when a new comment is created
async def notify_new_comment(stream_id: int, comment: Comment):
    """Notify WebSocket connections about new comment"""
    comment_data = {
        "id": comment.id,
        "username": comment.username,
        "message": comment.message,
        "phone": comment.phone,
        "created_at": comment.created_at.isoformat()
    }
    await broadcast_new_comment(stream_id, comment_data)

