"""
Tests for FFmpeg utilities
"""
import pytest
from app.utils.ffmpeg import format_duration, threads_for_encode


def test_format_duration_hours():
    """Test formatting duration with hours"""
    assert format_duration(3661) == "01:01:01"  # 1 hour, 1 minute, 1 second


def test_format_duration_minutes():
    """Test formatting duration with minutes only"""
    assert format_duration(125) == "00:02:05"  # 2 minutes, 5 seconds


def test_format_duration_seconds():
    """Test formatting duration with seconds only"""
    assert format_duration(45) == "00:00:45"


def test_threads_for_encode():
    """Test thread calculation"""
    threads = threads_for_encode()
    assert threads > 0
    assert isinstance(threads, int)


