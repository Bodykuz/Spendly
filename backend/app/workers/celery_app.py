"""Celery app + beat schedule."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "spendly",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=600,
    timezone="Europe/Warsaw",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "nightly-full-sync": {
        "task": "app.workers.tasks.sync_all_connections",
        "schedule": crontab(hour=3, minute=30),
    },
    "detect-insights-daily": {
        "task": "app.workers.tasks.refresh_insights_all_users",
        "schedule": crontab(hour=4, minute=15),
    },
}
