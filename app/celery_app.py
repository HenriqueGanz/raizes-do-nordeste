from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "raizes",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=5,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
