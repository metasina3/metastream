"""
Cleanup tasks for old/rejected data
"""
from celery import shared_task
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.channel import Channel
from app.models.video import Video


@shared_task(name="app.tasks.cleanup.cleanup_rejected_channels")
def cleanup_rejected_channels():
    """
    Delete rejected channels older than 24 hours
    """
    db = SessionLocal()
    try:
        threshold = datetime.utcnow() - timedelta(hours=24)
        rejected = db.query(Channel).filter(
            Channel.status == "rejected",
            Channel.approved_at < threshold
        ).all()
        
        count = len(rejected)
        for channel in rejected:
            db.delete(channel)
        
        db.commit()
        print(f"[CLEANUP] Deleted {count} rejected channels older than 24 hours")
        return {"success": True, "deleted_count": count}
    except Exception as e:
        db.rollback()
        print(f"[CLEANUP] Error deleting rejected channels: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(name="app.tasks.cleanup.cleanup_old_viewers")
def cleanup_old_viewers():
    """Clean up old viewer sessions (placeholder for future implementation)"""
    pass


@shared_task(name="app.tasks.cleanup.cleanup_old_comments")
def cleanup_old_comments():
    """Clean up old comments (placeholder for future implementation)"""
    pass


@shared_task(name="app.tasks.cleanup.cleanup_rejected_videos")
def cleanup_rejected_videos():
    """
    Delete rejected videos older than 24 hours
    """
    db = SessionLocal()
    try:
        threshold = datetime.utcnow() - timedelta(hours=24)
        rejected = db.query(Video).filter(
            Video.status == "rejected"
        ).all()
        
        # Filter in Python because we need to check if approved_at exists and is old enough
        to_delete = []
        for v in rejected:
            # Check if video has been in rejected state for > 24 hours
            # We use created_at as fallback if no approval record exists
            check_time = v.created_at
            # If we later add approved_at to Video model, use that
            if check_time and (datetime.utcnow() - check_time) > timedelta(hours=24):
                to_delete.append(v)
        
        count = len(to_delete)
        for video in to_delete:
            # Delete physical files
            import os
            if video.original_file and os.path.exists(video.original_file):
                try:
                    os.remove(video.original_file)
                except Exception:
                    pass
            if video.processed_file and os.path.exists(video.processed_file):
                try:
                    os.remove(video.processed_file)
                except Exception:
                    pass
            # Delete DB record
            db.delete(video)
        
        db.commit()
        print(f"[CLEANUP] Deleted {count} rejected videos older than 24 hours")
        return {"success": True, "deleted_count": count}
    except Exception as e:
        db.rollback()
        print(f"[CLEANUP] Error deleting rejected videos: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()
