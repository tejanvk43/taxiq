from typing import Literal, Optional

from pydantic import BaseModel


MismatchType = Literal[
    "MATCHED",
    "MISMATCH_AMOUNT",
    "MISSING_GSTR1",
    "ITC_NOT_REFLECTED",
    "EWAYBILL_MISMATCH",
    "VENDOR_RISK",
    "ITC_EXCESS",
]

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class Mismatch(BaseModel):
    invoiceId: str
    gstin: str
    vendorGstin: str
    period: str
    mismatchType: MismatchType
    riskLevel: RiskLevel
    severity: int  # 1..100
    amount: float
    detail: Optional[str] = None
