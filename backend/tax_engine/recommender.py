from __future__ import annotations

from typing import Dict, List

from backend.tax_engine.sections import TAX_SECTIONS


def generate_recommendations(gap_report: Dict) -> List[Dict]:
    """
    Convert gap report into action items sorted by potential_tax_saving.
    """
    items: List[Dict] = []
    sections = gap_report.get("sections", {})
    months = gap_report.get("monthsRemaining", 0)

    for sec, row in sections.items():
        gap = float(row.get("gap", 0))
        if gap <= 0:
            continue
        instruments = TAX_SECTIONS.get(sec, {}).get("instruments", [])
        suggestion = instruments[0] if instruments else "Eligible investment"
        items.append(
            {
                "section": sec,
                "gap": gap,
                "suggested_investment": suggestion,
                "deadline": f"March 31 (in ~{months} months)" if months else "March 31",
                "potential_tax_saving": float(row.get("potential_tax_saving", 0)),
            }
        )

    items.sort(key=lambda x: x["potential_tax_saving"], reverse=True)
    return items

