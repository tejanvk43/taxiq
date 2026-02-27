import os

import httpx
import streamlit as st
from pyvis.network import Network


BACKEND_URL = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")

st.markdown(
    """
<style>
section.main { background-color: #0A1628; }
.taxiq-badge {
  display:inline-block; padding:2px 8px; border-radius:999px;
  border:1px solid rgba(255,153,51,.55);
  background: rgba(255,153,51,.10);
  color: #FF9933; font-size: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)


st.markdown("## 🕸️ ITC Fraud Detection Agent")
st.caption("Knowledge Graph → circular chain detection → risk scoring")


def api_post(path: str):
    with httpx.Client(timeout=90) as client:
        return client.post(f"{BACKEND_URL}{path}")


def api_get(path: str):
    with httpx.Client(timeout=90) as client:
        return client.get(f"{BACKEND_URL}{path}")


top = st.columns(4)
with top[0]:
    load_btn = st.button("Load Sample Fraud Data", use_container_width=True, type="primary")
with top[1]:
    run_btn = st.button("Run Detection", use_container_width=True)
with top[2]:
    refresh_btn = st.button("Refresh Graph", use_container_width=True)
with top[3]:
    st.caption(f"Backend: `{BACKEND_URL}`")


if load_btn:
    with st.spinner("Loading sample fraud network into graph…"):
        r = api_post("/fraud/load-mock")
        if r.status_code == 200:
            st.success("Loaded sample fraud network.")
        else:
            st.error(r.text)


if run_btn:
    with st.spinner("Detecting circular chains + computing risk scores…"):
        r = api_post("/fraud/run")
        if r.status_code == 200:
            st.session_state["fraud_result"] = r.json()
            st.session_state["kpi_frauds"] = len(st.session_state["fraud_result"].get("chains_found", []))
            st.success("Detection complete.")
        else:
            st.error(r.text)


if refresh_btn or "fraud_graph" not in st.session_state:
    with st.spinner("Fetching graph visualization data…"):
        r = api_get("/fraud/graph-data")
        if r.status_code == 200:
            st.session_state["fraud_graph"] = r.json()
        else:
            st.error(r.text)


graph = st.session_state.get("fraud_graph", {"nodes": [], "edges": []})
result = st.session_state.get("fraud_result", {"chains_found": [], "risk_summary": {}})

if graph.get("backend") and graph.get("backend") != "neo4j":
    st.markdown('<span class="taxiq-badge">[DEMO DATA] Graph running on networkx (Neo4j unavailable)</span>', unsafe_allow_html=True)

metrics = st.columns(3)
with metrics[0]:
    st.metric("Total GSTINs in Network", len([n for n in graph.get("nodes", []) if str(n.get("id", "")).startswith("27")]))
with metrics[1]:
    rs = result.get("risk_summary", {})
    st.metric("High Risk GSTINs (red)", int(rs.get("high_risk", 0)))
with metrics[2]:
    st.metric("Circular Chains Detected", len(result.get("chains_found", [])))


st.divider()

st.markdown("### Interactive Fraud Network")
net = Network(height="560px", width="100%", bgcolor="#0A1628", font_color="white", directed=True)
net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=120, spring_strength=0.02, damping=0.09)

for n in graph.get("nodes", []):
    r = float(n.get("risk_score", 0))
    color = "#FF3B5C" if r > 0.7 else "#FF9933" if r > 0.4 else "#00B894"
    net.add_node(n["id"], label=n.get("label", n["id"]), title=f"risk={r:.2f}", color=color)

for e in graph.get("edges", []):
    width = float(e.get("width", 2))
    val = float(e.get("value", 0))
    net.add_edge(e["from"], e["to"], value=val, width=width, title=f"ITC value ₹{val:,.0f}")

html = net.generate_html()
st.components.v1.html(html, height=600, scrolling=True)


st.divider()

bottom = st.columns([0.55, 0.45], gap="large")
with bottom[0]:
    st.markdown("### Flagged GSTINs (Top Risk)")
    top10 = result.get("risk_summary", {}).get("top10", [])
    st.dataframe(top10, use_container_width=True)

with bottom[1]:
    st.markdown("### Circular Chains")
    for idx, c in enumerate(result.get("chains_found", [])):
        with st.expander(f"Chain {idx+1} · length {c.get('chain_length')}"):
            st.write(" → ".join(c.get("gstins", [])))

