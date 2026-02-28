"""
TaxIQ — 📈 Predictive Vendor Compliance Risk Model
Historical graph patterns → Trend analysis → Future risk prediction → Actionable insights.
"""
import os
import sys

import httpx
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, api_get, fmt_inr, BACKEND_URL, CHART_LAYOUT, COLORS

st.set_page_config(page_title="TaxIQ | Predictive Risk", page_icon="📈", layout="wide")
inject_css()

# ── Page Header ─────────────────────────────────────────
st.markdown('<div class="page-title">📈 Predictive Vendor Compliance Risk</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Historical graph patterns · Trend analysis · Future risk prediction · Actionable recommendations</div>', unsafe_allow_html=True)

# ── Vendor Selection ────────────────────────────────────
st.markdown("### Select Vendor for Prediction")

# Load vendors first
if "pred_vendors" not in st.session_state:
    try:
        r = api_get("/api/vendors/list")
        if r.status_code == 200:
            st.session_state["pred_vendors"] = r.json().get("vendors", [])
        else:
            st.session_state["pred_vendors"] = []
    except Exception:
        st.session_state["pred_vendors"] = []

vendors = st.session_state["pred_vendors"]

if not vendors:
    col_load, _ = st.columns([1, 3])
    with col_load:
        if st.button("📥 Load Vendor Network", use_container_width=True, type="primary"):
            try:
                r = api_get("/api/vendors/list")
                if r.status_code == 200:
                    st.session_state["pred_vendors"] = r.json().get("vendors", [])
                    st.rerun()
                else:
                    st.error(f"Backend HTTP {r.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")
    st.info("Click **Load Vendor Network** to fetch vendors from the backend.")
    st.stop()

# Vendor selector
vendor_options = [f"{v.get('name', '')} ({v.get('gstin', '')})" for v in vendors]
p1, p2 = st.columns([3, 1])
with p1:
    selected = st.selectbox("Choose vendor", vendor_options)
with p2:
    months_ahead = st.slider("Predict months ahead", min_value=1, max_value=6, value=3)

sel_idx = vendor_options.index(selected)
vendor = vendors[sel_idx]
gstin_sel = vendor.get("gstin", "")

# ── Run Prediction ──────────────────────────────────────
predict_btn = st.button("🔮 Run Predictive Analysis", use_container_width=True, type="primary")

if predict_btn:
    with st.spinner("Analyzing historical patterns and generating predictions..."):
        try:
            r = api_get(f"/api/vendors/{gstin_sel}/predict", params={"months_ahead": months_ahead})
            if r.status_code == 200:
                st.session_state["pred_result"] = r.json()
                st.session_state["pred_gstin"] = gstin_sel
            else:
                st.error(f"Prediction failed: HTTP {r.status_code}")
        except Exception as e:
            st.error(f"Could not reach backend: {e}")

# ── Display ─────────────────────────────────────────────
pred = st.session_state.get("pred_result")
if not pred or st.session_state.get("pred_gstin") != gstin_sel:
    st.info("Select a vendor and click **Run Predictive Analysis** to forecast compliance risk.")
    st.stop()

st.divider()

# ── Current Status ──────────────────────────────────────
current_score = pred.get("current_score", 0)
current_grade = pred.get("current_grade", "D")
outlook = pred.get("overall_outlook", "STABLE")
slope = pred.get("slope", 0)

outlook_config = {
    "IMPROVING": ("🟢", COLORS["green"], "Vendor is trending upward — lower risk over time"),
    "DECLINING": ("🔴", COLORS["red"], "Vendor is trending downward — increasing risk"),
    "STABLE":    ("🟡", COLORS["yellow"], "Vendor performance is stable with no significant trend"),
}
outlook_icon, outlook_color, outlook_desc = outlook_config.get(outlook, ("⚪", "#888", ""))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Current Score", f"{current_score}/100")
m2.metric("Current Grade", current_grade)
m3.metric("Trend Slope", f"{slope:+.2f}/month")
m4.metric("Outlook", f"{outlook_icon} {outlook}")

