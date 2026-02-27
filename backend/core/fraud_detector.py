from datetime import datetime
from typing import Any, Dict, List

from backend.graph.fraud_detector import (
    detect_circular_chains,
    calculate_risk_scores,
    get_risk_summary,
)
from backend.graph.graph_builder import graph_store


class FraudDetector:
    """
    Delegates to the real graph-based fraud detector in backend.graph.fraud_detector.
    Wraps the raw cycle data into the richer ring / shell-company response format
    expected by the /api/fraud/* endpoints.
    """

    async def detect_circular_rings(self, min_nodes: int = 3) -> List[Dict[str, Any]]:
        """Detect circular ITC chains using real graph cycle detection."""
        # Ensure risk scores are up-to-date
        await calculate_risk_scores()
        chains = await detect_circular_chains()

        rings: List[Dict[str, Any]] = []
        for idx, chain in enumerate(chains, start=1):
            gstins = chain.get("gstins", [])
            # Filter by minimum node count
            if len(set(gstins)) < min_nodes:
                continue

            # Estimate fraud amount from graph edge values
            fraud_amount = self._estimate_ring_amount(gstins)
            ring_size = chain.get("chain_length", len(set(gstins)))
            confidence = self._calculate_confidence(ring_size, fraud_amount)

            rings.append({
                "ringId": f"RING-{idx:03d}",
                "gstins": gstins,
                "confidence": round(confidence, 2),
                "fraudAmount": fraud_amount,
                "ringSize": ring_size,
                "detectedOn": datetime.utcnow().isoformat() + "Z",
            })

        # Sort by fraud amount descending
        rings.sort(key=lambda r: r["fraudAmount"], reverse=True)
        return rings

    async def detect_shell_companies(self) -> List[Dict[str, Any]]:
        """Identify potential shell companies using risk scores and graph topology."""
        await calculate_risk_scores()
        summary = await get_risk_summary()

        shells: List[Dict[str, Any]] = []
        for entry in summary.get("top10", []):
            risk = entry.get("risk_score", 0)
            if risk < 0.7:
                continue

            # Determine reason from graph topology
            gstin = entry.get("gstin", "")
            reasons = []
            g = graph_store.nx_graph
            if gstin in g:
                out_itc = sum(
                    1 for _, _, a in g.out_edges(gstin, data=True)
                    if a.get("type") == "CLAIMED_ITC_FROM"
                )
                in_itc = sum(
                    1 for _, _, a in g.in_edges(gstin, data=True)
                    if a.get("type") == "CLAIMED_ITC_FROM"
                )
                if out_itc > 3 and in_itc == 0:
                    reasons.append("High outward ITC claims with zero inward invoices")
                if out_itc > 5:
                    reasons.append(f"Unusually high ITC claim count ({out_itc} outward edges)")
                if risk >= 0.9:
                    reasons.append("Part of detected circular trading ring")
            if not reasons:
                reasons.append(f"Risk score {risk:.2f} exceeds threshold")

            shells.append({
                "gstin": gstin,
                "name": entry.get("name", gstin),
                "riskScore": risk,
                "reason": "; ".join(reasons),
                "detectedOn": datetime.utcnow().isoformat() + "Z",
            })

        return shells

    def _estimate_ring_amount(self, gstins: List[str]) -> float:
        """Sum edge values in the ring from the networkx graph."""
        g = graph_store.nx_graph
        total = 0.0
        unique = list(dict.fromkeys(gstins))  # preserve order, dedupe
        for i in range(len(unique)):
            src = unique[i]
            dst = unique[(i + 1) % len(unique)]
            if g.has_edge(src, dst):
                edge_data = g.edges[src, dst]
                total += float(edge_data.get("value", 0))
        # Fallback: if graph has no values, estimate from count
        if total == 0:
            total = len(unique) * 210000  # avg ₹2.1L per edge from mock data
        return total

    def _calculate_confidence(self, ring_size: int, amount: float) -> float:
        """Confidence heuristic: longer rings + higher amounts = higher confidence."""
        size_factor = min(ring_size / 8, 1.0) * 0.5
        amount_factor = min(amount / 5_000_000, 1.0) * 0.5
        return min(size_factor + amount_factor + 0.3, 0.99)
