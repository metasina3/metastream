"""
Celery tasks for database backup
"""
from celery import shared_task
from app.core.config import settings
import subprocess
import os
from datetime import datetime
from app.utils.telegram import send_file_to_telegram

@shared_task(queue='default')
def backup_database():
    """
    Backup PostgreSQL database and send to Telegram
    """
    if not settings.BACKUP_ENABLED:
        return {"success": False, "error": "Backup disabled"}
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"/tmp/metastream_backup_{timestamp}.sql"
        
        # Build pg_dump command
        db_host = os.getenv("POSTGRES_HOST", "db")  # Default to 'db' service name
        cmd = [
            "pg_dump",
            "-h", db_host,
            "-U", settings.POSTGRES_USER,
            "-d", settings.POSTGRES_DB,
            "-f", backup_file
        ]
        
        # Set password via env
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.POSTGRES_PASSWORD
        
        # Execute backup
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        
        # Compress
        subprocess.run(["gzip", backup_file])
        backup_file += ".gz"
        
        # Send to Telegram if enabled
        if settings.BACKUP_TELEGRAM_ENABLED and settings.BACKUP_TELEGRAM_CHAT_ID:
            send_file_to_telegram(backup_file, settings.BACKUP_TELEGRAM_CHAT_ID)
        
        # Cleanup
        os.remove(backup_file)
        
        return {"success": True, "file": backup_file}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

