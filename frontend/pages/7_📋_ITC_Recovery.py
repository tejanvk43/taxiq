"""
TaxIQ — 📋 ITC Recovery Tracker
Kanban pipeline: At Risk → In Progress → Recovered
Funnel chart · Trend line · Actionable cards.
"""
import os

import httpx
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="TaxIQ | ITC Recovery", page_icon="📋", layout="wide")

BACKEND = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")

# ── Design System CSS ───────────────────────────────────
st.markdown("""<style>
    .stApp { background-color: #0A1628; color: #F8F9FA; }
    .stMetric { background: #0D1F3C; border-radius: 12px;
                padding: 16px; border-left: 4px solid #FF9933; }
    .stButton>button { background: #FF9933; color: #0A1628;
                       font-weight: 700; border-radius: 8px;
                       border: none; }
    div[data-testid="metric-container"] {
      background: #0D1F3C; border-radius: 10px; padding: 10px; }
    .demo-badge {
      display:inline-block; padding:2px 10px; border-radius:999px;
      background:rgba(253,203,110,.15); border:1px solid #FDCB6E;
      color:#FDCB6E; font-size:12px; font-weight:600; }
    .kanban-header-risk    { background:#D63031; color:#FFF; padding:6px 14px;
                             border-radius:8px 8px 0 0; font-weight:700; }
    .kanban-header-prog    { background:#FDCB6E; color:#0A1628; padding:6px 14px;
                             border-radius:8px 8px 0 0; font-weight:700; }
    .kanban-header-done    { background:#00B894; color:#0A1628; padding:6px 14px;
                             border-radius:8px 8px 0 0; font-weight:700; }
    .kanban-card {
      background:#0D1F3C; border:1px solid #1E3A5F; border-radius:0 0 8px 8px;
      padding:12px; margin-bottom:8px; }
</style>""", unsafe_allow_html=True)


def fmt_inr(n):
    if n >= 1e7:  return f"₹{n/1e7:.1f}Cr"
    if n >= 1e5:  return f"₹{n/1e5:.1f}L"
    return f"₹{n:,.0f}"


def api_get(path):
    with httpx.Client(timeout=30) as c:
        return c.get(f"{BACKEND}{path}")


# ── DEMO DATA ──────────────────────────────────────────
DEMO_PIPELINE = {
    "at_risk": [
        {"gstin": "19AABCG1234Q1Z2", "name": "GoldStar Traders", "amount": 450000, "days_pending": 12, "mismatch_type": "Invoice Missing in GSTR-2B"},
        {"gstin": "07AABCS7777H1Z1", "name": "Shadow Supplies", "amount": 280000, "days_pending": 5, "mismatch_type": "Taxable Value Mismatch"},
        {"gstin": "33ABDCK3456N1ZT", "name": "Kumar Traders", "amount": 120000, "days_pending": 28, "mismatch_type": "GSTIN Mismatch"},
    ],
    "in_progress": [
        {"gstin": "24ABCPD6789Q1ZN", "name": "Patel Chemicals", "amount": 360000, "days_pending": 45, "mismatch_type": "Tax Rate Mismatch", "notice_sent": True},
        {"gstin": "27AABCR5678P1Z4", "name": "Rajesh Exports", "amount": 175000, "days_pending": 60, "mismatch_type": "Invoice Missing in GSTR-2B", "notice_sent": True},
    ],
    "recovered": [
        {"gstin": "29AAACN0001A1Z5", "name": "Nexus Manufacturing", "amount": 520000, "days_pending": 0, "mismatch_type": "Taxable Value Mismatch", "recovered_date": "2025-01-10"},
        {"gstin": "27AAACF9999K1Z9", "name": "Falcon Components", "amount": 310000, "days_pending": 0, "mismatch_type": "Tax Rate Mismatch", "recovered_date": "2024-12-28"},
        {"gstin": "36AABCT4321M1Z8", "name": "Telangana Steel", "amount": 195000, "days_pending": 0, "mismatch_type": "GSTIN Mismatch", "recovered_date": "2024-12-15"},
    ],
}

DEMO_TREND = [
    {"month": "Aug '24", "recovered": 120000, "at_risk": 800000},
    {"month": "Sep '24", "recovered": 250000, "at_risk": 720000},
    {"month": "Oct '24", "recovered": 410000, "at_risk": 650000},
    {"month": "Nov '24", "recovered": 680000, "at_risk": 500000},
    {"month": "Dec '24", "recovered": 830000, "at_risk": 420000},
    {"month": "Jan '25", "recovered": 1025000, "at_risk": 350000},
]

# ── Header ──────────────────────────────────────────────
st.title("📋 ITC Recovery Tracker")
st.caption("From mismatch → notice → vendor response → recovery. Track every rupee.")

# ── Load pipeline ───────────────────────────────────────
try:
    r = api_get("/api/recovery/pipeline")
    if r.status_code == 200:
        pipeline = r.json()
        is_demo = False
    else:
        raise Exception()
except Exception:
    pipeline = DEMO_PIPELINE
    is_demo = True

if is_demo:
    st.markdown('<span class="demo-badge">[DEMO DATA]</span>', unsafe_allow_html=True)

at_risk = pipeline.get("at_risk", [])
in_prog = pipeline.get("in_progress", [])
recovered = pipeline.get("recovered", [])

st.divider()

