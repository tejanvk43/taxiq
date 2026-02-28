"""
TaxIQ — 🔄 GSTR Reconciliation Engine
Compare GSTR-1 (supplier filed) vs GSTR-2B (buyer sees) — catch mismatches before filing.
"""
import json
import os
import sys

import httpx
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, fmt_inr, api_get, api_post, BACKEND_URL, CHART_LAYOUT, COLORS

st.set_page_config(page_title="TaxIQ | Reconciliation", page_icon="🔄", layout="wide")
inject_css()


MISMATCH_LABELS = {
    "TYPE_1": "Invoice Missing in GSTR-2B",
    "TYPE_2": "Taxable Value Mismatch",
    "TYPE_3": "Tax Rate Mismatch",
    "TYPE_4": "GSTIN Mismatch",
    "TYPE_5": "Period Mismatch",
}

# ── Header ──────────────────────────────────────────────
st.markdown('<div class="page-title">🔄 GSTR Reconciliation Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Compare GSTR-1 (supplier filed) vs GSTR-2B (buyer sees) — catch mismatches before filing</div>', unsafe_allow_html=True)

# ── Input Row ───────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    gstin = st.text_input("Supplier GSTIN", value="27AADCB2230M1ZT")
with col2:
    period = st.selectbox("Period", [
        "Jan 2024", "Feb 2024", "Mar 2024",
        "Oct 2024", "Nov 2024", "Dec 2024",
    ], index=3)
with col3:
    st.write("")
    st.write("")
    run_btn = st.button("🔍 Run Reconciliation", use_container_width=True, type="primary")

# ── Run reconciliation ──────────────────────────────────
if run_btn:
    with st.spinner("Running multi-hop graph traversal..."):
        try:
            r = api_post("/api/reconcile/run", json_body={"gstin": gstin, "period": period})
            if r.status_code == 200:
                st.session_state["recon_result"] = r.json()
            else:
                st.error(f"Reconciliation failed: HTTP {r.status_code} — {r.text[:200]}")
        except Exception as e:
            st.error(f"Backend not reachable: {e}")

# ── Display results ─────────────────────────────────────
result = st.session_state.get("recon_result")
if not result:
    st.info("Enter a GSTIN and click **Run Reconciliation** to start.")
    st.stop()

st.divider()

# ── Row 1: Metric Cards ────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
total_inv = result.get("total_invoices_checked", 0)
itc_risk = result.get("total_itc_at_risk", 0)
score = result.get("reconciliation_score", 0)
mm_count = len(result.get("mismatches", []))

m1.metric("Total Invoices Checked", total_inv)
m2.metric("ITC At Risk", fmt_inr(itc_risk), delta=f"-{fmt_inr(itc_risk)}" if itc_risk > 0 else "0",
          delta_color="inverse")
score_color = "🟢" if score > 90 else "🟡" if score > 70 else "🔴"
m3.metric("Reconciliation Score", f"{score_color} {score}%")
m4.metric("Mismatches Found", mm_count)

st.divider()

# ── Row 2: Mismatch Type Bar Chart ─────────────────────
st.markdown("### Mismatches by Type")
breakdown = result.get("mismatch_breakdown", {})
if not breakdown:
    # Build from mismatches list
    for mm in result.get("mismatches", []):
        label = MISMATCH_LABELS.get(mm.get("mismatchType", ""), mm.get("mismatchType", ""))
        breakdown[label] = breakdown.get(label, 0) + 1

types = list(breakdown.keys())
counts = list(breakdown.values())

# Color by risk summary
risk = result.get("risk_summary", {})
colors = []
for t in types:
    c = counts[types.index(t)]
    if c >= 3:
        colors.append("#D63031")  # crimson
    elif c >= 1:
        colors.append("#FDCB6E")  # amber
    else:
        colors.append("#00B894")  # emerald

fig_bar = go.Figure(go.Bar(
    y=types,
    x=counts,
    orientation="h",
    marker_color=colors,
    text=counts,
    textposition="auto",
))
fig_bar.update_layout(
    **CHART_LAYOUT,
    height=280,
    xaxis_title="Count",
)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ── Row 3: Mismatch Detail Table ───────────────────────
st.markdown("### Mismatch Details")
mismatches = result.get("mismatches", [])
if mismatches:
    import pandas as pd
    rows = []
    for mm in mismatches:
        risk_badge = {"HIGH": "🔴 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🟢 LOW", "CRITICAL": "🔴 CRITICAL"}
        rows.append({
            "Invoice No": mm.get("invoiceId", ""),
            "Type": MISMATCH_LABELS.get(mm.get("mismatchType", ""), mm.get("mismatchType", "")),
            "Supplier Amount": fmt_inr(mm.get("supplierAmount", 0) or 0),
            "Buyer Amount": fmt_inr(mm.get("buyerAmount", 0) or 0),
            "Difference": fmt_inr(mm.get("difference", 0) or 0),
            "Risk Level": risk_badge.get(mm.get("riskLevel", "LOW"), mm.get("riskLevel", "")),
            "Status": "Open",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.success("No mismatches found! All invoices reconciled ✅")

st.divider()

# ── Row 4: Audit Trail ─────────────────────────────────
st.markdown("### Audit Trail")
audit = result.get("audit_trail", [])
for i, mm in enumerate(mismatches):
    inv_id = mm.get("invoiceId", f"Invoice {i+1}")
    mm_type = MISMATCH_LABELS.get(mm.get("mismatchType", ""), mm.get("mismatchType", ""))
    risk_amt = mm.get("amount", 0)
    with st.expander(f"{inv_id} — {mm_type} — {fmt_inr(risk_amt)} at risk"):
        trail_text = audit[i] if i < len(audit) else mm.get("detail", "No details available.")
        st.write(trail_text)
        if st.button(f"📋 Copy for CA", key=f"copy_{i}"):
            st.code(trail_text, language=None)
            st.toast("Text ready to copy!", icon="📋")

st.divider()

# ── Download Audit Report ───────────────────────────────
report_text = f"TaxIQ GSTR Reconciliation Audit Report\n{'='*50}\n"
report_text += f"GSTIN: {result.get('gstin', gstin)}\n"
report_text += f"Period: {result.get('period', period)}\n"
report_text += f"Reconciliation Score: {score}%\n"
report_text += f"Total ITC at Risk: {fmt_inr(itc_risk)}\n"
report_text += f"Mismatches: {mm_count}\n\n"
for i, trail in enumerate(audit):
    report_text += f"{i+1}. {trail}\n\n"

st.download_button(
    "📥 Download Full Audit Report",
    data=report_text,
    file_name=f"recon_audit_{gstin}_{period.replace(' ', '_')}.txt",
    mime="text/plain",
    use_container_width=True,
)

st.caption("Powered by NEXUS Reconciliation Engine · Rule 36(4) · CGST Act 2017 · TaxIQ")
