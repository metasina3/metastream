"""
Telegram bot utilities
"""
import requests
from app.core.config import settings
from typing import Optional

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
        # Setup proxy if configured
        proxies = None
        if settings.TELEGRAM_PROXY_HTTP:
            proxies = {"http": settings.TELEGRAM_PROXY_HTTP, "https": settings.TELEGRAM_PROXY_HTTP}
        elif settings.TELEGRAM_PROXY_SOCKS5:
            proxies = {"http": settings.TELEGRAM_PROXY_SOCKS5, "https": settings.TELEGRAM_PROXY_SOCKS5}
        
        response = requests.post(url, json=data, proxies=proxies, timeout=10)
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
        proxies = None
        if settings.TELEGRAM_PROXY_HTTP:
            proxies = {"http": settings.TELEGRAM_PROXY_HTTP, "https": settings.TELEGRAM_PROXY_HTTP}
        elif settings.TELEGRAM_PROXY_SOCKS5:
            proxies = {"http": settings.TELEGRAM_PROXY_SOCKS5, "https": settings.TELEGRAM_PROXY_SOCKS5}
        
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id}
            response = requests.post(url, files=files, data=data, proxies=proxies, timeout=60)
            response.raise_for_status()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

