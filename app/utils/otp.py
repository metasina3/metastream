"""
OTP generation and verification utilities
"""
import random
import string
from datetime import datetime, timedelta
from app.core.config import settings


def generate_otp() -> str:
    """
    Generate random OTP code
    
    Returns: 4-digit code (string)
    """
    length = settings.OTP_LENGTH
    return ''.join(random.choices(string.digits, k=length))


def get_otp_expiry() -> datetime:
    """Get expiry datetime for OTP"""
    expiry_seconds = settings.OTP_EXPIRY
    return datetime.utcnow() + timedelta(seconds=expiry_seconds)


def is_otp_expired(expires_at: datetime) -> bool:
    """Check if OTP is expired"""
    return datetime.utcnow() > expires_at

