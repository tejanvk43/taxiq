from __future__ import annotations

from typing import Any, Dict, List, Tuple

import networkx as nx
from loguru import logger

from backend.graph.graph_builder import graph_store
from backend.graph.neo4j_client import get_neo4j_client


async def detect_circular_chains() -> List[Dict[str, Any]]:
    """
    Cypher:
      MATCH path=(a:GSTIN)-[:CLAIMED_ITC_FROM*3..8]->(a)
      RETURN path, length(path) as chain_length
      ORDER BY chain_length DESC LIMIT 20
    networkx fallback: find simple cycles length 3..8 on CLAIMED_ITC_FROM edges.
    """
    if await graph_store.neo4j_available():
        q = """
        MATCH path=(a:GSTIN)-[:CLAIMED_ITC_FROM*3..8]->(a)
        RETURN [n in nodes(path) | n.gstin] as gstins, length(path) as chain_length
        ORDER BY chain_length DESC
        LIMIT 20
        """
        rows = await get_neo4j_client().run_query(q)
        return [{"gstins": r["gstins"], "chain_length": int(r["chain_length"])} for r in rows]

    g = graph_store.nx_graph
    # subgraph of CLAIMED_ITC_FROM edges only
    h = nx.DiGraph([(u, v) for u, v, a in g.edges(data=True) if a.get("type") == "CLAIMED_ITC_FROM"])
    cycles = []
    for cyc in nx.simple_cycles(h):
        if 3 <= len(cyc) <= 8:
            cycles.append({"gstins": cyc + [cyc[0]], "chain_length": len(cyc)})
    cycles.sort(key=lambda x: x["chain_length"], reverse=True)
    return cycles[:20]


async def calculate_risk_scores() -> None:
    """
    Score each GSTIN 0-1 based on:
      - ITC claim volume (out-degree on CLAIMED_ITC_FROM)
      - Presence in cycles
      - Newer GSTIN heuristic (not stored; simulated)
    Updates risk_score property on GSTIN nodes.
    """
    cycles = await detect_circular_chains()
    cycle_nodes = set()
    for c in cycles:
        for g in c["gstins"]:
            cycle_nodes.add(g)

    if await graph_store.neo4j_available():
        # Approx risk in Neo4j using degree + cycle membership.
        q = """
        MATCH (g:GSTIN)
        OPTIONAL MATCH (g)-[r:CLAIMED_ITC_FROM]->()
        WITH g, count(r) as outClaims
        SET g.risk_score = toFloat( CASE
          WHEN outClaims >= 5 THEN 0.8
          WHEN outClaims >= 2 THEN 0.5
          ELSE 0.2
        END )
        RETURN count(g) as updated
        """
        await get_neo4j_client().run_query(q)
        # boost for cycle members
        if cycle_nodes:
            await get_neo4j_client().run_query(
                "MATCH (g:GSTIN) WHERE g.gstin IN $gstins SET g.risk_score = CASE WHEN g.risk_score < 0.85 THEN 0.9 ELSE g.risk_score END",
                {"gstins": list(cycle_nodes)},
            )
        return

    g = graph_store.nx_graph
    # compute out degree on CLAIMED_ITC_FROM
    for node, attrs in list(g.nodes(data=True)):
        if attrs.get("label") != "GSTIN":
            continue
        out_claims = 0
        total_val = 0.0
        for _, v, a in g.out_edges(node, data=True):
            if a.get("type") == "CLAIMED_ITC_FROM":
                out_claims += 1
                total_val += float(a.get("value", 0.0))
        risk = 0.2
        if out_claims >= 5 or total_val > 500000:
            risk = 0.8
        elif out_claims >= 2 or total_val > 150000:
            risk = 0.5
        if node in cycle_nodes:
            risk = max(risk, 0.9)
        g.nodes[node]["risk_score"] = float(risk)


async def get_risk_summary() -> Dict[str, Any]:
    if await graph_store.neo4j_available():
        q = """
        MATCH (g:GSTIN)
        WITH g,
        CASE
          WHEN g.risk_score > 0.7 THEN 'high'
          WHEN g.risk_score > 0.4 THEN 'medium'
          ELSE 'low'
        END as bucket
        RETURN bucket, count(*) as c
        """
        rows = await get_neo4j_client().run_query(q)
        buckets = {r["bucket"]: int(r["c"]) for r in rows}
        top = await get_neo4j_client().run_query("MATCH (g:GSTIN) RETURN g.gstin as gstin, g.name as name, g.risk_score as risk ORDER BY risk DESC LIMIT 10")
        return {
            "high_risk": buckets.get("high", 0),
            "medium_risk": buckets.get("medium", 0),
            "low_risk": buckets.get("low", 0),
            "top10": [{"gstin": r["gstin"], "name": r.get("name"), "risk_score": float(r.get("risk") or 0)} for r in top],
            "backend": "neo4j",
        }

    g = graph_store.nx_graph
    vals: List[Tuple[str, float]] = []
    for n, a in g.nodes(data=True):
        if a.get("label") == "GSTIN":
            vals.append((n, float(a.get("risk_score", 0.1))))
    high = sum(1 for _, r in vals if r > 0.7)
    med = sum(1 for _, r in vals if 0.4 < r <= 0.7)
    low = sum(1 for _, r in vals if r <= 0.4)
    vals.sort(key=lambda x: x[1], reverse=True)
    return {
        "high_risk": high,
        "medium_risk": med,
        "low_risk": low,
        "top10": [{"gstin": g, "name": g, "risk_score": r} for g, r in vals[:10]],
        "backend": "networkx",
    }

