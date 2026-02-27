from __future__ import annotations

from typing import Any, Dict

from backend.graph.fraud_detector import calculate_risk_scores, detect_circular_chains, get_risk_summary
from backend.graph.graph_builder import graph_store


class FraudAgent:
    async def run_detection(self) -> Dict[str, Any]:
        chains = await detect_circular_chains()
        await calculate_risk_scores()
        summary = await get_risk_summary()
        flagged = [x for x in summary.get("top10", []) if float(x.get("risk_score", 0)) > 0.4]
        return {"chains_found": chains, "risk_summary": summary, "flagged_gstins": flagged}

    async def get_graph_visualization_data(self) -> Dict[str, Any]:
        data = await graph_store.export_pyvis_data()
        # color coding hints for frontend
        for n in data.get("nodes", []):
            r = float(n.get("risk_score", 0.0))
            n["color"] = "red" if r > 0.7 else "orange" if r > 0.4 else "green"
        for e in data.get("edges", []):
            v = float(e.get("value", 0.0))
            e["width"] = 1 + min(8, v / 50000.0)
        return data

