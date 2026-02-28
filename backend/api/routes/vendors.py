import time
from collections import defaultdict
from typing import DefaultDict

from fastapi import APIRouter, Header, HTTPException, Query

from backend.core.nexus_scorer import NexusScorer

router = APIRouter(prefix="/api/vendors", tags=["vendors"])

# Hackathon-grade monetization scaffold: 100 calls/month per api_key.
_usage: DefaultDict[str, int] = defaultdict(int)
_reset_at: DefaultDict[str, float] = defaultdict(lambda: time.time() + 30 * 24 * 3600)


def _check_usage(api_key: str) -> None:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    now = time.time()
    if now >= _reset_at[api_key]:
        _usage[api_key] = 0
        _reset_at[api_key] = now + 30 * 24 * 3600
    if _usage[api_key] >= 100:
        raise HTTPException(status_code=429, detail="Free tier exceeded (100 calls/month)")
    _usage[api_key] += 1


@router.get("/score/{gstin}")
async def get_vendor_score(gstin: str):
    scorer = NexusScorer()
    return await scorer.calculate_score(gstin=gstin)


@router.get("/list")
async def list_vendors(risk_level: str | None = None, sort_by: str = "nexusScore", order: str = "desc"):
    scorer = NexusScorer()
    items = await scorer.get_all_vendor_scores(risk_level=risk_level)
    reverse = order.lower() == "desc"
    items.sort(key=lambda x: x.get(sort_by, x.get("nexusScore", 0)), reverse=reverse)
    return {"vendors": items}


@router.get("/{gstin}/history")
async def get_vendor_history(gstin: str, months: int = Query(default=6, le=12)):
    scorer = NexusScorer()
    history = await scorer.get_vendor_history(gstin=gstin, months=months)
    return {"gstin": gstin, "history": history}


@router.get("/{gstin}/predict")
async def predict_vendor_risk(gstin: str, months_ahead: int = Query(default=3, le=6)):
    """Predictive vendor compliance risk model using historical patterns."""
    scorer = NexusScorer()
    current = await scorer.calculate_score(gstin=gstin)
    history = await scorer.get_vendor_history(gstin=gstin, months=6)

    # Compute trend slope from history
    scores = [h["score"] for h in history]
    if len(scores) >= 2:
        slope = (scores[-1] - scores[0]) / max(len(scores) - 1, 1)
    else:
        slope = 0

    predictions = []
    current_score = current["nexusScore"]
    for i in range(1, months_ahead + 1):
        predicted = max(5, min(99, int(current_score + slope * i)))
        risk_flag = "IMPROVING" if slope > 1 else "DECLINING" if slope < -1 else "STABLE"
        predictions.append({
            "month_offset": i,
            "predicted_score": predicted,
            "predicted_grade": scorer._grade(predicted),
            "risk_flag": risk_flag,
            "confidence": round(max(0.5, 0.95 - i * 0.08), 2),
        })

    # Risk factors
    factors = current.get("factors", {})
    risk_factors = []
    for factor, val in factors.items():
        if val < 50:
            risk_factors.append({
                "factor": factor.replace("_", " ").title(),
                "score": val,
                "severity": "HIGH" if val < 30 else "MEDIUM",
                "recommendation": _get_recommendation(factor, val),
            })

    return {
        "gstin": gstin,
        "current_score": current_score,
        "current_grade": current.get("nexusGrade", ""),
        "trend": current.get("trend", "FLAT"),
        "slope": round(slope, 2),
        "predictions": predictions,
        "risk_factors": risk_factors,
        "overall_outlook": "IMPROVING" if slope > 1 else "DECLINING" if slope < -1 else "STABLE",
    }


def _get_recommendation(factor: str, score: int) -> str:
    recommendations = {
        "filing_regularity": "Ensure GSTR-1 and GSTR-3B are filed before due dates. Set up auto-reminders.",
        "itc_accuracy": "Reconcile purchase register with GSTR-2B monthly. Verify all ITC claims.",
        "turnover_consistency": "Maintain consistent revenue declarations. Sudden spikes trigger scrutiny.",
        "network_trustworthiness": "Review counterparty GSTINs. Avoid transacting with flagged entities.",
        "amendment_frequency": "Reduce amendments by verifying invoice details before filing.",
    }
    return recommendations.get(factor, "Monitor this metric and take corrective action.")
