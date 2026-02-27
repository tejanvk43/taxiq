"""
TaxIQ — 🔄 GSTR Reconciliation Engine
Compare GSTR-1 (supplier filed) vs GSTR-2B (buyer sees) — catch mismatches before filing.
"""
import json
import os

import httpx
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="TaxIQ | Reconciliation", page_icon="🔄", layout="wide")

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
</style>""", unsafe_allow_html=True)


def fmt_inr(n):
    if n >= 1e7: return f"₹{n/1e7:.1f}Cr"
    if n >= 1e5: return f"₹{n/1e5:.1f}L"
    return f"₹{n:,.0f}"


def api_post(path, json_body=None):
    with httpx.Client(timeout=90) as c:
        return c.post(f"{BACKEND}{path}", json=json_body)


def api_get(path):
    with httpx.Client(timeout=30) as c:
        return c.get(f"{BACKEND}{path}")


# ── DEMO fallback ───────────────────────────────────────
DEMO_RESULT = {
    "gstin": "27AADCB2230M1ZT",
    "period": "Oct 2024",
    "total_invoices_checked": 25,
    "reconciliation_score": 72.0,
    "total_itc_at_risk": 185400,
    "risk_summary": {"high": 2, "medium": 3, "low": 1},
    "mismatch_breakdown": {
        "Invoice Missing in GSTR-2B": 3,
        "Taxable Value Mismatch": 2,
        "Tax Rate Mismatch": 1,
        "GSTIN Mismatch": 1,
        "Period Mismatch": 0,
    },
    "mismatches": [
        {"invoiceId": "INV-2024-003", "mismatchType": "TYPE_1", "riskLevel": "HIGH",
         "amount": 59000, "supplierAmount": 50000, "buyerAmount": 0, "difference": 59000,
         "detail": "Invoice INV-2024-003 filed in GSTR-1 for ₹59,000 but NOT reflected in GSTR-2B. ITC of ₹9,000 blocked under Rule 36(4).",
         "gstin": "27AADCB2230M1ZT", "vendorGstin": "27BBPFU1234G1ZW", "period": "Oct 2024", "severity": 80},
        {"invoiceId": "INV-2024-001", "mismatchType": "TYPE_2", "riskLevel": "HIGH",
         "amount": 900, "supplierAmount": 100000, "buyerAmount": 95000, "difference": 5000,
         "detail": "Taxable value mismatch: GSTR-1 ₹1,00,000 vs GSTR-2B ₹95,000 (diff ₹5,000, 5.0%). Tax on difference: ₹900 at risk.",
         "gstin": "27AADCB2230M1ZT", "vendorGstin": "27BBPFU1234G1ZW", "period": "Oct 2024", "severity": 30},
        {"invoiceId": "INV-2024-007", "mismatchType": "TYPE_4", "riskLevel": "HIGH",
         "amount": 12600, "supplierAmount": 70000, "buyerAmount": 70000, "difference": 12600,
         "detail": "Invoice INV-2024-007 references wrong buyer GSTIN. ITC of ₹12,600 cannot be claimed.",
         "gstin": "27AADCB2230M1ZT", "vendorGstin": "27BBPFU1234G1ZW", "period": "Oct 2024", "severity": 80},
        {"invoiceId": "INV-2024-015", "mismatchType": "TYPE_1", "riskLevel": "MEDIUM",
         "amount": 18500, "supplierAmount": 45000, "buyerAmount": 0, "difference": 18500,
         "detail": "Invoice INV-2024-015 filed in GSTR-1 but missing from GSTR-2B. ITC ₹18,500 blocked.",
         "gstin": "27AADCB2230M1ZT", "vendorGstin": "33ABDCK3456N1ZT", "period": "Oct 2024", "severity": 65},
        {"invoiceId": "INV-2024-009", "mismatchType": "TYPE_3", "riskLevel": "MEDIUM",
         "amount": 6400, "supplierAmount": 120000, "buyerAmount": 120000, "difference": 4.0,
         "detail": "Tax rate mismatch: GSTR-1 effective 18.0% vs GSTR-2B 12.0%. Difference: ₹6,400.",
         "gstin": "27AADCB2230M1ZT", "vendorGstin": "27BBPFU1234G1ZW", "period": "Oct 2024", "severity": 50},
        {"invoiceId": "INV-2024-012", "mismatchType": "TYPE_2", "riskLevel": "LOW",
         "amount": 2700, "supplierAmount": 85000, "buyerAmount": 70000, "difference": 15000,
         "detail": "Taxable value mismatch: GSTR-1 ₹85,000 vs GSTR-2B ₹70,000. Tax on difference: ₹2,700.",
         "gstin": "27AADCB2230M1ZT", "vendorGstin": "27BBPFU1234G1ZW", "period": "Oct 2024", "severity": 30},
    ],
    "audit_trail": [
        "Supplier (GSTIN: 27BBPFU1234G1ZW) filed invoice INV-2024-003 for ₹59,000. However, your GSTR-2B shows: Invoice Missing in GSTR-2B. This puts ₹9,000 of ITC at risk. Recommended action: Contact supplier to file GSTR-1 for this period.",
        "Supplier (GSTIN: 27BBPFU1234G1ZW) filed invoice INV-2024-001 for ₹1,00,000. However, your GSTR-2B shows: Taxable Value Mismatch. This puts ₹900 of ITC at risk. Recommended action: Verify invoice with supplier and request credit/debit note.",
        "Supplier (GSTIN: 27BBPFU1234G1ZW) filed invoice INV-2024-007 for ₹70,000. However, your GSTR-2B shows: GSTIN Mismatch. This puts ₹12,600 of ITC at risk. Recommended action: Request supplier to amend invoice with correct buyer GSTIN.",
        "Supplier (GSTIN: 33ABDCK3456N1ZT) filed invoice INV-2024-015 for ₹45,000. However, your GSTR-2B shows: Invoice Missing in GSTR-2B. This puts ₹18,500 of ITC at risk. Recommended action: Contact supplier to file GSTR-1.",
        "Supplier (GSTIN: 27BBPFU1234G1ZW) filed invoice INV-2024-009 for ₹1,20,000. However, your GSTR-2B shows: Tax Rate Mismatch. This puts ₹6,400 of ITC at risk. Recommended action: Check HSN code classification.",
        "Supplier (GSTIN: 27BBPFU1234G1ZW) filed invoice INV-2024-012 for ₹85,000. However, your GSTR-2B shows: Taxable Value Mismatch. This puts ₹2,700 of ITC at risk. Recommended action: Verify invoice with supplier.",
    ],
}

MISMATCH_LABELS = {
    "TYPE_1": "Invoice Missing in GSTR-2B",
    "TYPE_2": "Taxable Value Mismatch",
    "TYPE_3": "Tax Rate Mismatch",
    "TYPE_4": "GSTIN Mismatch",
    "TYPE_5": "Period Mismatch",
}

# ── Header ──────────────────────────────────────────────
st.title("🔄 GSTR Reconciliation Engine")
st.caption("Compare GSTR-1 (supplier filed) vs GSTR-2B (buyer sees) — catch mismatches before filing")

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
                st.session_state["recon_demo"] = False
            else:
                raise Exception(f"HTTP {r.status_code}")
        except Exception:
            st.session_state["recon_result"] = DEMO_RESULT
            st.session_state["recon_demo"] = True

# ── Display results ─────────────────────────────────────
result = st.session_state.get("recon_result")
if not result:
    st.info("Enter a GSTIN and click **Run Reconciliation** to start.")
    st.stop()

is_demo = st.session_state.get("recon_demo", False)
if is_demo:
    st.markdown('<span class="demo-badge">[DEMO DATA]</span>', unsafe_allow_html=True)

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
    template="plotly_dark",
    paper_bgcolor="#0A1628",
    plot_bgcolor="#0D1F3C",
    font_color="#F8F9FA",
    height=280,
    margin=dict(l=20, r=20, t=10, b=10),
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
