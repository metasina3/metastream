#!/usr/bin/env python3
"""
Script to send database backup to Telegram
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.utils.telegram import send_file_to_telegram

def main():
    if len(sys.argv) < 2:
        print("Usage: python send_backup_to_telegram.py <backup_file_path>")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        sys.exit(1)
    
    if not settings.TELEGRAM_ENABLED or not settings.TELEGRAM_BOT_TOKEN:
        print("❌ Telegram is disabled")
        sys.exit(1)
    
    if not settings.TELEGRAM_ADMIN_IDS:
        print("❌ No admin IDs configured")
        sys.exit(1)
    
    admin_ids = settings.TELEGRAM_ADMIN_IDS.split(",") if settings.TELEGRAM_ADMIN_IDS else []
    
    print(f"📤 Sending backup to {len(admin_ids)} admin(s)...")
    print(f"📁 File: {backup_file}")
    print(f"📊 Size: {os.path.getsize(backup_file) / (1024*1024):.2f} MB")
    
    success_count = 0
    for chat_id in admin_ids:
        if chat_id.strip():
            print(f"\n📨 Sending to {chat_id.strip()}...")
            result = send_file_to_telegram(backup_file, chat_id.strip())
            if result.get("success"):
                print(f"✅ Sent successfully to {chat_id.strip()}")
                success_count += 1
            else:
                print(f"❌ Failed to send to {chat_id.strip()}: {result.get('error', 'Unknown error')}")
    
    if success_count > 0:
        print(f"\n✅ Backup sent to {success_count} admin(s) successfully!")
        return 0
    else:
        print("\n❌ Failed to send backup to any admin")
        return 1

if __name__ == "__main__":
    sys.exit(main())

