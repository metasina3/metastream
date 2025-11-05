"""
SMS utilities for sending messages
"""
import requests
from app.core.config import settings


async def send_sms(phone: str, message: str) -> dict:
    """
    Send SMS via configured provider
    
    Returns: {'success': bool, 'message_id': str, 'cost': float}
    """
    if settings.SMS_GATEWAY_DEFAULT == "kavenegar":
        return await send_kavenegar_sms(phone, message)
    
    # Add other providers here
    return {"success": False, "error": "Unknown provider"}


async def send_kavenegar_sms(phone: str, message: str) -> dict:
    """
    Send SMS via Kavenegar API
    """
    api_key = settings.SMS_API_KEY
    if not api_key:
        return {"success": False, "error": "SMS API key not configured"}
    
    url = f"{settings.SMS_API_URL}/{api_key}/sms/send.json"
    
    try:
        response = requests.post(url, json={
            "receptor": phone,
            "message": message
        })
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "message_id": str(data.get("entries", [{}])[0].get("messageid", "")),
            "cost": 0.1  # Approximate cost
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

