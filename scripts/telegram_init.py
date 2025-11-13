#!/usr/bin/env python3
"""
Script to initialize Telegram bot: set webhook and send test message
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
from app.core.config import settings

def main():
    print("🤖 Initializing Telegram Bot...")
    print(f"📋 Bot Token: {settings.TELEGRAM_BOT_TOKEN[:10]}..." if settings.TELEGRAM_BOT_TOKEN else "❌ No bot token")
    print(f"👥 Admin IDs: {settings.TELEGRAM_ADMIN_IDS}")
    print(f"🔧 Proxy: {settings.TELEGRAM_PROXY_HTTP}")
    print()
    
    if not settings.TELEGRAM_ENABLED:
        print("❌ Telegram is disabled in settings")
        return 1
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is not set")
        return 1
    
    if not settings.TELEGRAM_ADMIN_IDS:
        print("❌ TELEGRAM_ADMIN_IDS is not set")
        return 1
    
    # 1. Set webhook
    print("1️⃣ Setting webhook...")
    try:
        webhook_url = f"{settings.API_URL}/api/telegram/webhook"
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
        data = {"url": webhook_url}
        
        proxies = None
        if settings.TELEGRAM_PROXY_HTTP:
            proxies = {"http": settings.TELEGRAM_PROXY_HTTP, "https": settings.TELEGRAM_PROXY_HTTP}
        
        response = requests.post(url, json=data, proxies=proxies, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            print(f"✅ Webhook set successfully: {webhook_url}")
        else:
            print(f"❌ Failed to set webhook: {result}")
            return 1
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return 1
    
    print()
    
    # 2. Send test message
    print("2️⃣ Sending test message...")
    try:
        message = "🚀 <b>ربات تلگرام راه‌اندازی شد!</b>\n\n"
        message += "✅ Webhook تنظیم شد\n"
        message += "✅ ربات آماده دریافت درخواست‌های تایید است\n\n"
        message += f"🔗 Webhook URL: {webhook_url}\n"
        message += f"👥 Admin IDs: {settings.TELEGRAM_ADMIN_IDS}"
        
        admin_ids = settings.TELEGRAM_ADMIN_IDS.split(",") if settings.TELEGRAM_ADMIN_IDS else []
        success_count = 0
        
        for chat_id in admin_ids:
            if chat_id.strip():
                send_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                send_data = {
                    "chat_id": chat_id.strip(),
                    "text": message,
                    "parse_mode": "HTML"
                }
                
                try:
                    send_response = requests.post(send_url, json=send_data, proxies=proxies, timeout=10)
                    send_response.raise_for_status()
                    print(f"✅ Test message sent to {chat_id.strip()}")
                    success_count += 1
                except Exception as e:
                    print(f"❌ Failed to send message to {chat_id.strip()}: {e}")
        
        if success_count > 0:
            print(f"\n✅ {success_count} test message(s) sent successfully")
        else:
            print("\n❌ No messages were sent")
            return 1
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return 1
    
    print()
    print("🎉 Telegram bot initialized successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

