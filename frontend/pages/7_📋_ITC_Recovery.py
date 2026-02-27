"""
TaxIQ — 📋 ITC Recovery Pipeline
Kanban board tracking Input Tax Credit at risk, in progress, and recovered.
"""

import os
import json
from datetime import datetime, timedelta
import random

import httpx
import streamlit as st

st.set_page_config(page_title="TaxIQ | ITC Recovery", page_icon="📋", layout="wide")

BACKEND = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")

# ── CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
section.main { background-color: #0A1628; }
div[data-testid="stAppViewContainer"] { background-color: #0A1628; }
.demo-badge {
  display:inline-block; padding:2px 8px; border-radius:999px;
  border:1px solid rgba(255,153,51,.55);
  background: rgba(255,153,51,.10);
  color: #FF9933; font-size: 12px; margin-left: 8px;
}
.kanban-header {
  font-size: 16px; font-weight: 700; padding: 6px 12px;
  border-radius: 6px; margin-bottom: 10px; text-align: center;
}
.kanban-risk   { background: rgba(239,68,68,.15); color: #EF4444; border: 1px solid rgba(239,68,68,.35); }
.kanban-prog   { background: rgba(245,158,11,.15); color: #F59E0B; border: 1px solid rgba(245,158,11,.35); }
.kanban-done   { background: rgba(34,197,94,.15);  color: #22C55E; border: 1px solid rgba(34,197,94,.35); }

.kanban-card {
  background: #0E1F3E; border: 1px solid #1A3A5C; border-radius: 8px;
  padding: 14px; margin-bottom: 10px; position: relative;
}
.kanban-card:hover { border-color: #FF9933; }
.card-gstin   { font-size: 13px; color: #94A3B8; margin-bottom: 4px; }
.card-vendor  { font-size: 15px; font-weight: 600; color: #E0E0E0; }
.card-amount  { font-size: 18px; font-weight: 700; color: #FF9933; margin: 6px 0; }
.card-days    { font-size: 12px; color: #94A3B8; }
.drag-hint    { font-size: 11px; color: #475569; text-align: center; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


def inr(v):
    """Format a number in Indian style (₹X,XX,XXX)."""
    s = f"{int(abs(v)):,}"
    parts = s.split(",")
    if len(parts) <= 1:
        formatted = s
    else:
        last = parts[-1]
        rest = ",".join(parts[:-1])
        # Re-group rest in 2-digit segments (Indian numbering)
        rest_digits = rest.replace(",", "")
        groups = []
        while len(rest_digits) > 2:
            groups.insert(0, rest_digits[-2:])
            rest_digits = rest_digits[:-2]
        if rest_digits:
            groups.insert(0, rest_digits)
        formatted = ",".join(groups) + "," + last
    return f"₹{formatted}"


def api_get(path, params=None):
    with httpx.Client(timeout=30) as c:
        return c.get(f"{BACKEND}{path}", params=params)


# ── Demo data ───────────────────────────────────────────
def demo_pipeline():
    return {
        "gstin": "27AADCB2230M1ZT",
        "columns": [
            {
                "id": "at_risk",
                "title": "🔴 At Risk",
                "cards": [
                    {"id": "ITC-001", "vendor": "M/s Rathi Steel Corp",
                     "gstin": "27AAECR4512K1ZM",
                     "amount": 185000, "days": 45,
                     "action": "Send Reminder"},
                    {"id": "ITC-002", "vendor": "M/s Patel Chemicals",
                     "gstin": "24ABCPD6789Q1ZN",
                     "amount": 95000, "days": 62,
                     "action": "Escalate"},
                    {"id": "ITC-003", "vendor": "M/s Gupta Textiles",
                     "gstin": "09AAFCG1234L1ZP",
                     "amount": 210000, "days": 30,
                     "action": "Verify Invoice"},
                ],
            },
            {
                "id": "in_progress",
                "title": "🟡 In Progress",
                "cards": [
                    {"id": "ITC-004", "vendor": "M/s Sharma Electronics",
                     "gstin": "07ABCPS5678M1ZR",
                     "amount": 120000, "days": 18,
                     "action": "Follow Up"},
                    {"id": "ITC-005", "vendor": "M/s Reddy Motors",
                     "gstin": "36AADCR9876P1ZS",
                     "amount": 75000, "days": 10,
                     "action": "Confirm Payment"},
                ],
            },
            {
                "id": "recovered",
                "title": "🟢 Recovered",
                "cards": [
                    {"id": "ITC-006", "vendor": "M/s Kumar Traders",
                     "gstin": "33ABDCK3456N1ZT",
                     "amount": 145000, "days": 0,
                     "action": "Completed"},
                    {"id": "ITC-007", "vendor": "M/s Singh Logistics",
                     "gstin": "06AACS7890R1ZU",
                     "amount": 88000, "days": 0,
                     "action": "Completed"},
                    {"id": "ITC-008", "vendor": "M/s Joshi Packaging",
                     "gstin": "29AABCJ2345S1ZV",
                     "amount": 62000, "days": 0,
                     "action": "Completed"},
                    {"id": "ITC-009", "vendor": "M/s Deshmukh Foods",
                     "gstin": "27AAEPD4567T1ZW",
                     "amount": 55000, "days": 0,
                     "action": "Completed"},
                ],
            },
        ],
    }


# ── Header ──────────────────────────────────────────────
st.markdown("## 📋 ITC Recovery Pipeline")
st.caption("Track Input Tax Credit claims from at-risk through recovery. Kanban-style pipeline view.")

st.divider()

# ── Load pipeline data ──────────────────────────────────
if st.button("🔄 Load Recovery Pipeline", use_container_width=True, type="primary"):
    with st.spinner("Fetching ITC pipeline from backend…"):
        try:
            r = api_get("/api/recovery/pipeline")
            if r.status_code == 200:
                st.session_state["itc_pipeline"] = r.json()
                st.session_state["itc_demo"] = False
            else:
                raise Exception(f"HTTP {r.status_code}")
        except Exception:
            st.session_state["itc_pipeline"] = demo_pipeline()
            st.session_state["itc_demo"] = True

# Default demo data
if "itc_pipeline" not in st.session_state:
    st.session_state["itc_pipeline"] = demo_pipeline()
    st.session_state["itc_demo"] = True

pipeline = st.session_state["itc_pipeline"]
is_demo = st.session_state.get("itc_demo", False)

if is_demo:
    st.markdown('<span class="demo-badge">[DEMO]</span>', unsafe_allow_html=True)

# ── Compute summary metrics ────────────────────────────
cols_data = pipeline.get("columns", [])
col_map = {}
for col in cols_data:
    cid = col.get("id", "")
    cards = col.get("cards", [])
    total = sum(c.get("amount", 0) for c in cards)
    col_map[cid] = {"total": total, "count": len(cards), "cards": cards, "title": col.get("title", "")}

at_risk_amt = col_map.get("at_risk", {}).get("total", 0)
in_progress_amt = col_map.get("in_progress", {}).get("total", 0)
recovered_amt = col_map.get("recovered", {}).get("total", 0)
total_itc = at_risk_amt + in_progress_amt + recovered_amt
recovery_rate = (recovered_amt / total_itc * 100) if total_itc > 0 else 0

# ── Summary metrics row ────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total ITC Tracked", inr(total_itc))
m2.metric("🔴 At Risk", inr(at_risk_amt))
m3.metric("🟢 Recovered", inr(recovered_amt))
m4.metric("Recovery Rate", f"{recovery_rate:.1f}%")

st.divider()

# ── Kanban board ────────────────────────────────────────
st.markdown("### Kanban Board")

k1, k2, k3 = st.columns(3)

def render_kanban_column(container, col_id, css_class):
    data = col_map.get(col_id, {"total": 0, "count": 0, "cards": [], "title": col_id})
    with container:
        st.markdown(f'<div class="kanban-header {css_class}">{data["title"]}  ({data["count"]})</div>',
                     unsafe_allow_html=True)
        st.markdown(f'<div style="text-align:center;font-size:13px;color:#94A3B8;margin-bottom:8px;">'
                     f'Total: {inr(data["total"])}</div>', unsafe_allow_html=True)

        for card in data["cards"]:
            st.markdown(f"""
            <div class="kanban-card">
                <div class="card-gstin">{card.get("gstin", "—")}</div>
                <div class="card-vendor">{card.get("vendor", "Unknown")}</div>
                <div class="card-amount">{inr(card.get("amount", 0))}</div>
                <div class="card-days">{'✅ Settled' if card.get("days", 0) == 0 else f'⏳ {card["days"]} days pending'}</div>
            </div>""", unsafe_allow_html=True)

            if card.get("action") and card["action"] != "Completed":
                if st.button(f"⚡ {card['action']}", key=f"btn_{card['id']}",
                             use_container_width=True):
                    st.toast(f"Action '{card['action']}' triggered for {card.get('vendor', card['id'])}!", icon="⚡")

        st.markdown('<div class="drag-hint">↕ Drag to reorder (visual hint)</div>',
                     unsafe_allow_html=True)


render_kanban_column(k1, "at_risk", "kanban-risk")
render_kanban_column(k2, "in_progress", "kanban-prog")
render_kanban_column(k3, "recovered", "kanban-done")

st.divider()

# ── Funnel chart ────────────────────────────────────────
st.markdown("### Recovery Funnel")

try:
    import plotly.graph_objects as go

    labels = ["🔴 At Risk", "🟡 In Progress", "🟢 Recovered"]
    values = [at_risk_amt, in_progress_amt, recovered_amt]
    colors = ["#EF4444", "#F59E0B", "#22C55E"]

    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textinfo="value+percent initial",
        texttemplate="%{value:,.0f}<br>%{percentInitial:.1%}",
        marker=dict(color=colors),
    ))
    fig.update_layout(
        paper_bgcolor="#0A1628",
        plot_bgcolor="#0A1628",
        font=dict(color="#E0E0E0"),
        height=340,
        margin=dict(l=20, r=20, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
except ImportError:
    st.warning("Plotly not installed. Showing text summary instead.")
    st.write(f"At Risk: {inr(at_risk_amt)} | In Progress: {inr(in_progress_amt)} | Recovered: {inr(recovered_amt)}")

# ── Recovery timeline ───────────────────────────────────
st.divider()
st.markdown("### 📈 Recovery Trend (Last 6 Months)")

try:
    import plotly.graph_objects as go

    months = []
    now = datetime.now()
    for i in range(5, -1, -1):
        d = now - timedelta(days=30 * i)
        months.append(d.strftime("%b '%y"))

    # Simulated cumulative data for demo
    random.seed(42)
    cum_recovered = [0] * 6
    base = 50000
    for i in range(6):
        base += random.randint(30000, 100000)
        cum_recovered[i] = base

    cum_risk = [total_itc - r for r in cum_recovered]
    cum_risk = [max(0, r) for r in cum_risk]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=months, y=cum_risk, name="ITC at Risk",
        fill="tozeroy", fillcolor="rgba(239,68,68,.15)",
        line=dict(color="#EF4444", width=2),
    ))
    fig2.add_trace(go.Scatter(
        x=months, y=cum_recovered, name="Recovered",
        fill="tozeroy", fillcolor="rgba(34,197,94,.15)",
        line=dict(color="#22C55E", width=2),
    ))
    fig2.update_layout(
        paper_bgcolor="#0A1628",
        plot_bgcolor="#0A1628",
        font=dict(color="#E0E0E0"),
        xaxis=dict(gridcolor="#1A2E50"),
        yaxis=dict(gridcolor="#1A2E50", tickprefix="₹"),
        legend=dict(x=0, y=1.1, orientation="h"),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)
except ImportError:
    pass

st.divider()
st.caption("Powered by GSTN Reconciliation Engine · TaxIQ")
