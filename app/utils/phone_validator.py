"""
Phone number validation utilities
"""
import re
from app.core.config import settings


def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Validate Iranian phone number
    
    Returns: (is_valid, formatted_number)
    Formats: 09xxxxxxxxx or +989xxxxxxxxx
    """
    # Clean phone number
    phone = phone.strip()
    
    # Check length
    if len(phone) != 11 and len(phone) != 13:
        return False, ""
    
    # Check pattern
    pattern = settings.PHONE_REGEX
    if not re.match(pattern, phone):
        return False, ""
    
    # Format: Normalize to 09xxxxxxxxx
    if phone.startswith("+989"):
        formatted = "0" + phone[3:]
    elif phone.startswith("09"):
        formatted = phone
    else:
        return False, ""
    
    return True, formatted


def is_valid_phone(phone: str) -> bool:
    """Quick validation check"""
    is_valid, _ = validate_phone(phone)
    return is_valid

