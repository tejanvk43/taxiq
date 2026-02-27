from __future__ import annotations

from datetime import date
from typing import Dict

import pandas as pd

from backend.tax_engine.sections import TAX_SECTIONS


def _months_remaining_till_march31(today: date) -> int:
    fy_end = date(today.year, 3, 31)
    if today > fy_end:
        fy_end = date(today.year + 1, 3, 31)
    return max(0, (fy_end.year - today.year) * 12 + (fy_end.month - today.month) + (1 if fy_end.day >= today.day else 0))


def _applicable_tax_rate(income: float) -> float:
    # Simple marginal slab approximation (old regime): 0/5/20/30 + cess.
    if income > 1_000_000:
        base = 0.30
    elif income > 500_000:
        base = 0.20
    elif income > 250_000:
        base = 0.05
    else:
        base = 0.0
    return base * 1.04


def analyze_gaps(df: pd.DataFrame, annual_income: float, age: int, has_senior_parents: bool) -> Dict:
    """
    Sum investments per tax_section; compare to limits; compute gaps + urgency + potential saving.
    """
    _ = age
    invested = df[df["is_deductible"] == True].groupby("tax_section")["amount"].sum().to_dict()  # noqa: E712
    today = date.today()
    months_remaining = _months_remaining_till_march31(today)
    tax_rate = _applicable_tax_rate(annual_income)

    report = {}

    # 80C
    lim_80c = TAX_SECTIONS["80C"]["limit"]
    cur_80c = float(invested.get("80C", 0.0))
    gap_80c = max(0.0, lim_80c - cur_80c)
    report["80C"] = _build_row(cur_80c, lim_80c, gap_80c, months_remaining, tax_rate)

    # 80D
    lim_80d = TAX_SECTIONS["80D"]["limit_senior"] if age >= 60 else TAX_SECTIONS["80D"]["limit_below60"]
    if has_senior_parents:
        lim_80d += TAX_SECTIONS["80D"]["limit_parents_senior"]
    cur_80d = float(invested.get("80D", 0.0))
    gap_80d = max(0.0, lim_80d - cur_80d)
    report["80D"] = _build_row(cur_80d, lim_80d, gap_80d, months_remaining, tax_rate)

    # 80CCD1B
    lim_nps = TAX_SECTIONS["80CCD1B"]["limit"]
    cur_nps = float(invested.get("80CCD1B", 0.0))
    gap_nps = max(0.0, lim_nps - cur_nps)
    report["80CCD1B"] = _build_row(cur_nps, lim_nps, gap_nps, months_remaining, tax_rate)

    # 24B (home loan interest)
    lim_24b = TAX_SECTIONS["24B"]["limit"]
    cur_24b = float(invested.get("24B", 0.0))
    gap_24b = max(0.0, lim_24b - cur_24b)
    report["24B"] = _build_row(cur_24b, lim_24b, gap_24b, months_remaining, tax_rate)

    return {
        "asOf": today.isoformat(),
        "annualIncome": annual_income,
        "monthsRemaining": months_remaining,
        "sections": report,
        "taxRateApprox": tax_rate,
    }


def _build_row(current: float, limit: float | str | None, gap: float, months_remaining: int, tax_rate: float) -> Dict:
    if isinstance(limit, (int, float)):
        urgency = "high" if gap > 0.5 * limit else "medium" if gap > 0.2 * limit else "low"
        potential = round(gap * tax_rate, 2)
    else:
        urgency = "low"
        potential = 0.0
    return {
        "current_investment": round(float(current), 2),
        "limit": limit,
        "gap": round(float(gap), 2),
        "months_remaining": months_remaining,
        "urgency_level": urgency,
        "potential_tax_saving": potential,
    }

