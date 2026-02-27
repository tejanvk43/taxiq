import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from backend.services.mock_gstn import MockGSTNClient


class GSTNClient:
    """
    GSTN API client.
    When MOCK_GSTN=true (default for hackathon), delegates to MockGSTNClient
    and returns realistic structured JSON matching GSTN API schema.
    When MOCK_GSTN=false, would call real GSP endpoint (not wired for hackathon).
    """

    BASE_URL = "https://api.gst.gov.in"

    def __init__(self) -> None:
        self.api_key = os.getenv("GSTN_API_KEY", "")
        self.mock_mode = os.getenv("MOCK_GSTN", "true").lower() == "true"
        self._mock = MockGSTNClient()
        self._rng = random.Random(42)

    async def get_gstr1(self, gstin: str, period: str, otp: str = "") -> Dict[str, Any]:
        """Fetch GSTR-1 (outward supplies filed by supplier)."""
        raw = await self._mock.get_gstr1(gstin=gstin, period=period, otp=otp)
        invoices = raw.get("invoices", [])
        b2b_entries = []
        for inv in invoices:
            tax_amt = inv.get("taxAmount", round(inv.get("amount", 0) * 0.18, 2))
            cgst = round(tax_amt / 2, 2)
            sgst = round(tax_amt / 2, 2)
            b2b_entries.append({
                "inum": inv.get("invoiceId", f"INV-{period}-001"),
                "idt": inv.get("date", f"{period}-15"),
                "val": inv.get("amount", 0),
                "txval": round(inv.get("amount", 0) / 1.18, 2),
                "camt": cgst,
                "samt": sgst,
                "iamt": 0.0,
                "inv_typ": "R",
                "pos": "27",
                "rchrg": "N",
                "irn": inv.get("irn", ""),
            })
        return {
            "gstin": gstin,
            "fp": period.replace("-", ""),
            "filed": raw.get("filed", True),
            "filing_date": f"{period}-11",
            "b2b": [{
                "ctin": gstin,
                "inv": b2b_entries,
            }],
            "total_invoices": len(b2b_entries),
            "total_value": sum(e["val"] for e in b2b_entries),
            "total_tax": sum(e["camt"] + e["samt"] + e["iamt"] for e in b2b_entries),
        }

    async def get_gstr2b(self, gstin: str, period: str) -> Dict[str, Any]:
        """Fetch GSTR-2B (auto-drafted ITC statement for buyer)."""
        gstr1 = await self._mock.get_gstr1(gstin=gstin, period=period)
        all_invoices = gstr1.get("invoices", [])
        # Simulate real-world: ~85% of GSTR-1 invoices reflect in GSTR-2B
        reflected = []
        missing = []
        for inv in all_invoices:
            if self._rng.random() < 0.85:
                tax_amt = inv.get("taxAmount", round(inv.get("amount", 0) * 0.18, 2))
                # Occasionally introduce amount mismatch (~10%)
                amount = inv["amount"]
                if self._rng.random() < 0.10:
                    amount = round(amount * (1 + self._rng.uniform(-0.08, 0.08)), 2)
                reflected.append({
                    "inum": inv["invoiceId"],
                    "idt": inv.get("date", f"{period}-15"),
                    "val": amount,
                    "txval": round(amount / 1.18, 2),
                    "itc_avail": round(amount * 0.18 / 1.18, 2),
                    "tax_rate": 18.0,
                    "supplier_gstin": gstin,
                    "irn": inv.get("irn", ""),
                })
            else:
                missing.append(inv["invoiceId"])
        return {
            "gstin": gstin,
            "fp": period.replace("-", ""),
            "generated_on": f"{period}-12",
            "b2b": [{
                "ctin": gstin,
                "inv": reflected,
            }],
            "total_reflected": len(reflected),
            "total_missing": len(missing),
            "missing_invoice_ids": missing,
            "total_itc_available": sum(e["itc_avail"] for e in reflected),
        }

    async def get_filing_status(self, gstin: str) -> Dict[str, Any]:
        """Fetch filing compliance status for the last 12 months."""
        raw = await self._mock.get_filing_status(gstin=gstin)
        months = raw.get("months", [])
        filed_count = sum(1 for m in months if m.get("filed"))
        total = len(months) or 1
        return {
            "gstin": gstin,
            "filing_rate": round(filed_count / total * 100, 1),
            "months": [
                {
                    "period": m["period"],
                    "gstr1_filed": m.get("filed", False),
                    "gstr3b_filed": m.get("filed", False),
                    "filing_date": f"{m['period']}-11" if m.get("filed") else None,
                    "late": self._rng.random() < 0.15 if m.get("filed") else False,
                }
                for m in months
            ],
            "overall_compliance": "GOOD" if filed_count / total > 0.9 else "POOR" if filed_count / total < 0.7 else "MODERATE",
            "last_checked": datetime.utcnow().isoformat() + "Z",
        }
