"""
Celery Application — Background task processing for Masaad Estimator.
Handles CPU-heavy work: PDF extraction, BOM explosion, DXF parsing, report generation.
This prevents FastAPI timeouts on Railway (30s limit).

Beat schedule:
  refresh_lme_prices — daily 08:00 GST (04:00 UTC) — fetches LME Aluminum USD/MT
"""
import os
from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "masaad",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Dubai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,   # 5 minutes soft limit
    task_time_limit=600,        # 10 minutes hard limit
    result_expires=3600,        # Results expire after 1 hour
    # ── Beat schedule ────────────────────────────────────────────────────────
    beat_schedule={
        "refresh-lme-daily": {
            "task": "tasks.refresh_lme_prices",
            # 08:00 GST = UTC+4, so 04:00 UTC
            "schedule": crontab(hour=4, minute=0),
            "options": {"expires": 3600},
        },
    },
)
