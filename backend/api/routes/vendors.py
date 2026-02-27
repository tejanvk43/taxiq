import time
from collections import defaultdict
from typing import DefaultDict

from fastapi import APIRouter, Header, HTTPException

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
    _ = sort_by
    _ = order
    scorer = NexusScorer()
    demo = ["19AABCG1234Q1Z2", "27AAACF9999K1Z9", "07AABCS7777H1Z1"]
    items = [await scorer.calculate_score(x) for x in demo]
    if risk_level:
        if risk_level == "HIGH":
            items = [x for x in items if x["nexusScore"] < 40]
        elif risk_level == "MEDIUM":
            items = [x for x in items if 40 <= x["nexusScore"] < 70]
        elif risk_level == "LOW":
            items = [x for x in items if x["nexusScore"] >= 70]
    return {"vendors": items}


@router.get("/{gstin}/history")
async def get_vendor_history(gstin: str, months: int = 12):
    scorer = NexusScorer()
    base = await scorer.calculate_score(gstin=gstin)
    history = []
    score = base["nexusScore"]
    for i in range(months):
        history.append({"monthOffset": i, "score": max(5, min(99, score - i * 2))})
    return {"gstin": gstin, "history": history}
