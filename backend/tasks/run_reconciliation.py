import asyncio

from backend.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2)
def run_reconciliation(self, gstin: str, period: str) -> dict:
    """Run full GSTR reconciliation asynchronously."""
    try:
        from backend.core.reconciliation_engine import ReconciliationEngine
        engine = ReconciliationEngine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.reconcile(gstin, period)
        )
        # Push WebSocket event if manager available
        try:
            from backend.services.ws_manager import manager
            asyncio.get_event_loop().run_until_complete(
                manager.broadcast(gstin, {
                    "type": "RECONCILIATION_COMPLETE",
                    "payload": {
                        "gstin": gstin,
                        "mismatches": result.get("total_invoices_checked", 0),
                        "itcAtRisk": result.get("total_itc_at_risk", 0),
                    },
                })
            )
        except Exception:
            pass
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
