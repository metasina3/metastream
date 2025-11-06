from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.utils.datetime_utils import now_tehran

class StreamSchedule(Base):
    __tablename__ = "streams"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    channel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)  # Don't delete streams if channel is deleted
    video_id: Mapped[Optional[int]] = mapped_column(ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)  # Don't delete streams if video is deleted
    title: Mapped[str] = mapped_column(String(255))
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration: Mapped[int] = mapped_column(Integer, default=0)  # Duration in seconds from video
    status: Mapped[str] = mapped_column(String(50), default="scheduled", index=True)  # scheduled, live, ended, cancelled
    allow_comments: Mapped[bool] = mapped_column(Boolean, default=True)
    viewers_count: Mapped[int] = mapped_column(Integer, default=0)
    max_viewers: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # For URL
    proxy_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Optional proxy for streaming (socks5://user:pass@host:port)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Error message if stream failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_tehran)

