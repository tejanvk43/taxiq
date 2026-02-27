from fastapi import APIRouter

from backend.core.itc_recovery import ITCRecoveryPipeline

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


@router.get("/pipeline")
async def get_recovery_pipeline(gstin: str, period: str = "2024-01"):
    pipeline = ITCRecoveryPipeline()
    return await pipeline.get_pipeline(gstin=gstin, period=period)
