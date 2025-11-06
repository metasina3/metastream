"""
Authentication endpoints
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Form, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models import User, OtpRequest
from app.utils.phone_validator import validate_phone
from app.utils.otp import generate_otp, get_otp_expiry
from app.utils.sms import send_sms
from datetime import datetime
from app.core.security import verify_password, hash_password
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register/request-otp")
async def request_otp(request: Request, phone: str):
    """
    Request OTP for registration
    """
    if not settings.FEATURE_OTP_ENABLED:
        raise HTTPException(status_code=403, detail="OTP is disabled")
    # Validate phone
    is_valid, formatted_phone = validate_phone(phone)
    if not is_valid:
        raise HTTPException(status_code=400, detail="شماره موبایل معتبر نیست")
    
    # Check if user exists
    db: Session = next(get_db())
    user = db.query(User).filter(User.phone == formatted_phone).first()
    
    if user:
        raise HTTPException(status_code=400, detail="کاربر با این شماره وجود دارد")
    
    # Generate OTP
    otp_code = generate_otp()
    expiry = get_otp_expiry()
    
    # Store OTP
    otp = OtpRequest(
        phone=formatted_phone,
        otp_code=otp_code,
        expires_at=expiry
    )
    db.add(otp)
    db.commit()
    
    # Send SMS if enabled
    if settings.FEATURE_OTP_ENABLED and settings.SMS_API_KEY:
        await send_sms(formatted_phone, f"کد تایید شما: {otp_code}")
    
    return {"success": True, "expires_in": settings.OTP_EXPIRY}


@router.post("/register/verify-otp")
async def verify_otp(request: Request, phone: str, otp: str):
    """
    Verify OTP and create user
    """
    if not settings.FEATURE_OTP_ENABLED:
        raise HTTPException(status_code=403, detail="OTP is disabled")
    # Validate phone
    is_valid, formatted_phone = validate_phone(phone)
    if not is_valid:
        raise HTTPException(status_code=400, detail="شماره موبایل معتبر نیست")
    
    db: Session = next(get_db())
    
    # Get latest OTP
    otp_request = db.query(OtpRequest).filter(
        OtpRequest.phone == formatted_phone,
        OtpRequest.verified == False
    ).order_by(OtpRequest.created_at.desc()).first()
    
    if not otp_request:
        raise HTTPException(status_code=400, detail="کد تایید پیدا نشد")
    
    # Check expiry
    if datetime.utcnow() > otp_request.expires_at:
        raise HTTPException(status_code=400, detail="کد منقضی شده است")
    
    # Check attempts
    if otp_request.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="تعداد تلاش‌ها بیشتر از حد مجاز")
    
    # Verify OTP
    if otp_request.otp_code != otp:
        otp_request.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="کد اشتباه است")
    
    # Create user
    user = User(
        phone=formatted_phone,
        name="کاربر",
        phone_verified=True,
        role="user"
    )
    db.add(user)
    
    # Mark OTP as verified
    otp_request.verified = True
    otp_request.verified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    # Set session
    request.session["user_id"] = user.id
    request.session["phone"] = formatted_phone
    
    return {"success": True, "user_id": user.id, "phone": formatted_phone}


@router.get("/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Get current logged-in user
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.name,
        "role": user.role,
        "is_active": user.is_active,
        "impersonating": bool(request.session.get("original_user_id"))
    }


@router.post("/logout")
async def logout(request: Request):
    """
    Logout current user
    """
    request.session.clear()
    return {"success": True}


@router.post("/login")
async def email_phone_password_login(request: Request, identity: Optional[str] = None, password: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Email/phone and password login for panel access. Accepts form, JSON, or query params.
    """
    # Try getting form-data first
    if not (identity and password):
        try:
            # form-data
            form = await request.form()
            identity = identity or form.get('identity')
            password = password or form.get('password')
        except Exception:
            pass
    # Try getting JSON body
    if not (identity and password):
        try:
            data = await request.json()
            identity = identity or data.get('identity')
            password = password or data.get('password')
        except Exception:
            pass
    # Try query params if still missing
    if not (identity and password):
        qp = request.query_params
        identity = identity or qp.get('identity')
        password = password or qp.get('password')
    if not identity or not password:
        raise HTTPException(status_code=400, detail="ایمیل/شماره و رمز عبور الزامی است")
    q = db.query(User)
    user = q.filter((User.email == identity) | (User.phone == identity)).first()
    from app.core.security import verify_password
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="ایمیل/شماره یا رمز اشتباه است")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="حساب کاربری غیرفعال است")
    # Expiry: admins always unlimited
    if user.role != "admin" and user.expires_at and user.expires_at < datetime.utcnow():
        raise HTTPException(status_code=402, detail="اشتراک شما به پایان رسیده. لطفاً با پشتیبانی تماس بگیرید.")
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    user.last_login = datetime.utcnow()
    db.commit()
    return {"success": True, "user": {"id": user.id, "name": user.name, "role": user.role, "expires_at": user.expires_at, "is_active": user.is_active}}

