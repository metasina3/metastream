"""
Celery Configuration
"""
from celery import Celery
from app.core.config import settings
from celery.schedules import crontab

# Create Celery app
celery_app = Celery(
    "metastream",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Import tasks to register them
from app import tasks  # noqa: F401

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
    
    # Result settings
    result_expires=3600,
    
    # Task routing
    task_routes={
        'app.tasks.video.*': {'queue': 'prep'},
        'app.tasks.stream.*': {'queue': 'stream'},
    },
    
    # Task time limits
    task_soft_time_limit=300,
    task_time_limit=600,

    # Beat schedule
    beat_schedule={
        'cleanup-rejected-videos-hourly': {
            'task': 'app.tasks.cleanup.cleanup_rejected_videos',
            'schedule': crontab(minute=0, hour='*'),
        },
        'cleanup-rejected-channels-daily': {
            'task': 'app.tasks.cleanup.cleanup_rejected_channels',
            'schedule': crontab(hour=3, minute=0),  # Every day at 3 AM
        },
        'check-and-start-streams': {
            'task': 'app.tasks.stream.check_and_start_streams',
            'schedule': 30.0,  # Every 30 seconds
        },
        'check-live-streams': {
            'task': 'app.tasks.stream.check_live_streams',
            'schedule': 60.0,  # Every 60 seconds
        },
        'monitor-stream-workers': {
            'task': 'app.tasks.stream.monitor_stream_workers',
            'schedule': 60.0,  # Every 60 seconds
        },
        'auto-approve-comments': {
            'task': 'app.tasks.comments.auto_approve_comments',
            'schedule': 5.0,  # Every 5 seconds
        },
    },
)