# ── Top Metrics ─────────────────────────────────────────
total_risk = sum(c["amount"] for c in at_risk)
total_prog = sum(c["amount"] for c in in_prog)
total_rec  = sum(c["amount"] for c in recovered)
total_all  = total_risk + total_prog + total_rec
rate = (total_rec / total_all * 100) if total_all else 0
prev_rate = rate - 4.2  # simulated trend

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total ITC At Risk", fmt_inr(total_risk + total_prog))
m2.metric("In Progress", fmt_inr(total_prog), delta=f"{len(in_prog)} cases")
m3.metric("Recovered", fmt_inr(total_rec), delta=f"+{fmt_inr(total_rec)}")
m4.metric("Recovery Rate", f"{rate:.1f}%", delta=f"↑{rate - prev_rate:.1f}%")

st.divider()

# ── Kanban Board ────────────────────────────────────────
st.markdown("### Pipeline Board")
k1, k2, k3 = st.columns(3)

with k1:
    st.markdown(f'<div class="kanban-header-risk">🔴 AT RISK — {len(at_risk)} cases · {fmt_inr(total_risk)}</div>', unsafe_allow_html=True)
    for c in at_risk:
        with st.container():
            st.markdown(f"**{c['name']}**")
            st.caption(f"GSTIN: {c['gstin']}")
            st.markdown(f"💰 {fmt_inr(c['amount'])} · 📋 {c.get('mismatch_type', 'Unknown')}")
            days = c.get("days_pending", 0)
            st.progress(min(days / 90, 1.0), text=f"{days}/90 days pending")
            if st.button("📨 Send Notice", key=f"send_{c['gstin']}", use_container_width=True):
                st.toast(f"📨 Notice sent to {c['name']}!", icon="✅")

with k2:
    st.markdown(f'<div class="kanban-header-prog">🟡 IN PROGRESS — {len(in_prog)} cases · {fmt_inr(total_prog)}</div>', unsafe_allow_html=True)
    for c in in_prog:
        with st.container():
            st.markdown(f"**{c['name']}**")
            st.caption(f"GSTIN: {c['gstin']}")
            st.markdown(f"💰 {fmt_inr(c['amount'])} · 📋 {c.get('mismatch_type', 'Unknown')}")
            days = c.get("days_pending", 0)
            st.progress(min(days / 90, 1.0), text=f"{days}/90 days pending")
            if st.button("📞 Follow Up", key=f"follow_{c['gstin']}", use_container_width=True):
                st.toast(f"📞 Follow-up reminder set for {c['name']}!", icon="🔔")

with k3:
    st.markdown(f'<div class="kanban-header-done">🟢 RECOVERED — {len(recovered)} cases · {fmt_inr(total_rec)}</div>', unsafe_allow_html=True)
    for c in recovered:
        with st.container():
            st.markdown(f"**{c['name']}**")
            st.caption(f"GSTIN: {c['gstin']}")
            st.markdown(f"💰 {fmt_inr(c['amount'])} · ✅ Recovered {c.get('recovered_date', '')}")
            st.progress(1.0, text="Complete")
            if st.button("🗂 Close Case", key=f"close_{c['gstin']}", use_container_width=True):
                st.toast(f"🗂 Case closed for {c['name']}", icon="✅")

st.divider()

# ── Funnel Chart ────────────────────────────────────────
st.markdown("### Recovery Funnel")

funnel_stages = ["Identified", "Notice Sent", "Response Received", "Partially Resolved", "Fully Recovered"]
funnel_values = [
    len(at_risk) + len(in_prog) + len(recovered),
    len(in_prog) + len(recovered),
    len(in_prog) + len(recovered) - 1,
    len(recovered) + 1,
    len(recovered),
]
funnel_colors = ["#D63031", "#FF9933", "#FDCB6E", "#00B894", "#00B894"]

fig_funnel = go.Figure(go.Funnel(
    y=funnel_stages,
    x=funnel_values,
    marker=dict(color=funnel_colors),
    textinfo="value+percent initial",
    textfont=dict(color="#F8F9FA"),
))
fig_funnel.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0A1628",
    plot_bgcolor="#0D1F3C",
    font_color="#F8F9FA",
    height=320,
    margin=dict(l=20, r=20, t=20, b=20),
)
st.plotly_chart(fig_funnel, use_container_width=True)

st.divider()

# ── Recovery Trend ──────────────────────────────────────
st.markdown("### Recovery Trend (6 Months)")

trend = DEMO_TREND
months = [t["month"] for t in trend]

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(
    x=months,
    y=[t["at_risk"] for t in trend],
    name="At Risk",
    mode="lines+markers",
    line=dict(color="#D63031", width=3),
    marker=dict(size=8),
    fill="tonexty" if False else None,
))
fig_trend.add_trace(go.Scatter(
    x=months,
    y=[t["recovered"] for t in trend],
    name="Recovered",
    mode="lines+markers",
    line=dict(color="#00B894", width=3),
    marker=dict(size=8),
))
fig_trend.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0A1628",
    plot_bgcolor="#0D1F3C",
    font_color="#F8F9FA",
    height=300,
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    yaxis_title="Amount (₹)",
)
st.plotly_chart(fig_trend, use_container_width=True)

st.caption("Powered by ITC Recovery Engine · Real-time Pipeline · TaxIQ")
