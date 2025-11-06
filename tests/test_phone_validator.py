"""
Tests for phone validation utility
"""
import pytest
from app.utils.phone_validator import validate_phone, is_valid_phone


def test_valid_phone_09_format():
    """Test valid phone starting with 09"""
    is_valid, formatted = validate_phone("09377833157")
    assert is_valid == True
    assert formatted == "09377833157"


def test_valid_phone_plus989_format():
    """Test valid phone starting with +989"""
    is_valid, formatted = validate_phone("+989377833157")
    assert is_valid == True
    assert formatted == "09377833157"


def test_invalid_phone_short():
    """Test invalid short phone"""
    is_valid, formatted = validate_phone("0912345")
    assert is_valid == False


def test_invalid_phone_wrong_start():
    """Test invalid phone with wrong start"""
    is_valid, formatted = validate_phone("1234567890")
    assert is_valid == False


def test_is_valid_phone_helper():
    """Test is_valid_phone helper"""
    assert is_valid_phone("09377833157") == True
    assert is_valid_phone("123") == False

