"""
TaxIQ — 🏢 NEXUS Vendor Compliance Scores
5-factor AI scoring → AAA to D grades → OCEN loan eligibility.
"""
import os
import sys

import httpx
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, fmt_inr, api_get, BACKEND_URL, CHART_LAYOUT, COLORS

st.set_page_config(page_title="TaxIQ | Vendor Scores", page_icon="🏢", layout="wide")
inject_css()


def grade_css(grade: str) -> str:
    g = grade.upper()
    if g in ("AAA", "AA"): return "grade-aaa"
    if g in ("A", "BBB"): return "grade-a"
    if g in ("BB", "B"): return "grade-b"
    return "grade-d"


def grade_color(grade: str) -> str:
    g = grade.upper()
    if g in ("AAA", "AA"): return COLORS["green"]
    if g in ("A", "BBB"): return COLORS["yellow"]
    if g in ("BB", "B"): return COLORS["accent"]
    return COLORS["red"]


# ── Header ──────────────────────────────────────────────
st.markdown('<div class="page-title">🏢 NEXUS Vendor Compliance Scores</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">5-factor AI scoring → AAA to D grades → OCEN loan eligibility</div>', unsafe_allow_html=True)

# ── Load vendors ────────────────────────────────────────
load_btn = st.button("📥 Load All Vendors", use_container_width=True, type="primary")

if load_btn:
    with st.spinner("Fetching vendor network..."):
        try:
            r = api_get("/api/vendors/list")
            if r.status_code == 200:
                data = r.json()
                st.session_state["vendors"] = data.get("vendors", data if isinstance(data, list) else [])
            else:
                st.error(f"Backend returned HTTP {r.status_code}")
        except Exception as e:
            st.error(f"Could not reach backend: {e}")

if "vendors" not in st.session_state:
    st.session_state["vendors"] = []

vendors = st.session_state["vendors"]

if not vendors:
    st.info("Click **Load All Vendors** to fetch vendor scores from the backend.")

st.divider()

# ── Top Metrics ─────────────────────────────────────────
total_v = len(vendors)
high_risk = sum(1 for v in vendors if v.get("nexusScore", 0) < 40)
avg_score = sum(v.get("nexusScore", 0) for v in vendors) / total_v if total_v else 0

t1, t2, t3 = st.columns(3)
t1.metric("Vendors Monitored", total_v)
t2.metric("High Risk Vendors", high_risk, delta=f"{high_risk} flagged", delta_color="inverse")
t3.metric("Avg Compliance Score", f"{avg_score:.0f}/100")

st.divider()

# ── Vendor Grid ─────────────────────────────────────────
st.markdown("### Vendor Scorecard Grid")
cols_per_row = 3
for row_start in range(0, len(vendors), cols_per_row):
    cols = st.columns(cols_per_row)
    for i, col in enumerate(cols):
        idx = row_start + i
        if idx >= len(vendors):
            break
        v = vendors[idx]
        with col:
            with st.container():
                grade = v.get("nexusGrade", v.get("grade", "D"))
                css = grade_css(grade)
                st.markdown(f'NEXUS Grade: <span class="{css}">{grade}</span>', unsafe_allow_html=True)
                st.markdown(f"**{v.get('name', v.get('gstin', ''))}**")
                st.caption(f"GSTIN: {v.get('gstin', '')}")
                st.divider()

                # Radar chart
                factors = v.get("factors", {})
                if factors:
                    cats = ["Filing", "ITC Accuracy", "Turnover", "Network", "Amendments"]
                    vals = [
                        factors.get("filing_regularity", 50),
                        factors.get("itc_accuracy", 50),
                        factors.get("turnover_consistency", 50),
                        factors.get("network_trustworthiness", 50),
                        factors.get("amendment_frequency", 50),
                    ]
                    fig = go.Figure(go.Scatterpolar(
                        r=vals + [vals[0]],
                        theta=cats + [cats[0]],
                        fill="toself",
                        fillcolor=f"rgba({','.join(str(int(grade_color(grade).lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.2)",
                        line_color=grade_color(grade),
                    ))
                    fig.update_layout(
                        **CHART_LAYOUT,
                        polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False)),
                        showlegend=False,
                        height=200,
                        margin=dict(l=30, r=30, t=10, b=10),
                        font=dict(size=10, color="#F8F9FA"),
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"radar_{idx}")

                st.divider()
                score = v.get("nexusScore", v.get("complianceScore", 0))
                st.progress(min(score / 100, 1.0), text=f"Compliance: {score}%")
                loan = v.get("loanEligible", False)
                st.markdown(f"Loan Eligible: {'✅ Yes' if loan else '❌ No'}")

