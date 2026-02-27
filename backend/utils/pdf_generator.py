from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fpdf import FPDF


class TaxReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "TaxIQ — Personal Tax Report", ln=1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1)
        self.ln(4)
        self.set_text_color(0, 0, 0)


def generate_tax_report_pdf(output_path: str, analysis: Dict[str, Any]) -> str:
    """
    Create a readable PDF report summarizing:
    - Regime comparison
    - Gap report (80C/80D/80CCD1B/24B)
    - Action items
    - AI advice
    """
    pdf = TaxReportPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    profile = analysis.get("profile", {})
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Profile", ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, f"Name: {profile.get('name','User')}\nIncome: ₹{profile.get('annual_income')}\nAge: {profile.get('age')}")
    pdf.ln(2)

    rc = analysis.get("regime_comparison", {})
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Regime Comparison (FY2024-25)", ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        6,
        f"Old Regime Tax: ₹{round(rc.get('old_regime_tax',0),2)}\n"
        f"New Regime Tax: ₹{round(rc.get('new_regime_tax',0),2)}\n"
        f"Best: {rc.get('best_regime','-')} (saves ₹{round(rc.get('savings',0),2)})",
    )
    pdf.ln(2)

    gaps = analysis.get("gap_report", {}).get("sections", {})
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Investment Gaps", ln=1)
    pdf.set_font("Helvetica", "", 10)
    for sec, row in gaps.items():
        pdf.multi_cell(
            0,
            6,
            f"{sec}: invested ₹{row.get('current_investment')} / limit {row.get('limit')} → gap ₹{row.get('gap')} "
            f"(urgency: {row.get('urgency_level')}, potential saving ₹{row.get('potential_tax_saving')})",
        )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Action Items", ln=1)
    pdf.set_font("Helvetica", "", 10)
    for item in analysis.get("action_items", []):
        pdf.multi_cell(
            0,
            6,
            f"- {item['section']}: invest ₹{round(item['gap'],2)} in {item['suggested_investment']} before {item['deadline']} "
            f"(save ~₹{round(item['potential_tax_saving'],2)})",
        )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "AI Advice", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, analysis.get("ai_advice", ""))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    return output_path

