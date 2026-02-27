from pydantic import BaseModel, Field


class Transaction(BaseModel):
    date: str
    description: str
    amount: float
    txn_type: str  # DEBIT/CREDIT
    tax_category: str = ""
    tax_section: str = ""
    is_deductible: bool = False
    confidence: float = Field(default=0.5, ge=0, le=1)

