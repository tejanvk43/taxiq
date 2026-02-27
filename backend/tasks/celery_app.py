import os

from celery import Celery


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


celery_app = Celery(
    "taxiq",
    broker=_redis_url(),
    backend=_redis_url(),
    include=[
        "backend.tasks.ingest_gstr1",
        "backend.tasks.ingest_gstr2b",
        "backend.tasks.run_reconciliation",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
