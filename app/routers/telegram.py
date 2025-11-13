"""
Telegram bot webhook and callback handlers
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.approval import Approval
from app.models.video import Video
from app.models.channel import Channel
from app.models.user import User
from app.utils.telegram import send_message
from datetime import datetime
from typing import Optional
import json

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/test")
async def test_telegram():
    """
    Test Telegram bot - send a test message to all admins
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Telegram disabled")
    
    if not settings.TELEGRAM_ADMIN_IDS:
        raise HTTPException(status_code=400, detail="No admin IDs configured")
    
    message = "🤖 <b>ربات تلگرام فعال است!</b>\n\n"
    message += "✅ ربات به درستی کار می‌کند\n"
    message += "📱 این یک پیام تست است\n\n"
    message += f"🔧 Proxy: {settings.TELEGRAM_PROXY_HTTP or 'None'}\n"
    message += f"👥 Admin IDs: {settings.TELEGRAM_ADMIN_IDS}"
    
    admin_ids = settings.TELEGRAM_ADMIN_IDS.split(",") if settings.TELEGRAM_ADMIN_IDS else []
    results = []
    
    for chat_id in admin_ids:
        if chat_id.strip():
            result = send_message(chat_id.strip(), message)
            results.append({"chat_id": chat_id.strip(), "result": result})
    
    return {
        "success": True,
        "message": "Test message sent",
        "results": results
    }


