#!/usr/bin/env python3
"""
Export all channels with their information and keys to a text file
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.models.channel import Channel
from app.models.user import User

def format_datetime(dt):
    """Format datetime to readable string"""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def main():
    db = SessionLocal()
    
    try:
        # Get all channels
        channels = db.query(Channel).order_by(Channel.id).all()
        
        if not channels:
            print("❌ No channels found in database")
            return 1
        
        # Get user information for each channel
        output_lines = []
        output_lines.append("=" * 80)
        output_lines.append("لیست کانال‌های MetaStream")
        output_lines.append("=" * 80)
        output_lines.append(f"تاریخ استخراج: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append(f"تعداد کل کانال‌ها: {len(channels)}")
        output_lines.append("=" * 80)
        output_lines.append("")
        
        for idx, channel in enumerate(channels, 1):
            # Get user information
            user = None
            if channel.user_id:
                user = db.query(User).filter(User.id == channel.user_id).first()
            
            approved_by_user = None
            if channel.approved_by:
                approved_by_user = db.query(User).filter(User.id == channel.approved_by).first()
            
            output_lines.append(f"کانال #{idx}")
            output_lines.append("-" * 80)
            output_lines.append(f"شناسه (ID): {channel.id}")
            output_lines.append(f"نام: {channel.name}")
            output_lines.append(f"Slug: {channel.slug}")
            output_lines.append(f"نام کاربری آپارات: {channel.aparat_username}")
            output_lines.append(f"لینک آپارات: https://www.aparat.com/{channel.aparat_username}")
            output_lines.append(f"وضعیت: {channel.status}")
            output_lines.append(f"تاریخ ایجاد: {format_datetime(channel.created_at)}")
            output_lines.append(f"تاریخ تایید: {format_datetime(channel.approved_at)}")
            
            # User information
            if user:
                output_lines.append(f"کاربر ایجادکننده:")
                output_lines.append(f"  - User ID: {user.id}")
                output_lines.append(f"  - نام: {user.name or 'N/A'}")
                output_lines.append(f"  - ایمیل: {user.email or 'N/A'}")
                output_lines.append(f"  - موبایل: {user.phone or 'N/A'}")
            else:
                output_lines.append(f"کاربر ایجادکننده: N/A (User ID: {channel.user_id or 'N/A'})")
            
            # Approved by
            if approved_by_user:
                output_lines.append(f"تایید شده توسط:")
                output_lines.append(f"  - User ID: {approved_by_user.id}")
                output_lines.append(f"  - نام: {approved_by_user.name or 'N/A'}")
            elif channel.approved_by:
                output_lines.append(f"تایید شده توسط: User ID {channel.approved_by} (کاربر یافت نشد)")
            
            # RTMP Information
            output_lines.append("")
            output_lines.append("اطلاعات RTMP:")
            output_lines.append(f"  - RTMP URL: {channel.rtmp_url or 'N/A'}")
            output_lines.append(f"  - RTMP Key: {channel.rtmp_key or 'N/A'}")
            
            if channel.rtmp_url and channel.rtmp_key:
                full_rtmp = f"{channel.rtmp_url}/{channel.rtmp_key}"
                output_lines.append(f"  - RTMP کامل: {full_rtmp}")
            
            output_lines.append("")
            output_lines.append("=" * 80)
            output_lines.append("")
        
        # Write to file
        output_file = project_root / "channels_export.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        
        print(f"✅ {len(channels)} کانال استخراج شد")
        print(f"📁 فایل ذخیره شده در: {output_file}")
        print(f"📊 حجم فایل: {os.path.getsize(output_file) / 1024:.2f} KB")
        
        return 0
        
    except Exception as e:
        print(f"❌ خطا در استخراج کانال‌ها: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())

