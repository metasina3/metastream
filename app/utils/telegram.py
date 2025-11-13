"""
Telegram bot utilities
"""
import requests
from app.core.config import settings
from typing import Optional
from sqlalchemy.orm import Session

def get_proxy_config() -> Optional[dict]:
    """
    Get proxy configuration for Telegram requests
    For Docker containers, converts localhost to host.docker.internal
    Handles proxy URLs with authentication (user:pass@host:port)
    """
    if settings.TELEGRAM_PROXY_HTTP:
        proxy_url = settings.TELEGRAM_PROXY_HTTP
        # If running in Docker and proxy is localhost, use host.docker.internal
        if proxy_url.startswith("http://localhost:") or proxy_url.startswith("https://localhost:"):
            proxy_url = proxy_url.replace("localhost", "host.docker.internal")
        # URL encoding is handled by requests library automatically
        return {"http": proxy_url, "https": proxy_url}
    elif settings.TELEGRAM_PROXY_SOCKS5:
        proxy_url = settings.TELEGRAM_PROXY_SOCKS5
        # If running in Docker and proxy is localhost, use host.docker.internal
        if proxy_url.startswith("socks5://localhost:") or proxy_url.startswith("socks5h://localhost:"):
            proxy_url = proxy_url.replace("localhost", "host.docker.internal")
        return {"http": proxy_url, "https": proxy_url}
    return None

def send_message(chat_id: str, message: str, reply_markup: Optional[dict] = None) -> dict:
    """
    Send message to Telegram
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "Telegram disabled"}
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    try:
        proxies = get_proxy_config()
        response = requests.post(url, json=data, proxies=proxies, timeout=30)
        response.raise_for_status()
        
        return {"success": True, "message_id": response.json().get("result", {}).get("message_id")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_file_to_telegram(file_path: str, chat_id: str) -> dict:
    """
    Send file to Telegram
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "Telegram disabled"}
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
    
    try:
        proxies = get_proxy_config()
        
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id}
            response = requests.post(url, files=files, data=data, proxies=proxies, timeout=60)
            response.raise_for_status()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_approval_notification(approval_id: int, approval_type: str, entity_id: int, db: Session, user_name: Optional[str] = None) -> dict:
    """
    Send approval notification to Telegram admins with inline buttons and detailed information
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "Telegram disabled"}
    
    if not settings.TELEGRAM_ADMIN_IDS:
        return {"success": False, "error": "No admin IDs configured"}
    
    # Import models
    from app.models.video import Video
    from app.models.channel import Channel
    from app.models.user import User
    from app.utils.ffmpeg import format_duration
    
    # Build message with details
    type_label = "ویدیو" if approval_type == "video" else "کانال"
    message = f"🔔 <b>درخواست تایید جدید</b>\n\n"
    message += f"📋 نوع: {type_label}\n"
    message += f"📝 درخواست ID: {approval_id}\n\n"
    
    if approval_type == "video":
        # Get video details
        video = db.query(Video).filter(Video.id == entity_id).first()
        if video:
            message += f"🎬 <b>عنوان:</b> {video.title}\n"
            message += f"🆔 ویدیو ID: {video.id}\n"
            
            # Duration
            if video.duration and video.duration > 0:
                duration_str = format_duration(video.duration)
                message += f"⏱️ <b>مدت زمان:</b> {duration_str}\n"
            else:
                message += f"⏱️ <b>مدت زمان:</b> نامشخص\n"
            
            # File size
            if video.file_size and video.file_size > 0:
                size_mb = round(video.file_size / (1024 * 1024), 2)
                message += f"💾 <b>حجم:</b> {size_mb} MB\n"
            
            # User info
            if video.user_id:
                user = db.query(User).filter(User.id == video.user_id).first()
                if user:
                    message += f"\n👤 <b>کاربر درخواست‌دهنده:</b>\n"
                    message += f"   • نام: {user.name or 'بدون نام'}\n"
                    message += f"   • ایمیل: {user.email or 'ندارد'}\n"
                    message += f"   • موبایل: {user.phone or 'ندارد'}\n"
                    message += f"   • User ID: {user.id}\n"
        else:
            message += f"⚠️ ویدیو با ID {entity_id} یافت نشد\n"
    
    elif approval_type == "channel":
        # Get channel details
        channel = db.query(Channel).filter(Channel.id == entity_id).first()
        if channel:
            message += f"📺 <b>نام کانال:</b> {channel.name}\n"
            message += f"🆔 کانال ID: {channel.id}\n"
            message += f"🔗 <b>یوزر آپارات:</b> @{channel.aparat_username}\n"
            message += f"🌐 <b>لینک آپارات:</b> https://www.aparat.com/{channel.aparat_username}\n"
            
            # User info
            if channel.user_id:
                user = db.query(User).filter(User.id == channel.user_id).first()
                if user:
                    message += f"\n👤 <b>کاربر درخواست‌دهنده:</b>\n"
                    message += f"   • نام: {user.name or 'بدون نام'}\n"
                    message += f"   • ایمیل: {user.email or 'ندارد'}\n"
                    message += f"   • موبایل: {user.phone or 'ندارد'}\n"
                    message += f"   • User ID: {user.id}\n"
        else:
            message += f"⚠️ کانال با ID {entity_id} یافت نشد\n"
    
    # Create inline keyboard
    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "✅ تایید",
                    "callback_data": f"approve_{approval_id}"
                },
                {
                    "text": "❌ رد",
                    "callback_data": f"reject_{approval_id}"
                }
            ]
        ]
    }
    
    # Send to all admin chat IDs
    admin_ids = settings.TELEGRAM_ADMIN_IDS.split(",") if settings.TELEGRAM_ADMIN_IDS else []
    results = []
    
    for chat_id in admin_ids:
        if chat_id.strip():
            result = send_message(chat_id.strip(), message, reply_markup)
            results.append(result)
    
    return {"success": True, "results": results}

