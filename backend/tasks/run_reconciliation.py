from backend.tasks.celery_app import celery_app


@celery_app.task
def run_reconciliation(gstin: str, period: str) -> dict:
    # Scaffold: call ReconciliationEngine + push WebSocket events
    return {"gstin": gstin, "period": period, "status": "NOT_IMPLEMENTED"}