st.divider()

# ── Drill-Down Section ──────────────────────────────────
st.markdown("### 🔍 Vendor Deep Analysis")
vendor_names = [f"{v.get('name', '')} ({v.get('gstin', '')})" for v in vendors]
selected = st.selectbox("Select vendor for deep analysis", vendor_names)

if selected:
    sel_idx = vendor_names.index(selected)
    v = vendors[sel_idx]
    gstin_sel = v.get("gstin", "")

    # Try to fetch detailed score
    detail = v
    try:
        r = api_get(f"/api/vendors/score/{gstin_sel}")
        if r.status_code == 200:
            detail = {**v, **r.json()}
    except Exception:
        pass

    left, right = st.columns(2)

    with left:
        st.markdown("#### Score Breakdown")
        factors = detail.get("factors", {})
        import pandas as pd

        weights = {"filing_regularity": 0.25, "itc_accuracy": 0.25,
                   "turnover_consistency": 0.20, "network_trustworthiness": 0.20,
                   "amendment_frequency": 0.10}
        rows = []
        for k, w in weights.items():
            s = factors.get(k, 50)
            rows.append({
                "Factor": k.replace("_", " ").title(),
                "Score": s,
                "Weight": f"{w*100:.0f}%",
                "Contribution": round(s * w, 1),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with right:
        st.markdown("#### Score History (Last 6 Months)")
        hist = []
        try:
            r = api_get(f"/api/vendors/{gstin_sel}/history")
            if r.status_code == 200:
                hist = r.json().get("history", [])
        except Exception:
            pass

        months = [h.get("month", "") for h in hist]
        scores = [h.get("score", 0) for h in hist]
        fig_line = go.Figure(go.Scatter(
            x=months, y=scores,
            mode="lines+markers",
            line=dict(color="#FF9933", width=3),
            marker=dict(size=8),
        ))
        fig_line.update_layout(
            **CHART_LAYOUT,
            height=250,
            yaxis=dict(range=[0, 100]),
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # NEXUS explanation
    grade = detail.get("nexusGrade", detail.get("grade", "D"))
    top_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
    pos = [f.replace("_", " ") for f, _ in top_factors[:2]]
    neg = top_factors[-1][0].replace("_", " ") if top_factors else "unknown"
    st.info(
        f"This vendor scores **{grade}** because of strong {pos[0]} and {pos[1]}. "
        f"Main risk: weak {neg}. "
        f"Recommendation: {'Continue partnership.' if factors.get('filing_regularity', 0) > 70 else 'Monitor closely and require bank guarantees.'}"
    )

    # Loan Eligibility
    loan = detail.get("loanEligible", False)
    limit = detail.get("loanLimit", 0)
    if loan:
        st.success(f"✅ **OCEN Loan Eligible** — Estimated limit: {fmt_inr(limit)} based on turnover and compliance score")
    else:
        reason = "Filing regularity below 60%" if factors.get("filing_regularity", 0) < 60 else "Overall NEXUS score below threshold"
        st.error(f"❌ **Not eligible for OCEN lending** — {reason}")

st.caption("Powered by NEXUS 5-Factor Scoring · OCEN Protocol · TaxIQ")