st.markdown(
    f'<div class="tiq-card" style="border-left:4px solid {outlook_color};margin-top:12px">'
    f'<strong style="color:{outlook_color}">{outlook_icon} {outlook}</strong> — {outlook_desc}. '
    f'Slope: {slope:+.2f} points/month.</div>',
    unsafe_allow_html=True,
)

st.divider()

# ── Prediction Chart ────────────────────────────────────
st.markdown("### 📊 Score Forecast")

predictions = pred.get("predictions", [])

# Get historical data too
try:
    hist_r = api_get(f"/api/vendors/{gstin_sel}/history", params={"months": 6})
    if hist_r.status_code == 200:
        history = hist_r.json().get("history", [])
    else:
        history = []
except Exception:
    history = []

# Build chart with history + prediction
fig = go.Figure()

# Historical line
if history:
    hist_months = [h.get("month", "") for h in history]
    hist_scores = [h.get("score", 0) for h in history]
    fig.add_trace(go.Scatter(
        x=hist_months,
        y=hist_scores,
        mode="lines+markers",
        name="Historical",
        line=dict(color=COLORS["accent"], width=3),
        marker=dict(size=10, symbol="circle"),
    ))

# Prediction line
pred_months = [f"+{p['month_offset']}M" for p in predictions]
pred_scores = [p["predicted_score"] for p in predictions]
pred_confidence = [p.get("confidence", 0.9) for p in predictions]

# Connect history to prediction
if history:
    pred_months = [hist_months[-1]] + pred_months
    pred_scores = [hist_scores[-1]] + pred_scores

fig.add_trace(go.Scatter(
    x=pred_months,
    y=pred_scores,
    mode="lines+markers",
    name="Predicted",
    line=dict(color=COLORS["blue"], width=3, dash="dash"),
    marker=dict(size=10, symbol="diamond"),
))

# Confidence bands
if predictions:
    upper = [min(99, s + int(20 * (1 - c))) for s, c in zip(pred_scores[1:] if history else pred_scores, pred_confidence)]
    lower = [max(5, s - int(20 * (1 - c))) for s, c in zip(pred_scores[1:] if history else pred_scores, pred_confidence)]
    x_band = pred_months[1:] if history else pred_months

    fig.add_trace(go.Scatter(
        x=x_band + x_band[::-1],
        y=upper + lower[::-1],
        fill="toself",
        fillcolor="rgba(116,185,255,0.1)",
        line=dict(width=0),
        name="Confidence Band",
        showlegend=True,
    ))

# Risk threshold lines
fig.add_hline(y=40, line_dash="dot", line_color=COLORS["red"],
              annotation_text="High Risk Threshold", annotation_position="top right")
fig.add_hline(y=70, line_dash="dot", line_color=COLORS["green"],
              annotation_text="Good Standing", annotation_position="top right")

