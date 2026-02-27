from datetime import datetime
from typing import Any, Dict, List


class NexusScorer:
    WEIGHTS = {
        "filing_rate": 0.30,
        "gstr2b_reflectance": 0.25,
        "itc_accuracy": 0.20,
        "network_risk": 0.15,
        "eway_compliance": 0.10,
    }

    async def calculate_score(self, gstin: str) -> Dict[str, Any]:
        # Deterministic demo scores for the story.
        if gstin == "19AABCG1234Q1Z2":
            return self._score(
                gstin=gstin,
                nexusScore=18,
                filingRate=42,
                gstr2bReflectance=31,
                itcAccuracy=25,
                networkRisk=22,
                ewayCompliance=44,
                trend="DOWN",
            )
        if gstin == "27AAACF9999K1Z9":
            return self._score(
                gstin=gstin,
                nexusScore=52,
                filingRate=86,
                gstr2bReflectance=74,
                itcAccuracy=63,
                networkRisk=55,
                ewayCompliance=68,
                trend="FLAT",
            )
        if gstin == "07AABCS7777H1Z1":
            return self._score(
                gstin=gstin,
                nexusScore=33,
                filingRate=55,
                gstr2bReflectance=48,
                itcAccuracy=41,
                networkRisk=38,
                ewayCompliance=52,
                trend="DOWN",
            )
        return self._score(
            gstin=gstin,
            nexusScore=87,
            filingRate=96,
            gstr2bReflectance=94,
            itcAccuracy=91,
            networkRisk=82,
            ewayCompliance=88,
            trend="UP",
        )

    def _grade(self, score: int) -> str:
        if score >= 90:
            return "AAA"
        if score >= 85:
            return "AA+"
        if score >= 80:
            return "AA"
        if score >= 75:
            return "A+"
        if score >= 70:
            return "A"
        if score >= 60:
            return "BBB"
        if score >= 50:
            return "BB"
        if score >= 40:
            return "B"
        if score >= 30:
            return "CCC"
        return "D"

    def _score(
        self,
        gstin: str,
        nexusScore: int,
        filingRate: int,
        gstr2bReflectance: int,
        itcAccuracy: int,
        networkRisk: int,
        ewayCompliance: int,
        trend: str,
    ) -> Dict[str, Any]:
        loan_eligible = nexusScore >= 75 and filingRate >= 90
        loan_limit = int(nexusScore * 65000 * 0.5) if loan_eligible else 0
        return {
            "gstin": gstin,
            "nexusScore": nexusScore,
            "grade": self._grade(nexusScore),
            "filingRate": filingRate,
            "gstr2bReflectance": gstr2bReflectance,
            "itcAccuracy": itcAccuracy,
            "networkRisk": networkRisk,
            "ewayCompliance": ewayCompliance,
            "trend": trend,
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "loanEligible": loan_eligible,
            "loanLimit": loan_limit,
            "creditRating": self._grade(nexusScore),
            "loanOfferApr": 13.5 if loan_eligible else None,
            "loanTenorMonths": 12 if loan_eligible else None,
        }
