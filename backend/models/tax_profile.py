from pydantic import BaseModel, Field


class TaxProfile(BaseModel):
    name: str = "User"
    annual_income: float = Field(ge=0)
    age: int = Field(ge=0, le=120)
    has_senior_parents: bool = False

