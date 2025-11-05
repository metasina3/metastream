"""
Tests for configuration
"""
import pytest
import os
from app.core.config import settings


def test_settings_loaded():
    """Test that settings are loaded"""
    assert settings.APP_NAME is not None


def test_database_config():
    """Test database configuration exists"""
    # Should be able to access DB config
    assert hasattr(settings, 'DATABASE_URL')
    assert hasattr(settings, 'POSTGRES_HOST')
    assert hasattr(settings, 'POSTGRES_PORT')


def test_redis_config():
    """Test Redis configuration exists"""
    assert hasattr(settings, 'REDIS_URL')


def test_domain_config():
    """Test domain configuration exists"""
    assert hasattr(settings, 'MAIN_DOMAIN')
    assert hasattr(settings, 'PANEL_DOMAIN')
    assert hasattr(settings, 'API_DOMAIN')
    assert hasattr(settings, 'LIVE_DOMAIN')


