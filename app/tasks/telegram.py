"""
Celery tasks for Telegram notifications
"""
from celery import shared_task
from app.utils.telegram import send_message
from app.core.config import settings

@shared_task(queue='default')
def send_telegram_notification(chat_id: str, message: str, reply_markup: dict = None):
    """
    Send Telegram notification
    """
    if not settings.TELEGRAM_ENABLED:
        return {"success": False, "error": "Telegram disabled"}
    
    result = send_message(chat_id, message, reply_markup)
    return result


@shared_task(queue='default')
def notify_new_video(video_id: int, user_id: int):
    """
    Notify admins about new video upload
    """
    if not settings.FEATURE_TELEGRAM_NOTIFICATIONS:
        return {"success": False, "error": "Notifications disabled"}
    
    message = f"ویدیوی جدید آپلود شده:\n\nID: {video_id}\nUser: {user_id}"
    
    # Send to all admin chat IDs
    admin_ids = settings.TELEGRAM_ADMIN_IDS.split(",") if settings.TELEGRAM_ADMIN_IDS else []
    
    for chat_id in admin_ids:
        if chat_id.strip():
            send_message(chat_id.strip(), message)
    
    return {"success": True}

