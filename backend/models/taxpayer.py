from typing import Literal, Optional

from pydantic import BaseModel


RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class Taxpayer(BaseModel):
    gstin: str
    name: str
    state: str
    riskLevel: RiskLevel
    nexusScore: int
    complianceScore: Optional[int] = None
