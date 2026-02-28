import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List


@dataclass(frozen=True)
class _VendorProfile:
    gstin: str
    name: str
    state: str
    filing_rate: int
    base_score: int


class MockGSTNClient:
    """
    Demo generator. Intended for hackathon usage when no real GSTN API is available.
    Controlled by MOCK_GSTN=true.
    """

    def __init__(self, seed: int | None = None) -> None:
        seed_env = os.getenv("MOCK_SEED")
        final_seed = seed if seed is not None else int(seed_env) if seed_env else 76
        self._rng = random.Random(final_seed)
        self._vendors = [
            _VendorProfile("19AABCG1234Q1Z2", "GoldStar Traders", "WB", filing_rate=42, base_score=18),
            _VendorProfile("27AAACF9999K1Z9", "Falcon Components", "MH", filing_rate=86, base_score=52),
            _VendorProfile("07AABCS7777H1Z1", "Shadow Supplies", "DL", filing_rate=55, base_score=33),
        ]

    def list_demo_taxpayers(self) -> list[Dict[str, Any]]:
        return [
            {
                "gstin": "29AAACN0001A1Z5",
                "name": "Nexus Demo Manufacturing",
                "state": "KA",
                "riskLevel": "LOW",
                "nexusScore": 86,
                "complianceScore": 90,
            },
            *[
                {
                    "gstin": v.gstin,
                    "name": v.name,
                    "state": v.state,
                    "riskLevel": "HIGH" if v.base_score < 40 else "MEDIUM",
                    "nexusScore": v.base_score,
                    "complianceScore": max(10, min(99, v.base_score + 5)),
                }
                for v in self._vendors
            ],
        ]

    async def get_gstr1(self, gstin: str, period: str, otp: str | None = None) -> Dict[str, Any]:
        # Use GSTIN + period as seed so each query produces unique but deterministic data
        seed = hash((gstin, period)) & 0xFFFFFFFF
        rng = random.Random(seed)
        filed = rng.random() < 0.8
        count = rng.randint(12, 35)
        invoices = self._generate_invoices(gstin=gstin, period=period, count=count, rng=rng)
        return {"gstin": gstin, "period": period, "filed": filed, "invoices": invoices}

    async def get_gstr2b(self, gstin: str, period: str) -> Dict[str, Any]:
        return {"gstin": gstin, "period": period, "generatedOn": f"{period}-12"}

    async def get_filing_status(self, gstin: str) -> Dict[str, Any]:
        # Deterministic per-GSTIN filing history
        seed = hash(gstin) & 0xFFFFFFFF
        rng = random.Random(seed)
        now = datetime.utcnow()
        history = []
        for i in range(12):
            month = (now - timedelta(days=30 * i)).strftime("%Y-%m")
            history.append({"period": month, "filed": rng.random() < 0.82})
        return {"gstin": gstin, "months": history}

    def _generate_invoices(self, gstin: str, period: str, count: int,
                           rng: random.Random | None = None) -> List[Dict[str, Any]]:
        rng = rng or random.Random(hash((gstin, period)) & 0xFFFFFFFF)
        # Use last 6 chars of GSTIN as prefix for invoice IDs to make them unique
        gstin_tag = gstin[-6:-1] if len(gstin) >= 6 else gstin
        out = []
        for i in range(count):
            invoice_id = f"INV-{gstin_tag}-{period}-{i+1:03d}"
            amount = float(rng.randint(45_000, 650_000))
            tax = round(amount * 0.18, 2)
            day = rng.randint(1, 28)
            out.append(
                {
                    "invoiceId": invoice_id,
                    "irn": f"IRN-{gstin_tag}-{period.replace('-', '')}-{i+1:03d}",
                    "amount": amount,
                    "taxAmount": tax,
                    "date": f"{period}-{day:02d}",
                    "status": "UNKNOWN",
                }
            )
        return out
