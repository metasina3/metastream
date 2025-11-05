"""
Celery tasks for comment management
"""
from celery import shared_task
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import Comment
from app.utils.datetime_utils import now_tehran
from datetime import timedelta
import redis
import json
from app.core.config import settings


@shared_task(queue='default')
def auto_approve_comments():
    """
    Auto-approve comments that are 15 seconds old and haven't been deleted
    This should run every 5 seconds
    """
    db: Session = SessionLocal()
    try:
        now = now_tehran()
        
        # Find pending comments where published_at <= now (15 seconds after creation)
        # This means they should be auto-approved now
        pending_comments = db.query(Comment).filter(
            Comment.approved == False,
            Comment.deleted_at.is_(None),
            Comment.published_at.isnot(None),
            Comment.published_at <= now
        ).all()
        
        approved_count = 0
        for comment in pending_comments:
            try:
                # Approve the comment
                comment.approved = True
                db.commit()
                
                # Store in Redis for Go service
                try:
                    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
                    sid = str(comment.stream_id)
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
                    
                    print(f"[COMMENTS] Auto-approved comment {comment.id} for stream {comment.stream_id}")
                    approved_count += 1
                except Exception as redis_error:
                    print(f"[COMMENTS] Error storing comment {comment.id} in Redis: {redis_error}")
            except Exception as e:
                print(f"[COMMENTS] Error approving comment {comment.id}: {e}")
                db.rollback()
        
        if approved_count > 0:
            print(f"[COMMENTS] Auto-approved {approved_count} comments")
        
    except Exception as e:
        print(f"[COMMENTS] Error in auto_approve_comments: {e}")
    finally:
        db.close()

