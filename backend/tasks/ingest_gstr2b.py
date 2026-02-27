from backend.tasks.celery_app import celery_app


@celery_app.task
def ingest_gstr2b(gstin: str, period: str) -> dict:
    return {"gstin": gstin, "period": period, "status": "NOT_IMPLEMENTED"}
