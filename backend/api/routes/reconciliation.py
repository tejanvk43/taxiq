from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from backend.core.reconciliation_engine import ReconciliationEngine
from backend.services.ws_manager import manager

router = APIRouter(prefix="/api/reconcile", tags=["reconciliation"])


class ReconcileRequest(BaseModel):
    gstin: str
    period: str


@router.post("/run")
async def run_reconciliation(req: ReconcileRequest):
    engine = ReconciliationEngine()
    result = await engine.reconcile_gstin(gstin=req.gstin, period=req.period)

    await manager.broadcast(
        req.gstin,
        {
            "type": "RECON_COMPLETE",
            "payload": {"jobId": result["jobId"], "matched": result["summary"]["matched"], "mismatches": result["summary"]["mismatches"]},
        },
    )
    return result


@router.get("/status/{job_id}")
async def get_reconciliation_status(job_id: str):
    return {"jobId": job_id, "status": "COMPLETE", "progress": 1.0}


@router.get("/mismatches/{gstin}")
async def get_mismatches(
    gstin: str,
    period: str = "2024-01",
    status: str | None = None,
    risk_level: str | None = None,
    sort_by: str = "severity",
    page: int = 1,
    limit: int = 50,
):
    engine = ReconciliationEngine()
    mismatches = await engine.list_mismatches(gstin=gstin, period=period)

    if status:
        mismatches = [m for m in mismatches if m.mismatchType == status]
    if risk_level:
        mismatches = [m for m in mismatches if m.riskLevel == risk_level]

    if sort_by == "amount":
        mismatches.sort(key=lambda m: m.amount, reverse=True)
    else:
        mismatches.sort(key=lambda m: m.severity, reverse=True)

    start = (page - 1) * limit
    end = start + limit
    return {"gstin": gstin, "period": period, "items": [m.model_dump() for m in mismatches[start:end]], "total": len(mismatches)}


@router.get("/audit-trail/{invoice_id}")
async def get_audit_trail(invoice_id: str):
    engine = ReconciliationEngine()
    return await engine.get_audit_trail(invoice_id=invoice_id)
