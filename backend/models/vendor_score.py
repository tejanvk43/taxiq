from typing import Literal, Optional

from pydantic import BaseModel


Trend = Literal["UP", "DOWN", "FLAT"]


class VendorScore(BaseModel):
    gstin: str
    nexusScore: int
    grade: str
    filingRate: int
    gstr2bReflectance: int
    itcAccuracy: int
    networkRisk: int
    ewayCompliance: int
    trend: Trend
    lastUpdated: str
    loanEligible: bool
    loanLimit: int
    creditRating: str
    loanOfferApr: Optional[float] = None
    loanTenorMonths: Optional[int] = None
