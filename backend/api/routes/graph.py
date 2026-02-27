import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from backend.core.graph_engine import GraphEngine

router = APIRouter(prefix="/api/graph", tags=["graph"])


def get_engine() -> GraphEngine:
    return GraphEngine()


@router.get("/traverse/{gstin}")
async def traverse_invoice_chain(
    gstin: str,
    depth: int = Query(default=3, le=6),
    period: str = Query(default="2024-01"),
    engine: GraphEngine = Depends(get_engine),
):
    mock = os.getenv("MOCK_GSTN", "true").lower() == "true"
    _ = depth
    if mock:
        # Minimal path-like payload for the frontend to render.
        nodes = [
            {"id": gstin, "label": "Taxpayer", "name": "Nexus Demo Manufacturing", "nexusScore": 86},
            {"id": "INV-2024-001", "label": "Invoice", "amount": 8420000, "status": "MISMATCH"},
            {"id": "GSTR1-2024-01", "label": "GSTR1", "period": period, "status": "FAIL"},
            {"id": "GSTR2B-2024-01", "label": "GSTR2B", "period": period, "status": "FAIL"},
            {"id": "EWB-DEMO-9001", "label": "EWayBill", "status": "SKIP"},
            {"id": "GSTR3B-2024-01", "label": "GSTR3B", "period": period, "status": "WARN"},
        ]
        links = [
            {"source": gstin, "target": "INV-2024-001", "type": "RECEIVED"},
            {"source": "19AABCG1234Q1Z2", "target": "INV-2024-001", "type": "ISSUED"},
            {"source": "INV-2024-001", "target": "GSTR1-2024-01", "type": "FILED_IN"},
            {"source": "INV-2024-001", "target": "GSTR2B-2024-01", "type": "REFLECTED_IN"},
            {"source": "INV-2024-001", "target": "EWB-DEMO-9001", "type": "VALIDATED_BY"},
            {"source": gstin, "target": "GSTR3B-2024-01", "type": "FILED"},
        ]
        return {"gstin": gstin, "period": period, "nodes": nodes, "links": links}

    query = """
    MATCH path = (t:Taxpayer {gstin: $gstin})-[:ISSUED]->(inv:Invoice)-[:FILED_IN]->(g1:GSTR1)
    OPTIONAL MATCH (inv)-[:REFLECTED_IN]->(g2b:GSTR2B)
    OPTIONAL MATCH (inv)-[:VALIDATED_BY]->(ewb:EWayBill)
    OPTIONAL MATCH (t)-[:FILED]->(g3b:GSTR3B {period: $period})
    WHERE inv.date STARTS WITH $period
    RETURN path, g2b, ewb, g3b
    ORDER BY inv.date DESC
    LIMIT 50
    """
    rows = await engine.run_cypher(query, {"gstin": gstin, "period": period})
    return {"gstin": gstin, "period": period, "rows": rows}


@router.get("/fraud-rings")
async def get_fraud_rings(min_confidence: float = Query(default=0.6), min_amount: float = Query(default=100000)):
    return {"minConfidence": min_confidence, "minAmount": min_amount, "rings": [{"ringId": "RING-001"}]}


@router.get("/network/{gstin}")
async def get_gstin_network(gstin: str, hops: int = 2):
    _ = hops
    nodes = [
        {"id": gstin, "kind": "Taxpayer", "name": "Nexus Demo Manufacturing", "nexusScore": 86},
        {"id": "19AABCG1234Q1Z2", "kind": "Taxpayer", "name": "GoldStar Traders", "nexusScore": 18},
        {"id": "27AAACF9999K1Z9", "kind": "Taxpayer", "name": "Falcon Components", "nexusScore": 52},
        {"id": "07AABCS7777H1Z1", "kind": "Taxpayer", "name": "Shadow Supplies", "nexusScore": 33},
        {"id": "INV-2024-001", "kind": "Invoice", "amount": 8420000, "status": "MISMATCH"},
    ]
    links = [
        {"source": "19AABCG1234Q1Z2", "target": "INV-2024-001", "type": "ISSUED"},
        {"source": gstin, "target": "INV-2024-001", "type": "RECEIVED"},
        {"source": "19AABCG1234Q1Z2", "target": "27AAACF9999K1Z9", "type": "RISKY_COUNTERPARTY"},
        {"source": "27AAACF9999K1Z9", "target": "07AABCS7777H1Z1", "type": "RISKY_COUNTERPARTY"},
        {"source": "07AABCS7777H1Z1", "target": "19AABCG1234Q1Z2", "type": "RISKY_COUNTERPARTY"},
    ]
    return {"nodes": nodes, "links": links}


@router.post("/shortest-path")
async def find_shortest_path(source_gstin: str, target_gstin: str) -> Dict[str, Any]:
    return {
        "source": source_gstin,
        "target": target_gstin,
        "path": [source_gstin, "27AAACF9999K1Z9", target_gstin],
        "length": 2,
    }
