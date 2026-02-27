import json
import os

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


BACKEND_URL = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")


def inr(x: float) -> str:
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


st.markdown("## 📊 Personal Tax Saver Agent")
st.caption("Bank CSV → classification → 80C/80D gaps → Old vs New regime → PDF report")

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
    barmode="stack",
    template="plotly_dark",
    height=360,
    margin=dict(l=20, r=20, t=10, b=20),
    paper_bgcolor="#0A1628",
    plot_bgcolor="#0A1628",
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