@router.post("/init")
async def init_telegram():
    """
    Initialize Telegram bot: set webhook and send test message
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Telegram disabled")
    
    results = {}
    
    # 1. Set webhook
    try:
        webhook_url = f"{settings.API_URL}/api/telegram/webhook"
        import requests
        from app.utils.telegram import get_proxy_config
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
        # Set webhook with allowed updates (messages and callback queries)
        data = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }
        
        proxies = get_proxy_config()
        response = requests.post(url, json=data, proxies=proxies, timeout=10)
        response.raise_for_status()
        
        webhook_result = response.json()
        results["webhook"] = {
            "success": True,
            "url": webhook_url,
            "result": webhook_result
        }
    except Exception as e:
        results["webhook"] = {
            "success": False,
            "error": str(e)
        }
    
    # 2. Send test message
    try:
        if not settings.TELEGRAM_ADMIN_IDS:
            results["test_message"] = {
                "success": False,
                "error": "No admin IDs configured"
            }
        else:
            message = "🚀 <b>ربات تلگرام راه‌اندازی شد!</b>\n\n"
            message += "✅ Webhook تنظیم شد\n"
            message += "✅ ربات آماده دریافت درخواست‌های تایید است\n\n"
            message += f"🔗 Webhook URL: {webhook_url}\n"
            message += f"👥 Admin IDs: {settings.TELEGRAM_ADMIN_IDS}"
            
            admin_ids = settings.TELEGRAM_ADMIN_IDS.split(",") if settings.TELEGRAM_ADMIN_IDS else []
            test_results = []
            
            for chat_id in admin_ids:
                if chat_id.strip():
                    result = send_message(chat_id.strip(), message)
                    test_results.append({"chat_id": chat_id.strip(), "result": result})
            
            results["test_message"] = {
                "success": True,
                "results": test_results
            }
    except Exception as e:
        results["test_message"] = {
            "success": False,
            "error": str(e)
        }
    
    return {
        "success": results.get("webhook", {}).get("success", False),
        "results": results
    }


@router.post("/set-webhook")
async def set_webhook(request: Request):
    """
    Set Telegram webhook URL (for admin use)
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Telegram disabled")
    
    try:
        data = await request.json()
        webhook_url = data.get("url")
        
        if not webhook_url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        import requests
        from app.utils.telegram import get_proxy_config
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
        # Set webhook with allowed updates (messages and callback queries)
        data = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }
        
        proxies = get_proxy_config()
        response = requests.post(url, json=data, proxies=proxies, timeout=10)
        response.raise_for_status()
        
        return {"success": True, "result": response.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Telegram webhook updates (for messages and callback queries)
    """
    if not settings.TELEGRAM_ENABLED:
        raise HTTPException(status_code=403, detail="Telegram disabled")
    
    try:
        data = await request.json()
        
        # Handle incoming messages
        if "message" in data:
            message = data["message"]
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            text = message.get("text", "")
            
            # Handle commands
            if text and text.startswith("/"):
                command = text.split()[0].lower()
                
                if command == "/start":
                    welcome_message = "🤖 <b>خوش آمدید به ربات MetaStream!</b>\n\n"
                    welcome_message += "این ربات برای تایید درخواست‌های ویدیو و کانال استفاده می‌شود.\n\n"
                    welcome_message += "📋 <b>دستورات:</b>\n"
                    welcome_message += "/start - نمایش این پیام\n"
                    welcome_message += "/help - راهنما\n"
                    welcome_message += "/status - وضعیت ربات\n\n"
                    welcome_message += "👥 فقط ادمین‌ها می‌توانند از این ربات استفاده کنند."
                    
                    await send_telegram_message(chat_id, welcome_message)
                
                elif command == "/help":
                    help_message = "📖 <b>راهنمای ربات MetaStream</b>\n\n"
                    help_message += "این ربات برای تایید درخواست‌های ویدیو و کانال استفاده می‌شود.\n\n"
                    help_message += "🔔 <b>نحوه کار:</b>\n"
                    help_message += "1. هنگام ایجاد approval (ویدیو یا کانال)، پیام به شما ارسال می‌شود\n"
                    help_message += "2. می‌توانید با دکمه‌های «تایید» یا «رد» اقدام کنید\n\n"
                    help_message += "📋 <b>دستورات:</b>\n"
                    help_message += "/start - شروع\n"
                    help_message += "/help - راهنما\n"
                    help_message += "/status - وضعیت ربات"
                    
                    await send_telegram_message(chat_id, help_message)
                
                elif command == "/status":
                    admin_ids = settings.TELEGRAM_ADMIN_IDS.split(",") if settings.TELEGRAM_ADMIN_IDS else []
                    is_admin = str(user_id) in [aid.strip() for aid in admin_ids]
                    
                    status_message = "📊 <b>وضعیت ربات</b>\n\n"
                    status_message += f"✅ ربات فعال است\n"
                    status_message += f"👤 شما: {'ادمین' if is_admin else 'کاربر عادی'}\n"
                    status_message += f"🔧 Proxy: {'فعال' if settings.TELEGRAM_PROXY_HTTP else 'غیرفعال'}\n"
                    if is_admin:
                        status_message += f"👥 Admin IDs: {settings.TELEGRAM_ADMIN_IDS}"
                    else:
                        status_message += "\n⚠️ شما دسترسی ادمین ندارید."
                    
                    await send_telegram_message(chat_id, status_message)
                
                else:
                    unknown_message = "❓ دستور نامعتبر است.\n\n"
                    unknown_message += "برای مشاهده دستورات از /help استفاده کنید."
                    await send_telegram_message(chat_id, unknown_message)
            
            # Handle regular messages (non-commands)
            elif text:
                response_message = "👋 سلام!\n\n"
                response_message += "برای شروع از دستور /start استفاده کنید."
                await send_telegram_message(chat_id, response_message)
        
        # Handle callback query (button clicks)
        elif "callback_query" in data:
            callback_query = data["callback_query"]
            callback_data = callback_query.get("data", "")
            user_id = callback_query.get("from", {}).get("id")
            message_id = callback_query.get("message", {}).get("message_id")
            chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
            
            # Check if user is admin
            admin_ids = settings.TELEGRAM_ADMIN_IDS.split(",") if settings.TELEGRAM_ADMIN_IDS else []
            if str(user_id) not in [aid.strip() for aid in admin_ids]:
                # Answer callback with error
                await answer_callback_query(callback_query.get("id"), "شما دسترسی ندارید", show_alert=True)
                return {"ok": True}
            
            # Parse callback data
            if callback_data.startswith("approve_"):
                approval_id = int(callback_data.split("_")[1])
                result = await handle_approve(approval_id, user_id, db)
                await answer_callback_query(callback_query.get("id"), result.get("message", "تایید شد"))
                
                # Update message
                if result.get("success"):
                    new_text = f"✅ <b>تایید شد</b>\n\n{result.get('details', '')}"
                    await edit_message_text(chat_id, message_id, new_text)
                
            elif callback_data.startswith("reject_"):
                approval_id = int(callback_data.split("_")[1])
                result = await handle_reject(approval_id, user_id, db)
                await answer_callback_query(callback_query.get("id"), result.get("message", "رد شد"))
                
                # Update message
                if result.get("success"):
                    new_text = f"❌ <b>رد شد</b>\n\n{result.get('details', '')}"
                    await edit_message_text(chat_id, message_id, new_text)
        
        return {"ok": True}
    except Exception as e:
        print(f"[TELEGRAM] Webhook error: {e}")
        return {"ok": False, "error": str(e)}


async def handle_approve(approval_id: int, telegram_user_id: int, db: Session) -> dict:
    """
    Handle approval action from Telegram
    """
    try:
        approval = db.query(Approval).filter(Approval.id == approval_id).first()
        if not approval or approval.status != "pending":
            return {"success": False, "message": "درخواست یافت نشد یا قبلاً پردازش شده"}
        
        # Find admin user by telegram ID (we'll use first admin user for now)
        # In future, we can add telegram_user_id to User model
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            return {"success": False, "message": "کاربر ادمین یافت نشد"}
        
        if approval.type == "video":
            video = db.query(Video).filter(Video.id == approval.entity_id).first()
            if not video:
                return {"success": False, "message": "ویدیو یافت نشد"}
            video.status = "ready"
            video.approved_at = datetime.utcnow()
            video.approved_by = admin_user.id
            details = f"ویدیو: {video.title} (ID: {video.id})"
        elif approval.type == "channel":
            channel = db.query(Channel).filter(Channel.id == approval.entity_id).first()
            if not channel:
                return {"success": False, "message": "کانال یافت نشد"}
            channel.status = "approved"
            details = f"کانال: {channel.name} (ID: {channel.id})"
        else:
            return {"success": False, "message": "نوع درخواست نامعتبر"}
        
        approval.status = "approved"
        approval.approved_at = datetime.utcnow()
        approval.approved_by = admin_user.id
        db.commit()
        
        return {"success": True, "message": "تایید شد", "details": details}
    except Exception as e:
        db.rollback()
        print(f"[TELEGRAM] Approve error: {e}")
        return {"success": False, "message": f"خطا: {str(e)}"}


async def handle_reject(approval_id: int, telegram_user_id: int, db: Session) -> dict:
    """
    Handle reject action from Telegram
    """
    try:
        approval = db.query(Approval).filter(Approval.id == approval_id).first()
        if not approval or approval.status != "pending":
            return {"success": False, "message": "درخواست یافت نشد یا قبلاً پردازش شده"}
        
        # Find admin user
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            return {"success": False, "message": "کاربر ادمین یافت نشد"}
        
        if approval.type == "video":
            video = db.query(Video).filter(Video.id == approval.entity_id).first()
            if video:
                video.status = "rejected"
                video.processed_at = datetime.utcnow()
                details = f"ویدیو: {video.title} (ID: {video.id})"
            else:
                details = f"ویدیو ID: {approval.entity_id}"
        elif approval.type == "channel":
            channel = db.query(Channel).filter(Channel.id == approval.entity_id).first()
            if channel:
                channel.status = "rejected"
                details = f"کانال: {channel.name} (ID: {channel.id})"
            else:
                details = f"کانال ID: {approval.entity_id}"
        else:
            return {"success": False, "message": "نوع درخواست نامعتبر"}
        
        approval.status = "rejected"
        db.commit()
        
        return {"success": True, "message": "رد شد", "details": details}
    except Exception as e:
        db.rollback()
        print(f"[TELEGRAM] Reject error: {e}")
        return {"success": False, "message": f"خطا: {str(e)}"}


async def answer_callback_query(callback_query_id: str, text: str, show_alert: bool = False):
    """
    Answer a callback query
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        return
    
    import requests
    from app.utils.telegram import get_proxy_config
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    data = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }
    
    try:
        proxies = get_proxy_config()
        requests.post(url, json=data, proxies=proxies, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM] Answer callback error: {e}")


async def edit_message_text(chat_id: int, message_id: int, text: str):
    """
    Edit a message text
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        return
    
    import requests
    from app.utils.telegram import get_proxy_config
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/editMessageText"
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        proxies = get_proxy_config()
        requests.post(url, json=data, proxies=proxies, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM] Edit message error: {e}")


async def send_telegram_message(chat_id: int, text: str, reply_markup: Optional[dict] = None):
    """
    Send a message to Telegram (async wrapper)
    """
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        return
    
    import requests
    from app.utils.telegram import get_proxy_config
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    try:
        proxies = get_proxy_config()
        requests.post(url, json=data, proxies=proxies, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM] Send message error: {e}")

