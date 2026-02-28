import json
import os
import sys

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, inr, fmt_inr, api_get, api_post, BACKEND_URL, CHART_LAYOUT, COLORS

st.set_page_config(page_title="TaxIQ | Tax Saver", page_icon="📊", layout="wide")
inject_css()

st.markdown('<div class="page-title">📊 Personal Tax Saver Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Bank CSV → classification → 80C/80D gaps → Old vs New regime → PDF report</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([0.35, 0.2, 0.15, 0.3], gap="large")

with col1:
    csv_file = st.file_uploader("Upload bank statement CSV", type=["csv"])
with col2:
    income = st.number_input("Annual income (₹)", value=800000, step=50000)
with col3:
    age = st.number_input("Age", value=30, step=1)
with col4:
    has_parents = st.checkbox("Has senior citizen parents?", value=False)

analyze = st.button("Analyze My Taxes", use_container_width=True, type="primary", disabled=csv_file is None)

if analyze and csv_file is not None:
    with st.spinner("Analyzing transactions, computing gaps, comparing regimes…"):
        try:
            with httpx.Client(timeout=180) as client:
                res = client.post(
                    f"{BACKEND_URL}/tax/analyze",
                    files={"file": (csv_file.name, csv_file.getvalue(), "text/csv")},
                    data={"annual_income": str(income), "age": str(int(age)), "has_senior_parents": str(has_parents).lower(), "name": "User"},
                )
            if res.status_code != 200:
                st.error(res.text)
            else:
                st.session_state["tax_analysis"] = res.json()
        except Exception as e:
            st.error(f"Backend not reachable or error occurred: {e}")


analysis = st.session_state.get("tax_analysis")
if not analysis:
    st.info("Upload the provided sample CSV at `data/sample_bank_statements/bank_statement.csv` and click **Analyze My Taxes**.")
    st.stop()


rc = analysis["regime_comparison"]
row1 = st.columns(2, gap="large")
with row1[0]:
    st.metric("Old Regime Tax (FY2024-25)", inr(rc["old_regime_tax"]))
with row1[1]:
    st.metric("New Regime Tax (FY2024-25)", inr(rc["new_regime_tax"]))

best = rc["best_regime"]
sav = rc["savings"]
st.success(f"You save {inr(sav)} with the **{best} regime**!")


st.divider()
st.markdown("### Investment Gap Chart")

sections = analysis["gap_report"]["sections"]
labels = list(sections.keys())
invested = [sections[s]["current_investment"] for s in labels]
gap = [sections[s]["gap"] if isinstance(sections[s]["limit"], (int, float)) else 0 for s in labels]

fig = go.Figure()
fig.add_trace(go.Bar(y=labels, x=invested, name="Invested", orientation="h", marker_color="#00B894"))
fig.add_trace(go.Bar(y=labels, x=gap, name="Gap Remaining", orientation="h", marker_color="#FF3B5C"))
fig.update_layout(
    **CHART_LAYOUT,
    barmode="stack",
    height=360,
)
st.plotly_chart(fig, use_container_width=True)


st.divider()
st.markdown("### AI Recommendations")
advice = analysis.get("ai_advice", "")
if "[DEMO DATA]" in advice:
    st.warning(advice)
else:
    st.info(advice)


st.divider()
st.markdown("### Action Items (sorted by tax saving)")
items = analysis.get("action_items", [])
st.dataframe(items, use_container_width=True)


st.divider()
st.markdown("### Download Full Tax Report PDF")
if st.button("Generate PDF", use_container_width=True):
    with st.spinner("Generating PDF…"):
        with httpx.Client(timeout=120) as client:
            pdf_res = client.post(f"{BACKEND_URL}/tax/report-pdf", json=analysis)
        if pdf_res.status_code != 200:
            st.error(pdf_res.text)
        else:
            st.download_button(
                "Download TaxIQ Report (PDF)",
                data=pdf_res.content,
                file_name="taxiq_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


# ── 💡 Hidden Deductions from GST Data ─────────────────
st.divider()
st.markdown("### 💡 Hidden Deductions from Your GST Data")
st.caption("Cross-layer intelligence: TaxIQ scans your GST invoices to find ITR deductions you may have missed.")

try:
    with httpx.Client(timeout=30) as client:
        enrichment_res = client.post(
            f"{BACKEND_URL}/api/tax/enrichment",
            json={"invoices": analysis.get("classified_txns", [])},
        )
    if enrichment_res.status_code == 200:
        hidden = enrichment_res.json().get("deductions", [])
    else:
        hidden = []
        st.warning(f"Enrichment API returned HTTP {enrichment_res.status_code}")
except Exception as e:
    hidden = []
    st.warning(f"Could not reach enrichment API: {e}")

total_hidden = sum(d.get("estimated_tax_saved", 0) for d in hidden)
st.metric("Total Hidden Tax Savings Found", inr(total_hidden))

for d in hidden:
    with st.expander(f"🔍 {d.get('section', '')} — {d.get('vendor', '')} — Save {inr(d.get('estimated_tax_saved', 0))}"):
        c1, c2 = st.columns(2)
        c1.markdown(f"**Invoice:** {d.get('invoice', '')}")
        c1.markdown(f"**HSN Code:** {d.get('hsn', '')}")
        c2.markdown(f"**Section:** {d.get('section', '')}")
        c2.markdown(f"**Invoice Amount:** {inr(d.get('invoice_amount', 0))}")
        st.info(f"💡 {d.get('description', '')}")


# ── 📅 Investment Calendar ──────────────────────────────
st.divider()
st.markdown("### 📅 Your Investment Calendar")
st.caption("Month-by-month plan to fill all 80C/80D gaps before March 31.")

try:
    with httpx.Client(timeout=30) as client:
        cal_res = client.post(
            f"{BACKEND_URL}/api/tax/calendar",
            json={"gap_report": analysis.get("gap_report", {})},
        )
    if cal_res.status_code == 200:
        calendar = cal_res.json()
    else:
        calendar = {"monthly_plan": [], "summary": {}}
        st.warning(f"Calendar API returned HTTP {cal_res.status_code}")
except Exception as e:
    calendar = {"monthly_plan": [], "summary": {}}
    st.warning(f"Could not reach calendar API: {e}")

summary = calendar.get("summary", {})
s1, s2, s3 = st.columns(3)
s1.metric("Total to Invest", inr(summary.get("total_to_invest", 0)))
s2.metric("Tax Saved", inr(summary.get("total_tax_saved", 0)))
s3.metric("Monthly Average", inr(summary.get("monthly_average", 0)))

# Gantt-style bar chart
plan = calendar.get("monthly_plan", [])
section_colors = {"80C": "#FF9933", "80D": "#00B894", "80CCD": "#FDCB6E",
                  "24(b)": "#74B9FF", "80E": "#A29BFE", "80G": "#FD79A8"}

fig_cal = go.Figure()
for entry in plan:
    month = entry.get("month", "")
    for inv in entry.get("investments", []):
        sec = inv.get("section", "Other")
        fig_cal.add_trace(go.Bar(
            y=[month], x=[inv.get("amount", 0)],
            name=f"{sec} — {inv.get('instrument', '')}",
            orientation="h",
            marker_color=section_colors.get(sec, "#636E72"),
            text=f"₹{inv.get('amount', 0):,} · {inv.get('instrument', '')}",
            textposition="inside",
        ))

fig_cal.update_layout(
    **CHART_LAYOUT,
    barmode="stack",
    height=250,
    showlegend=False,
    xaxis_title="Amount (₹)",
)
st.plotly_chart(fig_cal, use_container_width=True)

# Monthly expanders
for entry in plan:
    month = entry.get("month", "")
    investments = entry.get("investments", [])
    total = sum(i.get("amount", 0) for i in investments)
    with st.expander(f"📅 {month} — Invest {inr(total)}"):
        for inv in investments:
            priority = inv.get("priority", "MEDIUM")
            badge = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(priority, "⚪")
            st.markdown(
                f"{badge} **{inv.get('section', '')}** — {inv.get('instrument', '')} "
                f"— **{inr(inv.get('amount', 0))}** (Priority: {priority})"
            )

