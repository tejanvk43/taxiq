from datetime import datetime
from typing import Any, Dict

from backend.utils.llm_client import LLMClient


class NoticeGenerator:
    def __init__(self) -> None:
        self.llm = LLMClient()

    async def generate(
        self,
        vendor_gstin: str,
        notice_type: str,
        period: str,
        amount: float,
        section: str,
    ) -> Dict[str, Any]:
        prompt = (
            "You are a GST legal expert. Draft a formal notice under "
            f"{section} of CGST Act 2017 for {notice_type} by GSTIN {vendor_gstin} "
            f"for period {period}. ITC blocked: ₹{amount}. "
            "Include: legal citations, 7-day compliance window, consequences. "
            "Output: formal letter format only, no explanations."
        )
        try:
            draft = self.llm.ask(prompt)
        except Exception:
            draft = prompt.replace(
                "You are a GST legal expert.",
                "DRAFT NOTICE (MOCK):",
            )
        return {
            "noticeId": f"NOTICE-{vendor_gstin[-4:]}-{period}",
            "vendorGstin": vendor_gstin,
            "noticeType": notice_type,
            "period": period,
            "amount": amount,
            "section": section,
            "draft": draft,
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "billing": {"priceINR": 999, "status": "UNPAID"},
        }
