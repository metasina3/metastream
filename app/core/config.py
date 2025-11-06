"""
Application Configuration
All settings loaded from environment variables
"""
from pydantic import BaseModel
from typing import Optional
import os


class Settings(BaseModel):
    # ==================== Application ====================
    APP_NAME: str = os.getenv("APP_NAME", "Metastream")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    
    # ==================== Domains ====================
    MAIN_DOMAIN: str = os.getenv("MAIN_DOMAIN", "1.metastream.ir")
    MAIN_URL: str = os.getenv("MAIN_URL", "https://1.metastream.ir")
    
    PANEL_DOMAIN: str = os.getenv("PANEL_DOMAIN", "panel1.metastream.ir")
    PANEL_URL: str = os.getenv("PANEL_URL", "https://panel1.metastream.ir")
    
    API_DOMAIN: str = os.getenv("API_DOMAIN", "api1.metastream.ir")
    API_URL: str = os.getenv("API_URL", "https://api1.metastream.ir")
    
    LIVE_DOMAIN: str = os.getenv("LIVE_DOMAIN", "live1.metastream.ir")
    LIVE_URL: str = os.getenv("LIVE_URL", "https://live1.metastream.ir")
    
    # ==================== Development ====================
    DEV_MODE: bool = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
    ALLOW_DEV_HOSTS: str = os.getenv("ALLOW_DEV_HOSTS", "localhost,127.0.0.1")
    
    # ==================== Database ====================
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "metastream")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "metastream")
    
    # ==================== Redis ====================
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    
    # ==================== Streaming ====================
    STREAM_PROXY: Optional[str] = os.getenv("STREAM_PROXY")
    
    # ==================== API ====================
    API_VERSION: str = os.getenv("API_VERSION", "v1")
    
    # ==================== SMS ====================
    SMS_GATEWAY_DEFAULT: str = os.getenv("SMS_GATEWAY_DEFAULT", "kavenegar")
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    SMS_API_URL: str = os.getenv("SMS_API_URL", "https://api.kavenegar.com/v1/")
    
    # ==================== Telegram ====================
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_PROXY_HTTP: Optional[str] = os.getenv("TELEGRAM_PROXY_HTTP")
    TELEGRAM_PROXY_SOCKS5: Optional[str] = os.getenv("TELEGRAM_PROXY_SOCKS5")
    TELEGRAM_PROXY_TYPE: str = os.getenv("TELEGRAM_PROXY_TYPE", "")
    TELEGRAM_ENABLED: bool = os.getenv("TELEGRAM_ENABLED", "false").lower() in ("true", "1", "yes")
    TELEGRAM_ADMIN_IDS: str = os.getenv("TELEGRAM_ADMIN_IDS", "")
    
    # ==================== OTP ====================
    OTP_LENGTH: int = int(os.getenv("OTP_LENGTH", "4"))
    OTP_EXPIRY: int = int(os.getenv("OTP_EXPIRY", "300"))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))
    
    # ==================== Cookie ====================
    COOKIE_DOMAIN: str = os.getenv("COOKIE_DOMAIN", ".metastream.ir")
    COOKIE_EXPIRY: int = int(os.getenv("COOKIE_EXPIRY", "10368000"))  # 4 months
    COOKIE_HTTP_ONLY: bool = os.getenv("COOKIE_HTTP_ONLY", "true").lower() in ("true", "1", "yes")
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "true").lower() in ("true", "1", "yes")
    COOKIE_SAME_SITE: str = os.getenv("COOKIE_SAME_SITE", "lax")
    
    # ==================== Phone Validation ====================
    PHONE_REGEX: str = os.getenv("PHONE_REGEX", r"^(09|\+989)\d{9}$")
    PHONE_REQUIRED_LENGTH: int = int(os.getenv("PHONE_REQUIRED_LENGTH", "11"))
    
    # ==================== Video ====================
    VIDEO_UPLOAD_MAX_SIZE: int = int(os.getenv("VIDEO_UPLOAD_MAX_SIZE", "2147483648"))  # 2GB
    VIDEO_ALLOWED_FORMATS: str = os.getenv("VIDEO_ALLOWED_FORMATS", "mp4,mkv,avi,mov")
    VIDEO_OUTPUT_FORMAT: str = os.getenv("VIDEO_OUTPUT_FORMAT", "mp4")
    VIDEO_BITRATE: str = os.getenv("VIDEO_BITRATE", "2500k")
    VIDEO_RESOLUTION: str = os.getenv("VIDEO_RESOLUTION", "1920x1080")
    
    # ==================== FFmpeg ====================
    FFMPEG_THREADS: int = int(os.getenv("FFMPEG_THREADS", "6"))
    CPU_RESERVE: int = int(os.getenv("CPU_RESERVE", "2"))
    
    # ==================== Celery ====================
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
    CELERY_TIMEZONE: str = os.getenv("CELERY_TIMEZONE", "Asia/Tehran")
    
    # ==================== Retention ====================
    COMMENT_RETENTION_DAYS: int = int(os.getenv("COMMENT_RETENTION_DAYS", "3"))
    VIEWER_LOG_RETENTION_DAYS: int = int(os.getenv("VIEWER_LOG_RETENTION_DAYS", "90"))
    MEDIA_RETENTION_DAYS: int = int(os.getenv("MEDIA_RETENTION_DAYS", "30"))
    
    # ==================== Upload ====================
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/uploads")  # Absolute path inside container
    UPLOAD_TEMP_DIR: str = os.getenv("UPLOAD_TEMP_DIR", "/app/uploads/temp")
    CHUNK_UPLOAD_SIZE: int = int(os.getenv("CHUNK_UPLOAD_SIZE", "5242880"))  # 5MB
    
    # ==================== Go Service ====================
    GO_SERVICE_URL: str = os.getenv("GO_SERVICE_URL", "http://go-service:9000")
    GO_SERVICE_TIMEOUT: int = int(os.getenv("GO_SERVICE_TIMEOUT", "30"))
    
    # ==================== Rate Limiting ====================
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    RATE_LIMIT_STORAGE: str = os.getenv("RATE_LIMIT_STORAGE", "redis://redis:6379/1")
    
    # ==================== Analytics ====================
    ANALYTICS_ENABLED: bool = os.getenv("ANALYTICS_ENABLED", "true").lower() in ("true", "1", "yes")
    ANALYTICS_RETENTION_DAYS: int = int(os.getenv("ANALYTICS_RETENTION_DAYS", "365"))
    
    # ==================== Logging ====================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    LOG_MAX_SIZE: int = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # ==================== CORS ====================
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "https://1.metastream.ir,https://panel1.metastream.ir,https://live1.metastream.ir")
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    
    # ==================== Security ====================
    ALLOWED_IPS: str = os.getenv("ALLOWED_IPS", "")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "ms_session")
    SESSION_SECURE: bool = os.getenv("SESSION_SECURE", "true").lower() in ("true", "1", "yes")
    SESSION_HTTP_ONLY: bool = os.getenv("SESSION_HTTP_ONLY", "true").lower() in ("true", "1", "yes")
    
    # ==================== Features ====================
    FEATURE_OTP_ENABLED: bool = os.getenv("FEATURE_OTP_ENABLED", "true").lower() in ("true", "1", "yes")
    FEATURE_TELEGRAM_NOTIFICATIONS: bool = os.getenv("FEATURE_TELEGRAM_NOTIFICATIONS", "true").lower() in ("true", "1", "yes")
    FEATURE_ANALYTICS_EXPORT: bool = os.getenv("FEATURE_ANALYTICS_EXPORT", "true").lower() in ("true", "1", "yes")
    FEATURE_API_UPLOAD: bool = os.getenv("FEATURE_API_UPLOAD", "true").lower() in ("true", "1", "yes")
    FEATURE_COMMENT_MODERATION: bool = os.getenv("FEATURE_COMMENT_MODERATION", "true").lower() in ("true", "1", "yes")
    FEATURE_ADMIN_IMPERSONATION: bool = os.getenv("FEATURE_ADMIN_IMPERSONATION", "true").lower() in ("true", "1", "yes")
    
    # ==================== Backup ====================
    BACKUP_ENABLED: bool = os.getenv("BACKUP_ENABLED", "true").lower() in ("true", "1", "yes")
    BACKUP_INTERVAL_HOURS: int = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))
    BACKUP_RETENTION_COUNT: int = int(os.getenv("BACKUP_RETENTION_COUNT", "7"))
    BACKUP_TELEGRAM_ENABLED: bool = os.getenv("BACKUP_TELEGRAM_ENABLED", "true").lower() in ("true", "1", "yes")
    BACKUP_TELEGRAM_CHAT_ID: str = os.getenv("BACKUP_TELEGRAM_CHAT_ID", "")
    BACKUP_SCHEDULED_TIME: str = os.getenv("BACKUP_SCHEDULED_TIME", "03:00")
    
    # ==================== Timezone ====================
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tehran")
    
    # ==================== Admin ====================
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@metastream.ir")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "change-this")
    ADMIN_PHONE: str = os.getenv("ADMIN_PHONE", "09123456789")
    
    # ==================== Support ====================
    SUPPORT_TELEGRAM: str = os.getenv("SUPPORT_TELEGRAM", "metasina30")
    SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL", "support@metastream.ir")


settings = Settings()

# Normalize upload directories to absolute paths inside container
if not os.path.isabs(settings.UPLOAD_DIR):
    settings.UPLOAD_DIR = os.path.join('/app', settings.UPLOAD_DIR.lstrip('/'))
if not os.path.isabs(settings.UPLOAD_TEMP_DIR):
    settings.UPLOAD_TEMP_DIR = os.path.join('/app', settings.UPLOAD_TEMP_DIR.lstrip('/'))

# Avoid read-only code mount path
if settings.UPLOAD_DIR.startswith('/app/app'):
    settings.UPLOAD_DIR = '/app/uploads'
if settings.UPLOAD_TEMP_DIR.startswith('/app/app'):
    settings.UPLOAD_TEMP_DIR = '/app/uploads/temp'

