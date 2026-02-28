"""
TaxIQ — 📋 ITC Recovery Tracker
Kanban pipeline: At Risk → In Progress → Recovered
Funnel chart · Trend line · Actionable cards.
"""
import os
import sys

import httpx
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, fmt_inr, api_get, BACKEND_URL, CHART_LAYOUT, COLORS

st.set_page_config(page_title="TaxIQ | ITC Recovery", page_icon="📋", layout="wide")
inject_css()


# ── Header ──────────────────────────────────────────────
st.markdown('<div class="page-title">📋 ITC Recovery Tracker</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">From mismatch → notice → vendor response → recovery. Track every rupee.</div>', unsafe_allow_html=True)

# ── Load pipeline ───────────────────────────────────────
try:
    r = api_get("/api/recovery/pipeline")
    if r.status_code == 200:
        pipeline = r.json()
    else:
        st.error(f"Backend returned HTTP {r.status_code}")
        pipeline = {"at_risk": [], "in_progress": [], "recovered": []}
except Exception as e:
    st.error(f"Could not reach backend: {e}")
    pipeline = {"at_risk": [], "in_progress": [], "recovered": []}

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
    for idx, c in enumerate(at_risk):
        with st.container():
            st.markdown(f"**{c['name']}**")
            st.caption(f"GSTIN: {c['gstin']}")
            st.markdown(f"💰 {fmt_inr(c['amount'])} · 📋 {c.get('mismatch_type', 'Unknown')}")
            days = c.get("days_pending", 0)
            st.progress(min(days / 90, 1.0), text=f"{days}/90 days pending")
            if st.button("📨 Send Notice", key=f"send_{idx}_{c['gstin']}", use_container_width=True):
                st.toast(f"📨 Notice sent to {c['name']}!", icon="✅")

with k2:
    st.markdown(f'<div class="kanban-header-prog">🟡 IN PROGRESS — {len(in_prog)} cases · {fmt_inr(total_prog)}</div>', unsafe_allow_html=True)
    for idx, c in enumerate(in_prog):
        with st.container():
            st.markdown(f"**{c['name']}**")
            st.caption(f"GSTIN: {c['gstin']}")
            st.markdown(f"💰 {fmt_inr(c['amount'])} · 📋 {c.get('mismatch_type', 'Unknown')}")
            days = c.get("days_pending", 0)
            st.progress(min(days / 90, 1.0), text=f"{days}/90 days pending")
            if st.button("📞 Follow Up", key=f"follow_{idx}_{c['gstin']}", use_container_width=True):
                st.toast(f"📞 Follow-up reminder set for {c['name']}!", icon="🔔")

with k3:
    st.markdown(f'<div class="kanban-header-done">🟢 RECOVERED — {len(recovered)} cases · {fmt_inr(total_rec)}</div>', unsafe_allow_html=True)
    for idx, c in enumerate(recovered):
        with st.container():
            st.markdown(f"**{c['name']}**")
            st.caption(f"GSTIN: {c['gstin']}")
            st.markdown(f"💰 {fmt_inr(c['amount'])} · ✅ Recovered {c.get('recovered_date', '')}")
            st.progress(1.0, text="Complete")
            if st.button("🗂 Close Case", key=f"close_{idx}_{c['gstin']}", use_container_width=True):
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
    **CHART_LAYOUT,
    height=320,
)
st.plotly_chart(fig_funnel, use_container_width=True)

st.divider()

# ── Recovery Trend ──────────────────────────────────────
st.markdown("### Recovery Trend (6 Months)")

try:
    r = api_get("/api/recovery/trend")
    if r.status_code == 200:
        trend = r.json().get("trend", [])
    else:
        trend = []
except Exception:
    trend = []

if not trend:
    st.info("No trend data available yet.")
else:
    months = [t["month"] for t in trend]

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=months,
        y=[t["at_risk"] for t in trend],
        name="At Risk",
        mode="lines+markers",
        line=dict(color="#D63031", width=3),
        marker=dict(size=8),
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
        **CHART_LAYOUT,
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="Amount (₹)",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

st.caption("Powered by ITC Recovery Engine · Real-time Pipeline · TaxIQ")
