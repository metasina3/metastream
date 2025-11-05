from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class SmsGateway(Base):
    __tablename__ = "sms_gateways"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(50))
    api_key: Mapped[str] = mapped_column(String(500))
    api_url: Mapped[str] = mapped_column(String(500))
    balance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SmsLog(Base):
    __tablename__ = "sms_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(500))
    gateway_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sms_gateways.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    response: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OtpRequest(Base):
    __tablename__ = "otp_requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    otp_code: Mapped[str] = mapped_column(String(10))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

