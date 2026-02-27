from fastapi import APIRouter, Query

from backend.core.fraud_detector import FraudDetector

router = APIRouter(prefix="/api/fraud", tags=["fraud"])


@router.get("/rings")
async def list_fraud_rings(min_confidence: float = Query(default=0.6), min_amount: float = Query(default=100000)):
    detector = FraudDetector()
    rings = await detector.detect_circular_rings()
    rings = [r for r in rings if r["confidence"] >= min_confidence and r["fraudAmount"] >= min_amount]
    return {"rings": rings}


@router.get("/shell-companies")
async def list_shell_companies():
    detector = FraudDetector()
    shells = await detector.detect_shell_companies()
    return {"shells": shells}
