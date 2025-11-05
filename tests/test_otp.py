"""
Tests for OTP utilities
"""
import pytest
from datetime import datetime, timedelta
from app.utils.otp import generate_otp, get_otp_expiry, is_otp_expired


def test_generate_otp():
    """Test OTP generation"""
    otp = generate_otp()
    assert len(otp) == 4
    assert otp.isdigit()


def test_get_otp_expiry():
    """Test OTP expiry calculation"""
    expiry = get_otp_expiry()
    assert expiry > datetime.utcnow()
    # Should be about 5 minutes (300 seconds) in future
    diff = (expiry - datetime.utcnow()).total_seconds()
    assert 290 < diff < 310


def test_is_otp_expired():
    """Test OTP expiry check"""
    past = datetime.utcnow() - timedelta(seconds=10)
    future = datetime.utcnow() + timedelta(seconds=10)
    
    assert is_otp_expired(past) == True
    assert is_otp_expired(future) == False

