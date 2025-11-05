"""
Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models import User
from sqlalchemy.exc import IntegrityError
from app.routers import auth, admin, dashboard, api, player, moderation, approvals, analytics
try:
    from app.routers import websocket
except ImportError:
    websocket = None
from app.middleware.host_routing import HostRoutingMiddleware

app = FastAPI(title=settings.APP_NAME)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") + [settings.PANEL_URL, settings.LIVE_URL, "http://localhost:5173"],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware
app.add_middleware(HostRoutingMiddleware)  # Host-based routing
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SessionMiddleware, 
                   secret_key=settings.SECRET_KEY, 
                   max_age=settings.COOKIE_EXPIRY)

# Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(api.router)
app.include_router(player.router)
app.include_router(moderation.router)
app.include_router(approvals.router)
app.include_router(analytics.router)
if websocket:
    app.include_router(websocket.router)

# Static files
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except:
    pass

try:
    # Media directory is mounted at /app/media (separate from read-only code at /app/app)
    import os
    media_dir = "/app/media"
    uploads_dir = "/app/uploads"
    if os.path.exists(media_dir):
        app.mount("/media", StaticFiles(directory=media_dir), name="media")
    if os.path.exists(uploads_dir):
        app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
except:
    pass

# Startup event
@app.on_event("startup")
async def startup():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)
    
    # Run migrations
    try:
        db = SessionLocal()
        from sqlalchemy import text
        
        # 1. Migrate channels table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='channels' AND column_name='rtmp_url'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE channels ADD COLUMN rtmp_url VARCHAR(500)"))
            db.commit()
            print("[MIGRATION] Added rtmp_url to channels")
            
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='channels' AND column_name='rtmp_key'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE channels ADD COLUMN rtmp_key VARCHAR(500)"))
            db.commit()
            print("[MIGRATION] Added rtmp_key to channels")
            
        try:
            db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS unique_aparat_username_idx ON channels (aparat_username)"))
            db.commit()
        except Exception:
            pass
        
        # 2. Migrate streams table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='streams' AND column_name='caption'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE streams ADD COLUMN caption TEXT"))
            db.commit()
            print("[MIGRATION] Added caption to streams")
            
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='streams' AND column_name='slug'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE streams ADD COLUMN slug VARCHAR(255)"))
            db.commit()
            print("[MIGRATION] Added slug to streams")
            
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='streams' AND column_name='duration'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE streams ADD COLUMN duration INTEGER DEFAULT 0"))
            db.commit()
            print("[MIGRATION] Added duration to streams")
        
        # Add error_message column if it doesn't exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='streams' AND column_name='error_message'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE streams ADD COLUMN error_message TEXT"))
            db.commit()
            print("[MIGRATION] Added error_message to streams")
        
        # Make channel_id and video_id nullable to protect streams from deletion
        try:
            result = db.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='channel_id'
            """))
            row = result.fetchone()
            if row and row[0] == 'NO':
                db.execute(text("ALTER TABLE streams ALTER COLUMN channel_id DROP NOT NULL"))
                db.commit()
                print("[MIGRATION] Made channel_id nullable in streams")
        except Exception as e:
            print(f"[MIGRATION] Note: channel_id nullable migration: {e}")
        
        try:
            result = db.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='video_id'
            """))
            row = result.fetchone()
            if row and row[0] == 'NO':
                db.execute(text("ALTER TABLE streams ALTER COLUMN video_id DROP NOT NULL"))
                db.commit()
                print("[MIGRATION] Made video_id nullable in streams")
        except Exception as e:
            print(f"[MIGRATION] Note: video_id nullable migration: {e}")
        
        # Make requires_otp nullable (we removed it from model)
        try:
            db.execute(text("""
                ALTER TABLE streams 
                ALTER COLUMN requires_otp DROP NOT NULL,
                ALTER COLUMN requires_otp SET DEFAULT FALSE
            """))
            db.commit()
            print("[MIGRATION] Made requires_otp nullable in streams")
        except Exception as e:
            # Column might not exist or already nullable
            print(f"[MIGRATION] Note: requires_otp migration skipped: {e}")
        
        # Make otp_verification_required nullable
        try:
            db.execute(text("""
                ALTER TABLE streams 
                ALTER COLUMN otp_verification_required DROP NOT NULL,
                ALTER COLUMN otp_verification_required SET DEFAULT FALSE
            """))
            db.commit()
            print("[MIGRATION] Made otp_verification_required nullable in streams")
        except Exception as e:
            print(f"[MIGRATION] Note: otp_verification_required migration skipped: {e}")
        
        # Drop end_time if exists (we use duration now)
        try:
            db.execute(text("ALTER TABLE streams DROP COLUMN IF EXISTS end_time"))
            db.commit()
            print("[MIGRATION] Dropped end_time from streams")
        except Exception as e:
            print(f"[MIGRATION] Note: end_time drop skipped: {e}")
        
        # Make share_link nullable or drop it (we use slug now)
        try:
            db.execute(text("""
                ALTER TABLE streams 
                ALTER COLUMN share_link DROP NOT NULL
            """))
            db.commit()
            print("[MIGRATION] Made share_link nullable in streams")
        except Exception as e:
            print(f"[MIGRATION] Note: share_link migration skipped: {e}")
        
        # 3. Migrate comments table  
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='comments' AND column_name='last_name'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE comments ADD COLUMN last_name VARCHAR(100)"))
            db.commit()
            print("[MIGRATION] Added last_name to comments")
            
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='comments' AND column_name='text'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE comments ADD COLUMN text TEXT"))
            db.commit()
            print("[MIGRATION] Added text to comments")
            
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='comments' AND column_name='is_approved'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE comments ADD COLUMN is_approved BOOLEAN DEFAULT FALSE"))
            db.commit()
            print("[MIGRATION] Added is_approved to comments")
            
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='comments' AND column_name='is_deleted'
        """))
        if not result.fetchone():
            db.execute(text("ALTER TABLE comments ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))
            db.commit()
            print("[MIGRATION] Added is_deleted to comments")
        
        db.close()
        print("[MIGRATION] All migrations completed successfully")
    except Exception as e:
        print(f"[STARTUP] Migration error: {e}")
    # Ensure admin user exists based on env
    try:
        db = SessionLocal()
        from app.core.config import settings as _settings
        admin_email = _settings.ADMIN_EMAIL
        admin_password = _settings.ADMIN_PASSWORD
        admin_phone = _settings.ADMIN_PHONE
        if admin_email and admin_password:
            user = db.query(User).filter((User.email == admin_email) | (User.phone == (admin_phone or ""))).first()
            if user:
                user.email = admin_email
                user.role = "admin"
                user.is_active = True
                user.phone_verified = True
                user.name = user.name or "Administrator"
                user.password_hash = hash_password(admin_password)
                db.commit()
            else:
                try:
                    admin_user = User(
                        email=admin_email,
                        phone=admin_phone or "00000000000",
                        name="Administrator",
                        role="admin",
                        phone_verified=True,
                        is_active=True,
                        password_hash=hash_password(admin_password),
                    )
                    db.add(admin_user)
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    # If phone exists from a previous user, update that record to admin
                    if admin_phone:
                        u2 = db.query(User).filter(User.phone == admin_phone).first()
                        if u2:
                            u2.email = admin_email
                            u2.role = "admin"
                            u2.is_active = True
                            u2.phone_verified = True
                            u2.name = u2.name or "Administrator"
                            u2.password_hash = hash_password(admin_password)
                            db.commit()
    except Exception:
        pass
    finally:
        try:
            db.close()
        except Exception:
            pass

# Health check
@app.get("/")
async def root():
    return {"message": "Metastream API", "version": "2.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

