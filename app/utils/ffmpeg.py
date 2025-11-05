"""
FFmpeg utilities for video processing
"""
import multiprocessing
import subprocess
import os
from app.core.config import settings


def threads_for_encode() -> int:
    """
    Calculate threads for FFmpeg encoding
    """
    total = multiprocessing.cpu_count()
    
    if total >= 8:
        return 6  # 6 cores for FFmpeg
    else:
        reserve = max(0, settings.CPU_RESERVE)
        return max(1, total - reserve)


def get_video_duration(video_path: str) -> float:
    """
    Get video duration in seconds using FFprobe
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    
    return 0.0


def format_duration(seconds: float) -> str:
    """
    Format duration as HH:MM:SS
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

