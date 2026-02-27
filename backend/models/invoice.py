from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class HSNLine(BaseModel):
    hsn: str
    taxable_value: float = Field(ge=0)
    cgst: float = Field(default=0, ge=0)
    sgst: float = Field(default=0, ge=0)
    igst: float = Field(default=0, ge=0)


class Invoice(BaseModel):
    vendor_name: str
    vendor_gstin: Optional[str] = None
    buyer_gstin: Optional[str] = None
    invoice_number: str
    invoice_date: str  # YYYY-MM-DD
    total_value: float = Field(ge=0)
    taxable_value: float = Field(ge=0)
    cgst: float = Field(default=0, ge=0)
    sgst: float = Field(default=0, ge=0)
    igst: float = Field(default=0, ge=0)
    hsn_codes: List[HSNLine] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0, le=1)
    demo_data: bool = False

