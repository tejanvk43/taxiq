from typing import Literal, Optional

from pydantic import BaseModel


MismatchType = Literal[
    "TYPE_1",  # Invoice Missing in GSTR-2B
    "TYPE_2",  # Taxable Value Mismatch
    "TYPE_3",  # Tax Rate Mismatch
    "TYPE_4",  # GSTIN Mismatch
    "TYPE_5",  # Period Mismatch
    # Legacy aliases kept for backward compatibility
    "MATCHED",
    "MISMATCH_AMOUNT",
    "MISSING_GSTR1",
    "ITC_NOT_REFLECTED",
    "EWAYBILL_MISMATCH",
    "VENDOR_RISK",
    "ITC_EXCESS",
]

MISMATCH_LABELS = {
    "TYPE_1": "Invoice Missing in GSTR-2B",
    "TYPE_2": "Taxable Value Mismatch",
    "TYPE_3": "Tax Rate Mismatch",
    "TYPE_4": "GSTIN Mismatch",
    "TYPE_5": "Period Mismatch",
}

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
    supplierAmount: Optional[float] = None
    buyerAmount: Optional[float] = None
    difference: Optional[float] = None
