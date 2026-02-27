"""
TaxIQ — 🏢 NEXUS Vendor Scores
Scorecard grid with radar charts, loan eligibility, compliance bars, and drill-down history.
"""

import os
import json

import httpx
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="TaxIQ | Vendor Scores", page_icon="🏢", layout="wide")

BACKEND = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")

# ── Dark theme CSS ──────────────────────────────────────
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
.grade-big {
  font-size: 48px; font-weight: 800; text-align: center; line-height: 1.1;
}
.grade-green { color: #00CC66; }
.grade-yellow { color: #FFB800; }
.grade-red { color: #FF4444; }
</style>
""", unsafe_allow_html=True)


def inr(x) -> str:
    try:
        n = int(round(float(x)))
    except Exception:
        return f"₹{x}"
    s = str(abs(n))
    if len(s) <= 3:
        out = s
    else:
        out = s[-3:]
        s = s[:-3]
        while s:
            out = s[-2:] + "," + out
            s = s[:-2]
    return ("-₹" if n < 0 else "₹") + out


def api_get(path):
    with httpx.Client(timeout=30) as c:
        return c.get(f"{BACKEND}{path}")


def grade_color(grade: str) -> str:
    if grade in ("AAA", "AA+", "AA", "A+", "A"):
        return "grade-green"
    elif grade in ("BBB", "BB", "B"):
        return "grade-yellow"
    return "grade-red"


def grade_emoji(grade: str) -> str:
    if grade in ("AAA", "AA+", "AA", "A+", "A"):
        return "🟢"
    elif grade in ("BBB", "BB", "B"):
        return "🟡"
    return "🔴"


def make_radar(v: dict) -> go.Figure:
    """Create 5-factor radar chart for a vendor."""
    cats = ["Filing Rate", "GSTR-2B\nReflect.", "ITC\nAccuracy", "Network\nRisk", "E-Way\nCompliance"]
    vals = [
        v.get("filingRate", 0),
        v.get("gstr2bReflectance", 0),
        v.get("itcAccuracy", 0),
        v.get("networkRisk", 0),
        v.get("ewayCompliance", 0),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=cats + [cats[0]],
        fill="toself",
        fillcolor="rgba(255,153,51,0.15)",
        line=dict(color="#FF9933", width=2),
        marker=dict(size=6, color="#FF9933"),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#0E1F3E",
            radialaxis=dict(range=[0, 100], showticklabels=True, tickfont=dict(size=9, color="#888"), gridcolor="#1A2E50"),
            angularaxis=dict(tickfont=dict(size=10, color="#CCC"), gridcolor="#1A2E50"),
        ),
        paper_bgcolor="#0A1628",
        font_color="#E0E0E0",
        height=280,
        margin=dict(l=50, r=50, t=20, b=30),
        showlegend=False,
    )
    return fig


# ── Demo fallback ───────────────────────────────────────
DEMO_VENDORS = [
    {"gstin": "19AABCG1234Q1Z2", "nexusScore": 18, "grade": "D", "filingRate": 42, "gstr2bReflectance": 31, "itcAccuracy": 25, "networkRisk": 22, "ewayCompliance": 44, "trend": "DOWN", "lastUpdated": "2024-02-12T10:00:00Z", "loanEligible": False, "loanLimit": 0, "creditRating": "D", "loanOfferApr": None, "loanTenorMonths": None},
    {"gstin": "27AAACF9999K1Z9", "nexusScore": 52, "grade": "BB", "filingRate": 86, "gstr2bReflectance": 74, "itcAccuracy": 63, "networkRisk": 55, "ewayCompliance": 68, "trend": "FLAT", "lastUpdated": "2024-02-12T10:00:00Z", "loanEligible": False, "loanLimit": 0, "creditRating": "BB", "loanOfferApr": None, "loanTenorMonths": None},
    {"gstin": "07AABCS7777H1Z1", "nexusScore": 33, "grade": "CCC", "filingRate": 55, "gstr2bReflectance": 48, "itcAccuracy": 41, "networkRisk": 38, "ewayCompliance": 52, "trend": "DOWN", "lastUpdated": "2024-02-12T10:00:00Z", "loanEligible": False, "loanLimit": 0, "creditRating": "CCC", "loanOfferApr": None, "loanTenorMonths": None},
]

# ── Header ──────────────────────────────────────────────
st.markdown("## 🏢 NEXUS Vendor Scores")
st.caption("Vendor compliance scoring powered by 5-factor NEXUS algorithm. Grades from AAA to D. OCEN lending eligibility.")

st.divider()

# ── Load all vendors ────────────────────────────────────
load_btn = st.button("📥 Load All Vendors", type="primary", use_container_width=False)

if load_btn:
    with st.spinner("Loading vendor scores…"):
        try:
            r = api_get("/api/vendors/list")
            if r.status_code == 200:
                body = r.json()
                vendors = body.get("vendors", body.get("items", []))
                st.session_state["vendor_list"] = vendors
                st.session_state["vendor_demo"] = False
            else:
                raise Exception(f"HTTP {r.status_code}")
        except Exception:
            st.session_state["vendor_list"] = DEMO_VENDORS
            st.session_state["vendor_demo"] = True

if "vendor_list" in st.session_state:
    vendors = st.session_state["vendor_list"]
    is_demo = st.session_state.get("vendor_demo", False)

    if is_demo:
        st.markdown('<span class="demo-badge">[DEMO]</span>', unsafe_allow_html=True)

    if not vendors:
        st.info("No vendor data available.")
    else:
        # ── Scorecard grid ──────────────────────────────
        st.markdown("### Vendor Scorecard Grid")
        cols = st.columns(min(len(vendors), 3))
        for i, v in enumerate(vendors):
            with cols[i % len(cols)]:
                grade = v.get("grade", "?")
                score = v.get("nexusScore", 0)
                gstin_v = v.get("gstin", "?")
                trend = v.get("trend", "FLAT")
                trend_icon = {"UP": "📈", "DOWN": "📉", "FLAT": "➡️"}.get(trend, "➡️")
                loan = v.get("loanEligible", False)

                # Grade badge
                st.markdown(f'<div class="grade-big {grade_color(grade)}">{grade}</div>', unsafe_allow_html=True)
                st.markdown(f"**Score: {score}/100** {trend_icon}")
                st.caption(f"GSTIN: {gstin_v}")

                # Compliance progress bar
                st.progress(min(score / 100, 1.0))

                # Loan badge
                if loan:
                    st.success(f"✅ Loan eligible — {inr(v.get('loanLimit', 0))}")
                else:
                    st.error("❌ Not eligible for lending")

                # Radar chart
                st.plotly_chart(make_radar(v), use_container_width=True, key=f"radar_{gstin_v}")

                st.divider()

        # ── Drill-down section ──────────────────────────
        st.divider()
        st.markdown("### 🔎 Vendor Drill-Down")
        drill_gstin = st.selectbox(
            "Select vendor to inspect",
            [v.get("gstin", "?") for v in vendors],
        )

        if st.button("Load Details", key="drill_btn"):
            selected = next((v for v in vendors if v.get("gstin") == drill_gstin), None)

            if selected:
                st.markdown(f"#### {grade_emoji(selected.get('grade', '?'))} {drill_gstin} — Grade **{selected.get('grade', '?')}**")

                dcols = st.columns(5)
                dcols[0].metric("Filing Rate", f"{selected.get('filingRate', 0)}%")
                dcols[1].metric("GSTR-2B Reflect.", f"{selected.get('gstr2bReflectance', 0)}%")
                dcols[2].metric("ITC Accuracy", f"{selected.get('itcAccuracy', 0)}%")
                dcols[3].metric("Network Risk", f"{selected.get('networkRisk', 0)}")
                dcols[4].metric("E-Way Compliance", f"{selected.get('ewayCompliance', 0)}%")

                # Loan section
                st.divider()
                st.markdown("#### 🏦 OCEN Lending Widget")
                if selected.get("loanEligible"):
                    lcols = st.columns(4)
                    lcols[0].metric("Loan Limit", inr(selected.get("loanLimit", 0)))
                    lcols[1].metric("Credit Rating", selected.get("creditRating", "—"))
                    lcols[2].metric("APR", f"{selected.get('loanOfferApr', 0):.1f}%")
                    lcols[3].metric("Tenor", f"{selected.get('loanTenorMonths', 0)} months")
                else:
                    st.warning("Not eligible. Improve filing rate (≥90%) and NEXUS score (≥75) to unlock working-capital loans.")

                # Score history
                st.divider()
                st.markdown("#### 📈 Score History")
                with st.spinner("Loading history…"):
                    try:
                        hr = api_get(f"/api/vendors/{drill_gstin}/history?months=12")
                        if hr.status_code == 200:
                            hist = hr.json().get("history", [])
                        else:
                            raise Exception()
                    except Exception:
                        hist = [{"monthOffset": i, "score": max(5, selected.get("nexusScore", 50) - i * 2)} for i in range(12)]

                if hist:
                    months = [f"M-{h['monthOffset']}" for h in reversed(hist)]
                    scores = [h["score"] for h in reversed(hist)]
                    fig = go.Figure(go.Scatter(
                        x=months, y=scores,
                        mode="lines+markers",
                        line=dict(color="#FF9933", width=3),
                        marker=dict(size=8, color="#FF9933"),
                        fill="tozeroy",
                        fillcolor="rgba(255,153,51,0.1)",
                    ))
                    fig.update_layout(
                        plot_bgcolor="#0A1628", paper_bgcolor="#0A1628",
                        font_color="#E0E0E0",
                        xaxis_title="Month", yaxis_title="NEXUS Score",
                        yaxis=dict(range=[0, 100]),
                        height=300, margin=dict(l=40, r=20, t=20, b=50),
                    )
                    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("Powered by NEXUS 5-Factor Scoring · OCEN Lending Protocol · TaxIQ")
