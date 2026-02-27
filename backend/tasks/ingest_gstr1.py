from backend.tasks.celery_app import celery_app


@celery_app.task
def ingest_gstr1(gstin: str, period: str) -> dict:
    # Scaffold: implement GSTN polling + Neo4j upsert
    return {"gstin": gstin, "period": period, "status": "NOT_IMPLEMENTED"}
