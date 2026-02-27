"""
TaxIQ — 🏢 NEXUS Vendor Compliance Scores
5-factor AI scoring → AAA to D grades → OCEN loan eligibility.
"""
import os

import httpx
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="TaxIQ | Vendor Scores", page_icon="🏢", layout="wide")

BACKEND = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")

# ── Design System CSS ───────────────────────────────────
st.markdown("""<style>
    .stApp { background-color: #0A1628; color: #F8F9FA; }
    .stMetric { background: #0D1F3C; border-radius: 12px;
                padding: 16px; border-left: 4px solid #FF9933; }
    .stButton>button { background: #FF9933; color: #0A1628;
                       font-weight: 700; border-radius: 8px;
                       border: none; }
    .stDataFrame { background: #0D1F3C; }
    div[data-testid="metric-container"] {
      background: #0D1F3C; border-radius: 10px; padding: 10px; }
    .demo-badge {
      display:inline-block; padding:2px 10px; border-radius:999px;
      background:rgba(253,203,110,.15); border:1px solid #FDCB6E;
      color:#FDCB6E; font-size:12px; font-weight:600; }
    .grade-aaa { background:#00B894; color:#0A1628; padding:4px 12px;
                 border-radius:6px; font-weight:700; font-size:18px; }
    .grade-a   { background:#FDCB6E; color:#0A1628; padding:4px 12px;
                 border-radius:6px; font-weight:700; font-size:18px; }
    .grade-b   { background:#FF9933; color:#0A1628; padding:4px 12px;
                 border-radius:6px; font-weight:700; font-size:18px; }
    .grade-d   { background:#D63031; color:#F8F9FA; padding:4px 12px;
                 border-radius:6px; font-weight:700; font-size:18px; }
</style>""", unsafe_allow_html=True)


def fmt_inr(n):
    if n >= 1e7: return f"₹{n/1e7:.1f}Cr"
    if n >= 1e5: return f"₹{n/1e5:.1f}L"
    return f"₹{n:,.0f}"


def api_get(path, params=None):
    with httpx.Client(timeout=30) as c:
        return c.get(f"{BACKEND}{path}", params=params)


def grade_css(grade: str) -> str:
    g = grade.upper()
    if g in ("AAA", "AA"): return "grade-aaa"
    if g in ("A", "BBB"): return "grade-a"
    if g in ("BB", "B"): return "grade-b"
    return "grade-d"


def grade_color(grade: str) -> str:
    g = grade.upper()
    if g in ("AAA", "AA"): return "#00B894"
    if g in ("A", "BBB"): return "#FDCB6E"
    if g in ("BB", "B"): return "#FF9933"
    return "#D63031"


# ── DEMO DATA ──────────────────────────────────────────
DEMO_VENDORS = [
    {
        "gstin": "27AAACF9999K1Z9", "name": "Falcon Components Pvt Ltd",
        "nexusGrade": "AA", "nexusScore": 82, "complianceScore": 88,
        "loanEligible": True, "loanLimit": 2500000,
        "factors": {"filing_regularity": 90, "itc_accuracy": 85, "turnover_consistency": 78,
                    "network_trustworthiness": 80, "amendment_frequency": 92},
    },
    {
        "gstin": "29AAACN0001A1Z5", "name": "Nexus Demo Manufacturing",
        "nexusGrade": "AAA", "nexusScore": 91, "complianceScore": 95,
        "loanEligible": True, "loanLimit": 5000000,
        "factors": {"filing_regularity": 95, "itc_accuracy": 92, "turnover_consistency": 88,
                    "network_trustworthiness": 90, "amendment_frequency": 96},
    },
    {
        "gstin": "19AABCG1234Q1Z2", "name": "GoldStar Traders",
        "nexusGrade": "D", "nexusScore": 18, "complianceScore": 22,
        "loanEligible": False, "loanLimit": 0,
        "factors": {"filing_regularity": 15, "itc_accuracy": 20, "turnover_consistency": 12,
                    "network_trustworthiness": 25, "amendment_frequency": 18},
    },
    {
        "gstin": "07AABCS7777H1Z1", "name": "Shadow Supplies Delhi",
        "nexusGrade": "B", "nexusScore": 38, "complianceScore": 42,
        "loanEligible": False, "loanLimit": 0,
        "factors": {"filing_regularity": 45, "itc_accuracy": 30, "turnover_consistency": 35,
                    "network_trustworthiness": 40, "amendment_frequency": 50},
    },
    {
        "gstin": "24ABCPD6789Q1ZN", "name": "Patel Chemicals Gujarat",
        "nexusGrade": "A", "nexusScore": 72, "complianceScore": 76,
        "loanEligible": True, "loanLimit": 1500000,
        "factors": {"filing_regularity": 80, "itc_accuracy": 68, "turnover_consistency": 70,
                    "network_trustworthiness": 72, "amendment_frequency": 75},
    },
    {
        "gstin": "33ABDCK3456N1ZT", "name": "Kumar Traders Chennai",
        "nexusGrade": "BBB", "nexusScore": 65, "complianceScore": 68,
        "loanEligible": True, "loanLimit": 800000,
        "factors": {"filing_regularity": 70, "itc_accuracy": 62, "turnover_consistency": 60,
                    "network_trustworthiness": 68, "amendment_frequency": 65},
    },
]

DEMO_HISTORY = [
    {"month": "Jul '24", "score": 75},
    {"month": "Aug '24", "score": 78},
    {"month": "Sep '24", "score": 76},
    {"month": "Oct '24", "score": 80},
    {"month": "Nov '24", "score": 82},
    {"month": "Dec '24", "score": 85},
]


# ── Header ──────────────────────────────────────────────
st.title("🏢 NEXUS Vendor Compliance Scores")
st.caption("5-factor AI scoring → AAA to D grades → OCEN loan eligibility")

# ── Load vendors ────────────────────────────────────────
load_btn = st.button("📥 Load All Vendors", use_container_width=True, type="primary")

if load_btn:
    with st.spinner("Fetching vendor network..."):
        try:
            r = api_get("/api/vendors/list")
            if r.status_code == 200:
                data = r.json()
                st.session_state["vendors"] = data.get("vendors", data if isinstance(data, list) else [])
                st.session_state["vendors_demo"] = False
            else:
                raise Exception(f"HTTP {r.status_code}")
        except Exception:
            st.session_state["vendors"] = DEMO_VENDORS
            st.session_state["vendors_demo"] = True

if "vendors" not in st.session_state:
    st.session_state["vendors"] = DEMO_VENDORS
    st.session_state["vendors_demo"] = True

vendors = st.session_state["vendors"]
is_demo = st.session_state.get("vendors_demo", False)

if is_demo:
    st.markdown('<span class="demo-badge">[DEMO DATA]</span>', unsafe_allow_html=True)

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
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
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
        try:
            r = api_get(f"/api/vendors/{gstin_sel}/history")
            if r.status_code == 200:
                hist = r.json().get("history", DEMO_HISTORY)
            else:
                hist = DEMO_HISTORY
        except Exception:
            hist = DEMO_HISTORY

        months = [h.get("month", "") for h in hist]
        scores = [h.get("score", 0) for h in hist]
        fig_line = go.Figure(go.Scatter(
            x=months, y=scores,
            mode="lines+markers",
            line=dict(color="#FF9933", width=3),
            marker=dict(size=8),
        ))
        fig_line.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0A1628",
            plot_bgcolor="#0D1F3C",
            font_color="#F8F9FA",
            height=250,
            margin=dict(l=20, r=20, t=10, b=10),
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
