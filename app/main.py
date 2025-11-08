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
except (OSError, ValueError) as e:
    print(f"[STARTUP] Warning: Could not mount static files: {e}")

try:
    # Media directory is mounted at /app/media (separate from read-only code at /app/app)
    import os
    media_dir = "/app/media"
    uploads_dir = "/app/uploads"
    if os.path.exists(media_dir):
        app.mount("/media", StaticFiles(directory=media_dir), name="media")
    if os.path.exists(uploads_dir):
        app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
except (OSError, ValueError) as e:
    print(f"[STARTUP] Warning: Could not mount media/uploads directories: {e}")

# Startup event
@app.on_event("startup")
async def startup():
    """Create database tables"""
    # Use PostgreSQL advisory lock to prevent race conditions
    # Only one worker will create tables, others will wait
    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        
        # Try to acquire advisory lock (lock ID: 12345)
        # This ensures only one worker creates tables
        result = db.execute(text("SELECT pg_try_advisory_lock(12345)"))
        lock_acquired = result.scalar()
        
        if lock_acquired:
            try:
                # This worker acquired the lock, create tables
                print("[STARTUP] Acquired lock, creating database tables...")
                Base.metadata.create_all(bind=engine)
                print("[STARTUP] Database tables created/verified")
            except Exception as e:
                # Log errors but don't fail
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in [
                    "pg_type_typname_nsp_index",
                    "pg_class_relname_nsp_index", 
                    "duplicate key",
                    "already exists",
                    "relation"
                ]):
                    print("[STARTUP] Tables already exist")
                else:
                    print(f"[STARTUP] Warning: Database creation error: {e}")
            finally:
                # Release the lock
                db.execute(text("SELECT pg_advisory_unlock(12345)"))
                db.commit()
        else:
            # Another worker has the lock, wait for it to finish
            print("[STARTUP] Another worker is creating tables, waiting...")
            import time
            
            # Wait up to 10 seconds for tables to be created
            max_wait = 10
            wait_interval = 0.5
            waited = 0
            tables_exist = False
            
            while waited < max_wait:
                time.sleep(wait_interval)
                waited += wait_interval
                
                # Check if tables exist
                try:
                    result = db.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'users'
                        )
                    """))
                    tables_exist = result.scalar()
                    if tables_exist:
                        break
                except Exception:
                    pass  # Ignore errors during table check
            
            if tables_exist:
                print("[STARTUP] Tables already exist (created by another worker)")
            else:
                # Tables don't exist yet after waiting, try to create them (with error handling)
                print("[STARTUP] Tables not found after waiting, trying to create...")
                try:
                    Base.metadata.create_all(bind=engine)
                    print("[STARTUP] Database tables created")
                except Exception as e:
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in [
                        "pg_type_typname_nsp_index",
                        "pg_class_relname_nsp_index", 
                        "duplicate key",
                        "already exists",
                        "relation"
                    ]):
                        print("[STARTUP] Tables already exist (race condition handled)")
                    else:
                        print(f"[STARTUP] Warning: Database creation error: {e}")
    except Exception as e:
        # Fallback: try to create tables without lock (for compatibility)
        print(f"[STARTUP] Lock mechanism failed, trying direct creation: {e}")
        try:
            Base.metadata.create_all(bind=engine)
            print("[STARTUP] Database tables created/verified (fallback)")
        except Exception as e2:
            error_str = str(e2).lower()
            if any(keyword in error_str for keyword in [
                "pg_type_typname_nsp_index",
                "pg_class_relname_nsp_index", 
                "duplicate key",
                "already exists",
                "relation"
            ]):
                print("[STARTUP] Tables already exist (fallback)")
            else:
                print(f"[STARTUP] Warning: Database creation error: {e2}")
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass  # Ignore close errors
    
    # Run migrations
    # Each migration in separate transaction to avoid abort issues
    # Use a new connection for migrations
    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        
        # 1. Migrate channels table
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='channels' AND column_name='rtmp_url'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE channels ADD COLUMN rtmp_url VARCHAR(500)"))
                db.commit()
                print("[MIGRATION] Added rtmp_url to channels")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: rtmp_url already exists")
            else:
                print(f"[MIGRATION] Note: rtmp_url migration skipped: {e}")
            
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='channels' AND column_name='rtmp_key'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE channels ADD COLUMN rtmp_key VARCHAR(500)"))
                db.commit()
                print("[MIGRATION] Added rtmp_key to channels")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: rtmp_key already exists")
            else:
                print(f"[MIGRATION] Note: rtmp_key migration skipped: {e}")
            
        try:
            # Check if index exists first
            result = db.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename='channels' AND indexname='unique_aparat_username_idx'
            """))
            if not result.fetchone():
                db.execute(text("CREATE UNIQUE INDEX unique_aparat_username_idx ON channels (aparat_username)"))
                db.commit()
                print("[MIGRATION] Created unique_aparat_username_idx")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate key" in error_str:
                print("[MIGRATION] Note: unique_aparat_username_idx already exists")
            else:
                print(f"[MIGRATION] Note: unique_aparat_username_idx skipped: {e}")
        
        # 2. Migrate streams table
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='caption'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE streams ADD COLUMN caption TEXT"))
                db.commit()
                print("[MIGRATION] Added caption to streams")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: caption already exists")
            else:
                print(f"[MIGRATION] Note: caption migration skipped: {e}")
            
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='slug'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE streams ADD COLUMN slug VARCHAR(255)"))
                db.commit()
                print("[MIGRATION] Added slug to streams")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: slug already exists")
            else:
                print(f"[MIGRATION] Note: slug migration skipped: {e}")
            
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='duration'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE streams ADD COLUMN duration INTEGER DEFAULT 0"))
                db.commit()
                print("[MIGRATION] Added duration to streams")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: duration already exists")
            else:
                print(f"[MIGRATION] Note: duration migration skipped: {e}")
        
        # Add error_message column if it doesn't exist
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='error_message'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE streams ADD COLUMN error_message TEXT"))
                db.commit()
                print("[MIGRATION] Added error_message to streams")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: error_message already exists")
            else:
                print(f"[MIGRATION] Note: error_message migration skipped: {e}")
        
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
            db.rollback()
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
            db.rollback()
            print(f"[MIGRATION] Note: video_id nullable migration: {e}")
        
        # Make requires_otp nullable (we removed it from model)
        # Check if column exists first
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='requires_otp'
            """))
            if result.fetchone():
                db.execute(text("""
                    ALTER TABLE streams 
                    ALTER COLUMN requires_otp DROP NOT NULL,
                    ALTER COLUMN requires_otp SET DEFAULT FALSE
                """))
                db.commit()
                print("[MIGRATION] Made requires_otp nullable in streams")
        except Exception as e:
            db.rollback()
            # Column might not exist or already nullable
            print(f"[MIGRATION] Note: requires_otp migration skipped: {e}")
        
        # Make otp_verification_required nullable
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='otp_verification_required'
            """))
            if result.fetchone():
                db.execute(text("""
                    ALTER TABLE streams 
                    ALTER COLUMN otp_verification_required DROP NOT NULL,
                    ALTER COLUMN otp_verification_required SET DEFAULT FALSE
                """))
                db.commit()
                print("[MIGRATION] Made otp_verification_required nullable in streams")
        except Exception as e:
            db.rollback()
            print(f"[MIGRATION] Note: otp_verification_required migration skipped: {e}")
        
        # Drop end_time if exists (we use duration now)
        try:
            db.execute(text("ALTER TABLE streams DROP COLUMN IF EXISTS end_time"))
            db.commit()
            print("[MIGRATION] Dropped end_time from streams")
        except Exception as e:
            db.rollback()
            print(f"[MIGRATION] Note: end_time drop skipped: {e}")
        
        # Make share_link nullable or drop it (we use slug now)
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='streams' AND column_name='share_link'
            """))
            if result.fetchone():
                db.execute(text("""
                    ALTER TABLE streams 
                    ALTER COLUMN share_link DROP NOT NULL
                """))
                db.commit()
                print("[MIGRATION] Made share_link nullable in streams")
        except Exception as e:
            db.rollback()
            print(f"[MIGRATION] Note: share_link migration skipped: {e}")
        
        # 3. Migrate comments table  
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='comments' AND column_name='last_name'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE comments ADD COLUMN last_name VARCHAR(100)"))
                db.commit()
                print("[MIGRATION] Added last_name to comments")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: last_name already exists")
            else:
                print(f"[MIGRATION] Note: last_name migration skipped: {e}")
            
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='comments' AND column_name='text'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE comments ADD COLUMN text TEXT"))
                db.commit()
                print("[MIGRATION] Added text to comments")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: text already exists")
            else:
                print(f"[MIGRATION] Note: text migration skipped: {e}")
            
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='comments' AND column_name='is_approved'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE comments ADD COLUMN is_approved BOOLEAN DEFAULT FALSE"))
                db.commit()
                print("[MIGRATION] Added is_approved to comments")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: is_approved already exists")
            else:
                print(f"[MIGRATION] Note: is_approved migration skipped: {e}")
            
        try:
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='comments' AND column_name='is_deleted'
            """))
            if not result.fetchone():
                db.execute(text("ALTER TABLE comments ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))
                db.commit()
                print("[MIGRATION] Added is_deleted to comments")
        except Exception as e:
            db.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                print("[MIGRATION] Note: is_deleted already exists")
            else:
                print(f"[MIGRATION] Note: is_deleted migration skipped: {e}")
        
        print("[MIGRATION] All migrations completed successfully")
    except Exception as e:
        print(f"[STARTUP] Migration error: {e}")
        try:
            if db:
                db.rollback()
        except Exception:
            pass  # Ignore rollback errors
    finally:
        try:
            if db:
                db.close()
        except Exception:
            pass  # Ignore close errors
    # Ensure admin user exists based on env
    # Use advisory lock to prevent race condition when multiple workers start
    db = None
    try:
        db = SessionLocal()
        from sqlalchemy import text
        from app.core.config import settings as _settings
        
        admin_email = _settings.ADMIN_EMAIL
        admin_password = _settings.ADMIN_PASSWORD
        admin_phone = _settings.ADMIN_PHONE
        
        if admin_email and admin_password:
            # Try to acquire advisory lock (lock ID: 12346 for admin user)
            result = db.execute(text("SELECT pg_try_advisory_lock(12346)"))
            lock_acquired = result.scalar()
            
            if lock_acquired:
                try:
                    # This worker acquired the lock, create/update admin user
                    print("[STARTUP] Acquired lock for admin user creation...")
                    
                    # First, check if user exists by email or phone
                    user = db.query(User).filter(
                        (User.email == admin_email) | 
                        (User.phone == (admin_phone or ""))
                    ).first()
                    
                    if user:
                        # User exists, update it
                        # Always update password_hash to ensure it matches .env
                        user.email = admin_email
                        user.role = "admin"
                        user.is_active = True
                        user.phone_verified = True
                        user.name = user.name or "Administrator"
                        user.password_hash = hash_password(admin_password)
                        if admin_phone:
                            user.phone = admin_phone
                        db.commit()
                        print(f"[STARTUP] Updated existing user to admin: {admin_email} (password updated)")
                    else:
                        # User doesn't exist, create it
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
                            print(f"[STARTUP] Created admin user: {admin_email}")
                        except IntegrityError as e:
                            db.rollback()
                            # If email/phone exists, try to find and update
                            error_str = str(e).lower()
                            if "duplicate key" in error_str or "already exists" in error_str:
                                # Try to find by email first
                                u2 = db.query(User).filter(User.email == admin_email).first()
                                if not u2 and admin_phone:
                                    u2 = db.query(User).filter(User.phone == admin_phone).first()
                                
                                if u2:
                                    # Always update password_hash to ensure it matches .env
                                    u2.email = admin_email
                                    u2.role = "admin"
                                    u2.is_active = True
                                    u2.phone_verified = True
                                    u2.name = u2.name or "Administrator"
                                    u2.password_hash = hash_password(admin_password)
                                    if admin_phone:
                                        u2.phone = admin_phone
                                    db.commit()
                                    print(f"[STARTUP] Updated existing user to admin: {admin_email} (password updated)")
                                else:
                                    print(f"[STARTUP] Warning: Could not find user to update: {e}")
                            else:
                                print(f"[STARTUP] Warning: Admin user creation error: {e}")
                finally:
                    # Release the lock
                    db.execute(text("SELECT pg_advisory_unlock(12346)"))
                    db.commit()
            else:
                # Another worker has the lock, wait and check if admin user exists
                print("[STARTUP] Another worker is creating admin user, waiting...")
                import time
                
                # Wait up to 5 seconds for admin user to be created
                max_wait = 5
                wait_interval = 0.5
                waited = 0
                admin_exists = False
                
                while waited < max_wait:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    
                    # Check if admin user exists
                    try:
                        user = db.query(User).filter(
                            (User.email == admin_email) | 
                            (User.phone == (admin_phone or ""))
                        ).first()
                        if user:
                            admin_exists = True
                            break
                    except Exception:
                        pass  # Ignore errors during admin check
                
                if admin_exists:
                    print(f"[STARTUP] Admin user already exists: {admin_email}")
                else:
                    # Admin user doesn't exist after waiting, try to create/update
                    print("[STARTUP] Admin user not found after waiting, trying to create/update...")
                    try:
                        user = db.query(User).filter(
                            (User.email == admin_email) | 
                            (User.phone == (admin_phone or ""))
                        ).first()
                        
                        if user:
                            # Update existing user - always update password_hash to ensure it matches .env
                            user.email = admin_email
                            user.role = "admin"
                            user.is_active = True
                            user.phone_verified = True
                            user.name = user.name or "Administrator"
                            user.password_hash = hash_password(admin_password)
                            if admin_phone:
                                user.phone = admin_phone
                            db.commit()
                            print(f"[STARTUP] Updated existing user to admin: {admin_email} (password updated)")
                        else:
                            # Create new user
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
                            print(f"[STARTUP] Created admin user: {admin_email}")
                    except IntegrityError as e:
                        db.rollback()
                        error_str = str(e).lower()
                        if "duplicate key" in error_str or "already exists" in error_str:
                            # User already exists, try to update
                            user = db.query(User).filter(User.email == admin_email).first()
                            if not user and admin_phone:
                                user = db.query(User).filter(User.phone == admin_phone).first()
                            
                            if user:
                                # Always update password_hash to ensure it matches .env
                                user.email = admin_email
                                user.role = "admin"
                                user.is_active = True
                                user.phone_verified = True
                                user.name = user.name or "Administrator"
                                user.password_hash = hash_password(admin_password)
                                if admin_phone:
                                    user.phone = admin_phone
                                db.commit()
                                print(f"[STARTUP] Updated existing user to admin: {admin_email} (password updated)")
                            else:
                                print(f"[STARTUP] Admin user already exists (race condition handled)")
                        else:
                            print(f"[STARTUP] Warning: Admin user creation error: {e}")
                    except Exception as e:
                        error_str = str(e).lower()
                        if "duplicate key" in error_str or "already exists" in error_str:
                            print(f"[STARTUP] Admin user already exists (race condition handled)")
                        else:
                            print(f"[STARTUP] Warning: Admin user setup error: {e}")
    except Exception as e:
        # Fallback: try to create/update admin user without lock
        error_str = str(e).lower()
        if "duplicate key" in error_str or "already exists" in error_str:
            print(f"[STARTUP] Admin user already exists (fallback)")
        else:
            print(f"[STARTUP] Warning: Admin user setup error: {e}")
            # Try fallback creation
            try:
                if not db:
                    db = SessionLocal()
                from app.core.config import settings as _settings
                admin_email = _settings.ADMIN_EMAIL
                admin_password = _settings.ADMIN_PASSWORD
                admin_phone = _settings.ADMIN_PHONE
                
                if admin_email and admin_password:
                    user = db.query(User).filter(
                        (User.email == admin_email) | 
                        (User.phone == (admin_phone or ""))
                    ).first()
                    
                    if user:
                        # Always update password_hash to ensure it matches .env
                        user.email = admin_email
                        user.role = "admin"
                        user.is_active = True
                        user.phone_verified = True
                        user.name = user.name or "Administrator"
                        user.password_hash = hash_password(admin_password)
                        if admin_phone:
                            user.phone = admin_phone
                        db.commit()
                        print(f"[STARTUP] Updated existing user to admin (fallback): {admin_email} (password updated)")
            except:
                pass
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass  # Ignore close errors

# Health check
@app.get("/")
async def root():
    return {"message": "Metastream API", "version": "2.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

