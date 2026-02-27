from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from backend.graph.graph_builder import graph_store
from backend.graph.neo4j_client import get_neo4j_client


def _data_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "mock_gstn" / "fraud_network.json"


async def load_mock_fraud_data() -> Dict[str, Any]:
    """
    Loads a realistic mock fraud network:
    - 20 legitimate GSTINs
    - 1 circular ring of 5 GSTINs (A->B->C->D->E->A)
    - 2 star fraud patterns
    into Neo4j if available, else into networkx.
    """
    payload = json.loads(_data_path().read_text(encoding="utf-8"))

    gstins = payload["gstins"]
    edges = payload["itc_edges"]

    if await graph_store.neo4j_available():
        # constraints
        await get_neo4j_client().run_query("CREATE CONSTRAINT gstin_unique IF NOT EXISTS FOR (g:GSTIN) REQUIRE g.gstin IS UNIQUE")
        for g in gstins:
            await get_neo4j_client().run_query(
                "MERGE (x:GSTIN {gstin:$gstin}) SET x.name=$name, x.state=$state, x.type=$type, x.risk_score=coalesce(x.risk_score,0.1)",
                g,
            )
        for e in edges:
            await get_neo4j_client().run_query(
                "MATCH (a:GSTIN {gstin:$from}), (b:GSTIN {gstin:$to}) MERGE (a)-[r:CLAIMED_ITC_FROM]->(b) SET r.value=$value",
                e,
            )
        logger.info("Loaded mock fraud network into Neo4j nodes={} edges={}", len(gstins), len(edges))
        return {"loaded": True, "backend": "neo4j", "nodes": len(gstins), "edges": len(edges)}

    # networkx
    for g in gstins:
        await graph_store.create_gstin_node(gstin=g["gstin"], name=g["name"], state=g["state"], type=g["type"])
    for e in edges:
        graph_store.nx_graph.add_edge(e["from"], e["to"], type="CLAIMED_ITC_FROM", value=float(e["value"]))
    logger.info("Loaded mock fraud network into networkx nodes={} edges={}", len(gstins), len(edges))
    return {"loaded": True, "backend": "networkx", "nodes": len(gstins), "edges": len(edges)}

