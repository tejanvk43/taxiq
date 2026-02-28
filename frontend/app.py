import json
import os
from pathlib import Path

import httpx
import streamlit as st
from theme import inject_css, inr, fmt_inr, api_get, api_post, BACKEND_URL


st.set_page_config(
    page_title="TaxIQ | India's Tax Intelligence Agent",
    page_icon="💰",
    layout="wide",
)
inject_css()


st.markdown('<div class="page-title">TaxIQ</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">India\'s Unified Tax Intelligence Agent · GST OCR · ITC Fraud Graph · Personal Tax Saver · WhatsApp Bot</div>', unsafe_allow_html=True)

# ── 7 KPI Cards ─────────────────────────────────────────
# Fetch live KPIs from backend
if "kpis_loaded" not in st.session_state:
    try:
        with httpx.Client(timeout=10) as c:
            kpi_resp = c.get(f"{BACKEND_URL}/api/dashboard/kpis").json()
        st.session_state["kpi_invoices"] = kpi_resp.get("invoices_processed", 0)
        st.session_state["kpi_frauds"] = kpi_resp.get("fraud_rings", 0)
        st.session_state["kpi_tax_saved"] = kpi_resp.get("tax_saved", 0)
        st.session_state["kpi_mismatches"] = kpi_resp.get("mismatches_caught", 0)
        st.session_state["kpi_vendors"] = kpi_resp.get("vendors_scored", 0)
        st.session_state["kpi_notices"] = kpi_resp.get("notices_generated", 0)
        st.session_state["kpi_itc_recovered"] = kpi_resp.get("itc_recovered", 0)
        st.session_state["kpis_loaded"] = True
    except Exception:
        pass

r1 = st.columns(4)
r2 = st.columns(3)
with r1[0]:
    st.metric("Invoices Processed", st.session_state.get("kpi_invoices", 0))
with r1[1]:
    st.metric("Fraud Rings Found", st.session_state.get("kpi_frauds", 0))
with r1[2]:
    st.metric("Tax Saved (est.)", inr(st.session_state.get("kpi_tax_saved", 0)))
with r1[3]:
    st.metric("Mismatches Caught", st.session_state.get("kpi_mismatches", 0))
with r2[0]:
    st.metric("Vendors Scored", st.session_state.get("kpi_vendors", 0))
with r2[1]:
    st.metric("Notices Generated", st.session_state.get("kpi_notices", 0))
with r2[2]:
    st.metric("ITC Recovered", inr(st.session_state.get("kpi_itc_recovered", 0)))

st.divider()

if hasattr(st, "page_link"):
    row1 = st.columns(3)
    with row1[0]:
        st.page_link("pages/1_📸_GST_Filing.py", label="📸 GST Filing", use_container_width=True)
    with row1[1]:
        st.page_link("pages/2_🕸️_Fraud_Graph.py", label="🕸️ Fraud Graph", use_container_width=True)
    with row1[2]:
        st.page_link("pages/3_📊_Tax_Saver.py", label="📊 Tax Saver", use_container_width=True)
    row2 = st.columns(4)
    with row2[0]:
        st.page_link("pages/4_🔄_Reconciliation.py", label="🔄 Reconciliation", use_container_width=True)
    with row2[1]:
        st.page_link("pages/5_🏢_Vendor_Scores.py", label="🏢 Vendor Scores", use_container_width=True)
    with row2[2]:
        st.page_link("pages/6_📨_Notice_Generator.py", label="📨 Notice Generator", use_container_width=True)
    with row2[3]:
        st.page_link("pages/7_📋_ITC_Recovery.py", label="📋 ITC Recovery", use_container_width=True)
    row3 = st.columns(3)
    with row3[0]:
        st.page_link("pages/8_📥_Data_Ingestion.py", label="📥 Data Ingestion", use_container_width=True)
    with row3[1]:
        st.page_link("pages/9_🔍_Audit_Trail.py", label="🔍 Audit Trail", use_container_width=True)
    with row3[2]:
        st.page_link("pages/10_📈_Predictive_Risk.py", label="📈 Predictive Risk", use_container_width=True)
else:
    st.info("Use the left sidebar to navigate between all 10 pages.")

st.divider()

# ── System Status ───────────────────────────────────────
st.markdown("### System Status")

services = []
try:
    with httpx.Client(timeout=5) as c:
        h = c.get(f"{BACKEND_URL}/health").json()
    services.append(("FastAPI Backend", h.get("ok", True)))
    services.append(("Neo4j", h.get("neo4j", "demo")))
    services.append(("PostgreSQL", h.get("postgres", "demo")))
    services.append(("Redis / Celery", h.get("redis", "demo")))
    services.append(("Gemini AI", h.get("gemini", "demo")))
    services.append(("WhatsApp Bot", h.get("whatsapp", "demo")))
except Exception:
    services = [("FastAPI Backend", False), ("Neo4j", False), ("PostgreSQL", False), ("Redis / Celery", False), ("Gemini AI", False), ("WhatsApp Bot", False)]

pills = ""
for name, ok in services:
    if ok == "demo":
        color = "#FDCB6E"
        icon = "◉"
        label = f"{name} (demo)"
    elif ok:
        color = "#00B894"
        icon = "●"
        label = name
    else:
        color = "#D63031"
        icon = "○"
        label = name
    r_c, g_c, b_c = (int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    pills += f'<span style="display:inline-block;margin:0 6px 4px 0;padding:4px 12px;border-radius:999px;background:rgba({r_c},{g_c},{b_c},0.15);border:1px solid {color};color:{color};font-size:13px;font-weight:600">{icon} {label}</span>'
st.markdown(pills, unsafe_allow_html=True)

st.divider()

# ── Quick Demo hint ─────────────────────────────────────
st.info(
    "**🎯 Quick Demo for Judges**\n\n"
    "1. **GST Filing** → Upload `data/sample_invoices/` image → auto-extract → file GSTR-1\n"
    "2. **Fraud Graph** → Enter GSTIN `27AAACF9999K1Z9` → see network + shell companies\n"
    "3. **Tax Saver** → Upload `data/sample_bank_statements/bank_statement.csv` → see regime comparison + hidden deductions\n"
    "4. **Reconciliation** → Click Run → instant GSTR-1 vs 2B diff with 5 mismatch types\n"
    "5. **Vendor Scores** → Load vendors → see AAA-D grades with radar charts\n"
    "6. **Notice Generator** → Fill form → generate Section 73 SCN\n"
    "7. **ITC Recovery** → Full Kanban pipeline from detection to recovery\n"
    "8. **Data Ingestion** → Ingest GSTR-1, GSTR-2B, Purchase Register, e-Invoice with preview\n"
    "9. **Audit Trail** → Explainable multi-hop audit trail with legal references & NL explanations\n"
    "10. **Predictive Risk** → ML-powered vendor compliance forecast with confidence bands"
)

st.caption("Powered by Gemini AI · OCR by Tesseract · Graph by Neo4j/networkx · NEXUS Scoring · WhatsApp via Twilio · Reports by fpdf2")

