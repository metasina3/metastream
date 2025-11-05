"""
Celery Tasks
"""
from .video import prepare_video
from .cleanup import cleanup_old_comments, cleanup_old_viewers, cleanup_rejected_videos
from .backup import backup_database
from .telegram import send_telegram_notification, notify_new_video
from .stream import check_and_start_streams, start_stream_task, stop_stream, check_live_streams
from .comments import auto_approve_comments

__all__ = [
    "prepare_video",
    "cleanup_old_comments",
    "cleanup_old_viewers",
    "cleanup_rejected_videos",
    "backup_database",
    "send_telegram_notification",
    "notify_new_video",
    "check_and_start_streams",
    "start_stream_task",
    "stop_stream",
    "check_live_streams",
    "auto_approve_comments",
]

