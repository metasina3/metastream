from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class TelegramBot(Base):
    __tablename__ = "telegram_bots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_token: Mapped[str] = mapped_column(String(500))
    chat_id: Mapped[str] = mapped_column(String(100))
    proxy_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settings: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)  # JSON as string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
