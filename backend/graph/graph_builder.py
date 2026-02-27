from __future__ import annotations

from typing import Any, Dict, Optional

import networkx as nx
from loguru import logger

from backend.graph.neo4j_client import get_neo4j_client


class GraphStore:
    """
    Dual-mode store:
    - Neo4j if available
    - networkx fallback otherwise
    """

    def __init__(self) -> None:
        self.nx_graph = nx.DiGraph()

    async def neo4j_available(self) -> bool:
        try:
            client = get_neo4j_client()
            await client.run_query("RETURN 1 as ok")
            return True
        except Exception:
            return False

    async def create_gstin_node(self, gstin: str, name: str, state: str, type: str) -> None:
        if await self.neo4j_available():
            q = """
            MERGE (g:GSTIN {gstin:$gstin})
            SET g.name=$name, g.state=$state, g.type=$type
            RETURN g
            """
            await get_neo4j_client().run_query(q, {"gstin": gstin, "name": name, "state": state, "type": type})
            return

        self.nx_graph.add_node(gstin, label="GSTIN", gstin=gstin, name=name, state=state, type=type, risk_score=0.1)

    async def create_invoice_node(self, invoice_id: str, date: str, value: float, tax: float) -> None:
        if await self.neo4j_available():
            q = """
            MERGE (i:Invoice {invoice_id:$invoice_id})
            SET i.date=$date, i.value=$value, i.tax=$tax
            RETURN i
            """
            await get_neo4j_client().run_query(q, {"invoice_id": invoice_id, "date": date, "value": value, "tax": tax})
            return

        self.nx_graph.add_node(invoice_id, label="Invoice", invoice_id=invoice_id, date=date, value=value, tax=tax)

    async def link_supplier_buyer(self, supplier_gstin: str, buyer_gstin: str, invoice_id: str, itc_value: Optional[float] = None) -> None:
        if await self.neo4j_available():
            q = """
            MATCH (s:GSTIN {gstin:$s}), (b:GSTIN {gstin:$b}), (i:Invoice {invoice_id:$inv})
            MERGE (s)-[:ISSUED]->(i)
            MERGE (i)-[:RECEIVED_BY]->(b)
            MERGE (b)-[r:CLAIMED_ITC_FROM]->(s)
            SET r.value = coalesce(r.value, 0) + $itc
            RETURN r
            """
            await get_neo4j_client().run_query(
                q, {"s": supplier_gstin, "b": buyer_gstin, "inv": invoice_id, "itc": float(itc_value or 0.0)}
            )
            return

        self.nx_graph.add_edge(supplier_gstin, invoice_id, type="ISSUED")
        self.nx_graph.add_edge(invoice_id, buyer_gstin, type="RECEIVED_BY")
        self.nx_graph.add_edge(buyer_gstin, supplier_gstin, type="CLAIMED_ITC_FROM", value=float(itc_value or 0.0))

    async def export_pyvis_data(self) -> Dict[str, Any]:
        """
        Return {nodes, edges} for pyvis rendering.
        """
        if await self.neo4j_available():
            qn = "MATCH (n) RETURN labels(n) as labels, n as n LIMIT 500"
            qe = "MATCH (a)-[r]->(b) RETURN a.gstin as a, type(r) as t, b.gstin as b, r.value as v LIMIT 800"
            nodes_raw = await get_neo4j_client().run_query(qn)
            edges_raw = await get_neo4j_client().run_query(qe)
            nodes = []
            for row in nodes_raw:
                n = row["n"]
                labels = row["labels"]
                if "GSTIN" in labels:
                    nodes.append({"id": n.get("gstin"), "label": n.get("name", n.get("gstin")), "risk_score": float(n.get("risk_score", 0.1))})
                elif "Invoice" in labels:
                    nodes.append({"id": n.get("invoice_id"), "label": n.get("invoice_id"), "risk_score": 0.0})
            edges = [{"from": e["a"], "to": e["b"], "type": e["t"], "value": float(e.get("v") or 0.0)} for e in edges_raw if e.get("a") and e.get("b")]
            return {"nodes": nodes, "edges": edges, "backend": "neo4j"}

        nodes = []
        for nid, attrs in self.nx_graph.nodes(data=True):
            if attrs.get("label") == "GSTIN":
                nodes.append({"id": nid, "label": attrs.get("name", nid), "risk_score": float(attrs.get("risk_score", 0.1))})
            else:
                nodes.append({"id": nid, "label": str(nid), "risk_score": float(attrs.get("risk_score", 0.0))})
        edges = []
        for u, v, attrs in self.nx_graph.edges(data=True):
            if attrs.get("type") == "CLAIMED_ITC_FROM":
                edges.append({"from": u, "to": v, "type": attrs.get("type"), "value": float(attrs.get("value", 0.0))})
            else:
                edges.append({"from": u, "to": v, "type": attrs.get("type", "EDGE"), "value": float(attrs.get("value", 0.0))})
        return {"nodes": nodes, "edges": edges, "backend": "networkx"}


graph_store = GraphStore()

