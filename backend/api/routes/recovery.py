from fastapi import APIRouter, Query

from backend.core.itc_recovery import ITCRecoveryPipeline

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


@router.get("/pipeline")
async def get_recovery_pipeline(
    gstin: str = Query(default="29AAACN0001A1Z5"),
    period: str = Query(default="2024-01"),
):
    pipeline = ITCRecoveryPipeline()
    return await pipeline.get_pipeline(gstin=gstin, period=period)


@router.get("/trend")
async def get_recovery_trend(months: int = Query(default=6, le=12)):
    pipeline = ITCRecoveryPipeline()
    return {"trend": await pipeline.get_trend(months=months)}
