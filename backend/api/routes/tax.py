"""
TaxIQ — Tax Intelligence API Routes
Cross-layer enrichment + Investment calendar + Dashboard KPIs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.tax_engine.cross_layer_enricher import CrossLayerEnricher
from backend.tax_engine.investment_calendar import InvestmentCalendar

router = APIRouter(prefix="/api/tax", tags=["tax"])


class EnrichmentRequest(BaseModel):
    invoices: List[Dict[str, Any]] = []
    existing_deductions: Dict[str, float] = {}


class CalendarRequest(BaseModel):
    gap_report: Dict[str, Any] = {}


@router.post("/enrichment")
async def find_hidden_deductions(req: EnrichmentRequest):
    """Scan GST invoices for missed ITR deductions."""
    enricher = CrossLayerEnricher()
    deductions = enricher.find_missed_deductions(
        invoices=req.invoices,
        existing_deductions=req.existing_deductions,
    )
    total_saved = sum(d.get("estimated_tax_saved", 0) for d in deductions)
    return {
        "deductions": [
            {
                "invoice": d.get("invoice_id", ""),
                "vendor": d.get("vendor_name", ""),
                "hsn": d.get("hsn_code", ""),
                "section": d.get("tax_section", "").split()[-1] if d.get("tax_section") else "",
                "description": d.get("suggested_deduction", ""),
                "invoice_amount": d.get("amount", 0),
                "estimated_tax_saved": d.get("estimated_tax_saved", 0),
                "confidence": d.get("confidence", 0),
                "note": d.get("note", ""),
            }
            for d in deductions
        ],
        "total_tax_saved": total_saved,
        "count": len(deductions),
    }


@router.post("/calendar")
async def generate_investment_calendar(req: CalendarRequest):
    """Generate month-by-month investment plan from gap report."""
    calendar = InvestmentCalendar()
    return calendar.generate(gap_report=req.gap_report)
