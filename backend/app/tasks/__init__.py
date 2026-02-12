"""
Celery task queue configuration
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "real_estate",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])