fig.update_layout(
    **CHART_LAYOUT,
    height=400,
    yaxis=dict(range=[0, 100], title="Compliance Score"),
    xaxis_title="Period",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Prediction Details Table ────────────────────────────
st.markdown("### 📋 Month-by-Month Predictions")

pred_cols = st.columns(min(len(predictions), 6))
for i, (col, p) in enumerate(zip(pred_cols, predictions)):
    with col:
        score = p["predicted_score"]
        grade = p.get("predicted_grade", "D")
        flag = p.get("risk_flag", "STABLE")
        conf = p.get("confidence", 0)

        flag_config = {
            "IMPROVING": ("↗️", COLORS["green"]),
            "DECLINING": ("↘️", COLORS["red"]),
            "STABLE": ("→", COLORS["yellow"]),
        }
        f_icon, f_color = flag_config.get(flag, ("→", "#888"))

        grade_css_cls = "grade-aaa" if grade in ("AAA", "AA") else "grade-a" if grade in ("A", "BBB") else "grade-b" if grade in ("BB", "B") else "grade-d"

        st.markdown(
            f'<div class="tiq-card" style="text-align:center">'
            f'<div style="color:var(--text-muted);font-size:12px;text-transform:uppercase">Month +{p["month_offset"]}</div>'
            f'<div style="font-size:36px;font-weight:800;color:{f_color};margin:8px 0">{score}</div>'
            f'<div><span class="{grade_css_cls}">{grade}</span></div>'
            f'<div style="margin-top:8px;color:{f_color};font-weight:600">{f_icon} {flag}</div>'
            f'<div style="color:var(--text-muted);font-size:11px;margin-top:4px">Conf: {conf:.0%}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.divider()

# ── Risk Factors ────────────────────────────────────────
st.markdown("### ⚠️ Risk Factors & Recommendations")

risk_factors = pred.get("risk_factors", [])

if risk_factors:
    for rf in risk_factors:
        severity = rf.get("severity", "MEDIUM")
        sev_color = COLORS["red"] if severity == "HIGH" else COLORS["yellow"]
        score_val = rf.get("score", 50)

        st.markdown(
            f'<div class="tiq-card" style="border-left:4px solid {sev_color}">'
            f'<div style="display:flex;align-items:center;justify-content:space-between">'
            f'<div>'
            f'<span class="pill pill-{"red" if severity=="HIGH" else "yellow"}">{severity}</span>'
            f'<strong style="margin-left:8px">{rf.get("factor", "")}</strong>'
            f'<span style="color:var(--text-muted);margin-left:8px">Score: {score_val}/100</span>'
            f'</div>'
            f'<div style="width:120px">'
            f'<div style="background:var(--border);border-radius:4px;height:8px;overflow:hidden">'
            f'<div style="background:{sev_color};width:{score_val}%;height:100%;border-radius:4px"></div>'
            f'</div></div></div>'
            f'<div style="color:var(--text-muted);font-size:13px;margin-top:8px">'
            f'💡 {rf.get("recommendation", "")}</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.success("✅ No significant risk factors detected. This vendor has a healthy compliance profile.")

st.divider()

# ── Vendor Comparison Spider ────────────────────────────
st.markdown("### 🕸️ Current Factor Analysis")

# Get current vendor factors
try:
    score_r = api_get(f"/api/vendors/score/{gstin_sel}")
    if score_r.status_code == 200:
        factors = score_r.json().get("factors", {})
    else:
        factors = vendor.get("factors", {})
except Exception:
    factors = vendor.get("factors", {})

if factors:
    cats = ["Filing\nRegularity", "ITC\nAccuracy", "Turnover\nConsistency",
            "Network\nTrust", "Amendment\nFrequency"]
    vals = [
        factors.get("filing_regularity", 50),
        factors.get("itc_accuracy", 50),
        factors.get("turnover_consistency", 50),
        factors.get("network_trustworthiness", 50),
        factors.get("amendment_frequency", 50),
    ]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=cats + [cats[0]],
        fill="toself",
        fillcolor=f"rgba(255,153,51,0.2)",
        line=dict(color=COLORS["accent"], width=2),
        name="Current",
    ))

    # Add prediction overlay if declining
    if outlook == "DECLINING" and predictions:
        predicted_factor = max(5, current_score + slope * 3)
        ratio = predicted_factor / max(current_score, 1)
        pred_vals = [max(5, int(v * ratio)) for v in vals]
        fig_radar.add_trace(go.Scatterpolar(
            r=pred_vals + [pred_vals[0]],
            theta=cats + [cats[0]],
            fill="toself",
            fillcolor=f"rgba(214,48,49,0.1)",
            line=dict(color=COLORS["red"], width=2, dash="dash"),
            name="Predicted (3M)",
        ))

    fig_radar.update_layout(
        **CHART_LAYOUT,
        height=380,
        polar=dict(
            radialaxis=dict(range=[0, 100], showticklabels=True, tickfont=dict(size=10)),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

st.caption("Powered by TaxIQ Predictive Engine · Historical Graph Patterns · NEXUS 5-Factor Model")
