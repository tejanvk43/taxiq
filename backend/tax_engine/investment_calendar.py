"""
TaxIQ — Investment Calendar
Month-by-month investment plan to fill 80C/80D gaps before March 31.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from backend.tax_engine.sections import TAX_SECTIONS


# Instruments mapped to sections with monthly suitability
SECTION_INSTRUMENTS = {
    "80C": [
        {"instrument": "ELSS SIP (Axis Long Term Equity)", "type": "SIP", "min": 500, "lock_in": "3 years"},
        {"instrument": "PPF Contribution", "type": "lump_sum", "min": 500, "lock_in": "15 years"},
        {"instrument": "LIC Premium Payment", "type": "annual", "min": 1000, "lock_in": "varies"},
        {"instrument": "NSC (National Savings Certificate)", "type": "lump_sum", "min": 1000, "lock_in": "5 years"},
        {"instrument": "Sukanya Samriddhi Yojana", "type": "annual", "min": 250, "lock_in": "21 years"},
    ],
    "80D": [
        {"instrument": "Health Insurance Premium (Star Health)", "type": "annual", "min": 5000, "lock_in": "1 year"},
        {"instrument": "Super Top-Up Health Cover (Max Bupa)", "type": "annual", "min": 3000, "lock_in": "1 year"},
        {"instrument": "Preventive Health Check-Up", "type": "annual", "min": 5000, "lock_in": "none"},
    ],
    "80CCD1B": [
        {"instrument": "NPS Tier-I Contribution", "type": "SIP", "min": 500, "lock_in": "till 60"},
        {"instrument": "Atal Pension Yojana", "type": "SIP", "min": 42, "lock_in": "till 60"},
    ],
    "24B": [
        {"instrument": "Home Loan Interest Payment", "type": "EMI", "min": 0, "lock_in": "loan tenure"},
    ],
}

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class InvestmentCalendar:
    """
    Generates a month-by-month investment plan to fill 80C/80D gaps
    before March 31 — spread evenly across remaining months.
    """

    ESTIMATED_TAX_RATE = 0.312  # 30% slab + 4% cess

    def generate(
        self,
        gap_report: dict,
        current_month: int = 0,
        current_year: int = 0,
    ) -> Dict[str, Any]:
        """
        Build a monthly investment calendar from the gap report.

        Args:
            gap_report: Output of gap_analyzer.analyze_gaps()
            current_month: 1-12, defaults to today
            current_year: 4-digit year, defaults to today
        """
        today = date.today()
        if not current_month:
            current_month = today.month
        if not current_year:
            current_year = today.year

        # Calculate FY end (March 31)
        if current_month <= 3:
            fy_end = date(current_year, 3, 31)
        else:
            fy_end = date(current_year + 1, 3, 31)

        # Remaining months (including current)
        months_remaining = max(1, self._months_between(
            date(current_year, current_month, 1), fy_end
        ))

        sections = gap_report.get("sections", {})
        monthly_plan: List[Dict[str, Any]] = []
        total_to_invest = 0.0
        total_tax_saved = 0.0

        # Build per-section allocations
        section_gaps: List[Dict] = []
        for sec, data in sections.items():
            gap = float(data.get("gap", 0))
            if gap <= 0:
                continue
            section_gaps.append({"section": sec, "gap": gap, "urgency": data.get("urgency_level", "medium")})

        # Distribute across months
        for month_offset in range(months_remaining):
            m = current_month + month_offset
            y = current_year
            while m > 12:
                m -= 12
                y += 1
            month_label = f"{MONTH_NAMES[m - 1]} {y}"
            due_date = date(y, m, 28 if m != 2 else 28)

            investments: List[Dict[str, Any]] = []
            month_total = 0.0

            for sg in section_gaps:
                sec = sg["section"]
                gap = sg["gap"]
                if gap <= 0:
                    continue

                # Split evenly across remaining months from this point
                remaining = max(1, months_remaining - month_offset)
                amount_this_month = round(gap / months_remaining, 0)

                instruments = SECTION_INSTRUMENTS.get(sec, [])
                if not instruments:
                    continue

                # Pick instrument based on month (rotate for variety)
                inst = instruments[month_offset % len(instruments)]

                priority = "HIGH" if sg["urgency"] == "high" else (
                    "MEDIUM" if sg["urgency"] == "medium" else "LOW"
                )
                # Higher priority near March
                if month_offset >= months_remaining - 2:
                    priority = "HIGH"

                investments.append({
                    "section": sec,
                    "instrument": inst["instrument"],
                    "amount": amount_this_month,
                    "due_date": due_date.isoformat(),
                    "priority": priority,
                    "lock_in": inst.get("lock_in", "varies"),
                    "type": inst.get("type", "lump_sum"),
                })
                month_total += amount_this_month

            if investments:
                monthly_plan.append({
                    "month": month_label,
                    "month_number": m,
                    "year": y,
                    "investments": investments,
                    "total_this_month": month_total,
                })
                total_to_invest += month_total

        total_tax_saved = round(total_to_invest * self.ESTIMATED_TAX_RATE, 2)

        return {
            "months_remaining": months_remaining,
            "fy_end": fy_end.isoformat(),
            "monthly_plan": monthly_plan,
            "summary": {
                "total_to_invest": total_to_invest,
                "total_tax_saved": total_tax_saved,
                "monthly_average": round(total_to_invest / months_remaining, 0) if months_remaining else 0,
            },
        }

    @staticmethod
    def _months_between(d1: date, d2: date) -> int:
        """Count months between two dates (inclusive of partial months)."""
        return (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1
