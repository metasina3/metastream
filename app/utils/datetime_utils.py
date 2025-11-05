"""
DateTime utilities for handling timezone conversions
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import settings

# Tehran timezone
TEHRAN_TZ = ZoneInfo(settings.TIMEZONE)


def now_tehran() -> datetime:
    """
    Get current datetime in Tehran timezone
    """
    return datetime.now(TEHRAN_TZ)


def to_tehran(dt: datetime) -> datetime:
    """
    Convert any datetime to Tehran timezone
    """
    if dt is None:
        return None
    
    # If datetime is naive (no timezone), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    
    # Convert to Tehran timezone
    return dt.astimezone(TEHRAN_TZ)


def format_datetime_persian(dt: datetime) -> str:
    """
    Format datetime for Persian display
    """
    if dt is None:
        return ""
    
    # Convert to Tehran time
    dt_tehran = to_tehran(dt)
    
    # Format: YYYY-MM-DD HH:MM:SS
    return dt_tehran.strftime("%Y-%m-%d %H:%M:%S")

