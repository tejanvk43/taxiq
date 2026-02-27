from __future__ import annotations

from typing import Any, Dict

import pandas as pd
from loguru import logger

from backend.models.tax_profile import TaxProfile
from backend.pipelines.csv_parser import parse_bank_statement
from backend.tax_engine.gap_analyzer import analyze_gaps
from backend.tax_engine.recommender import generate_recommendations
from backend.tax_engine.regime_comparator import calculate_new_regime_tax, calculate_old_regime_tax
from backend.utils.llm_client import LLMClient
from backend.utils.vernacular import to_hindi


class TaxSaverAgent:
    def analyze(self, csv_path: str, annual_income: float, age: int, has_senior_parents: bool, name: str = "User") -> Dict[str, Any]:
        profile = TaxProfile(name=name, annual_income=annual_income, age=age, has_senior_parents=has_senior_parents)
        df = parse_bank_statement(csv_path)

        # Total deductions approximation from deductible transactions
        deductible_sum = float(df[df["is_deductible"] == True]["amount"].sum())  # noqa: E712
        gap_report = analyze_gaps(df=df, annual_income=annual_income, age=age, has_senior_parents=has_senior_parents)

        old_tax = calculate_old_regime_tax(income=annual_income, deductions=deductible_sum)
        new_tax = calculate_new_regime_tax(income=annual_income)
        savings = abs(old_tax - new_tax)
        best = "OLD" if old_tax < new_tax else "NEW"

        action_items = generate_recommendations(gap_report)

        ai_advice = self._ai_advice(profile=profile, gap_report=gap_report, best_regime=best, savings=savings)
        summary_stats = {
            "transactions": int(len(df)),
            "deductible_spend": deductible_sum,
            "best_regime": best,
            "estimated_savings": savings,
        }

        return {
            "profile": profile.model_dump(),
            "gap_report": gap_report,
            "regime_comparison": {"old_regime_tax": old_tax, "new_regime_tax": new_tax, "best_regime": best, "savings": savings},
            "ai_advice": ai_advice,
            "action_items": action_items,
            "summary_stats": summary_stats,
            "df_preview": df.head(30).to_dict(orient="records"),
        }

    def _ai_advice(self, profile: TaxProfile, gap_report: Dict[str, Any], best_regime: str, savings: float) -> str:
        # Build a compact narrative prompt
        sec80c = gap_report["sections"]["80C"]
        sec80d = gap_report["sections"]["80D"]
        secnps = gap_report["sections"]["80CCD1B"]
        months = gap_report.get("monthsRemaining", 0)

        prompt = (
            f"Given that {profile.name} earns ₹{int(profile.annual_income)} and has invested ₹{int(sec80c['current_investment'])} in 80C so far, "
            f"with ₹{int(sec80c['gap'])} gap remaining and only {months} months till March 31, provide specific, actionable investment advice. "
            "Include exact amounts, specific fund names (e.g., 'Axis ELSS'), and calculate exact tax saved. "
            "Be conversational, not robotic. End with a single motivating sentence in Hindi."
        )

        llm = LLMClient()
        try:
            out = llm.ask(prompt)
            # If DEMO mode returns JSON, turn it into readable advice.
            if out.strip().startswith("{"):
                return (
                    "[DEMO DATA] Suggested plan:\n"
                    f"- Top up 80C by ₹{int(sec80c['gap'])}: Axis ELSS / PPF.\n"
                    f"- Add 80D health cover top-up by ₹{int(sec80d['gap'])} (Max Bupa / Star Health).\n"
                    f"- Consider NPS 80CCD(1B) up to ₹{int(secnps['gap'])} for extra ₹50k deduction.\n"
                    f"- Expected tax saving (approx): ₹{int(sum(x['potential_tax_saving'] for x in gap_report['sections'].values() if isinstance(x.get('limit'), (int,float))))}.\n\n"
                    f"{to_hindi('Every rupee invested now saves tax later.')}"
                )
            # Ensure Hindi ending sentence exists
            if not any(ch in out for ch in ["।", "है", "कर", "आप"]):
                out = out.strip() + "\n\n" + to_hindi("You can do this.")
            return out
        except Exception as e:
            logger.warning("AI advice generation failed; using deterministic advice. err={}", str(e))
            return (
                "[DEMO DATA] Suggested plan:\n"
                f"- Choose {best_regime} regime (estimated savings ₹{int(savings)}).\n"
                f"- Fill 80C gap ₹{int(sec80c['gap'])}: Axis ELSS / PPF.\n"
                f"- Fill 80D gap ₹{int(sec80d['gap'])}: Health insurance.\n"
                f"- Fill NPS 80CCD(1B) gap ₹{int(secnps['gap'])}: NPS Tier I.\n\n"
                f"{to_hindi('Start today.')}"
            )

