import asyncio

from backend.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def ingest_gstr1(self, gstin: str, period: str) -> dict:
    """Fetch GSTR-1 from mock GSTN and store."""
    try:
        from backend.services.gstn_client import GSTNClient
        client = GSTNClient()
        data = asyncio.get_event_loop().run_until_complete(
            client.get_gstr1(gstin, period)
        )
        invoices = []
        for b2b in data.get("b2b", []):
            invoices.extend(b2b.get("inv", []))
        try:
            from backend.database.postgres_client import postgres_client
            postgres_client.store_gstr1(gstin, period, invoices)
        except Exception:
            pass  # DB optional
        return {
            "gstin": gstin,
            "period": period,
            "status": "success",
            "invoices_ingested": len(invoices),
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
