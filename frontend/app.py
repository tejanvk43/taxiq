import json
import os
from pathlib import Path

import httpx
import streamlit as st


st.set_page_config(
    page_title="TaxIQ | India's Tax Intelligence Agent",
    page_icon="💰",
    layout="wide",
)

st.markdown(
    """
<style>
/* TaxIQ dark theme accents */
section.main { background-color: #0A1628; }
div[data-testid="stAppViewContainer"] { background-color: #0A1628; }
div[data-testid="stHeader"] { background-color: rgba(10,22,40,0.6); }
.taxiq-badge {
  display:inline-block; padding:2px 8px; border-radius:999px;
  border:1px solid rgba(255,153,51,.55);
  background: rgba(255,153,51,.10);
  color: #FF9933; font-size: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)

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


def api_get(path: str):
    with httpx.Client(timeout=30) as client:
        return client.get(f"{BACKEND_URL}{path}")


def api_post(path: str, files=None, data=None, json_body=None):
    with httpx.Client(timeout=60) as client:
        return client.post(f"{BACKEND_URL}{path}", files=files, data=data, json=json_body)


st.markdown("## TaxIQ")
st.caption("India's Unified Tax Intelligence Agent · GST OCR · ITC Fraud Graph · Personal Tax Saver · WhatsApp Bot")

# ── 7 KPI Cards ─────────────────────────────────────────
r1 = st.columns(4)
r2 = st.columns(3)
with r1[0]:
    st.metric("Invoices Processed", st.session_state.get("kpi_invoices", 48))
with r1[1]:
    st.metric("Fraud Rings Found", st.session_state.get("kpi_frauds", 3))
with r1[2]:
    st.metric("Tax Saved (est.)", inr(st.session_state.get("kpi_tax_saved", 184200)))
with r1[3]:
    st.metric("Mismatches Caught", st.session_state.get("kpi_mismatches", 12))
with r2[0]:
    st.metric("Vendors Scored", st.session_state.get("kpi_vendors", 6))
with r2[1]:
    st.metric("Notices Generated", st.session_state.get("kpi_notices", 4))
with r2[2]:
    st.metric("ITC Recovered", inr(st.session_state.get("kpi_itc_recovered", 1025000)))

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
        st.page_link("pages/4_�_Reconciliation.py", label="🔄 Reconciliation", use_container_width=True)
    with row2[1]:
        st.page_link("pages/5_🏢_Vendor_Scores.py", label="🏢 Vendor Scores", use_container_width=True)
    with row2[2]:
        st.page_link("pages/6_📨_Notice_Generator.py", label="📨 Notice Generator", use_container_width=True)
    with row2[3]:
        st.page_link("pages/7_📋_ITC_Recovery.py", label="📋 ITC Recovery", use_container_width=True)
else:
    st.info("Use the left sidebar to navigate between all 7 pages.")

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
    "7. **ITC Recovery** → Full Kanban pipeline from detection to recovery"
)

st.caption("Powered by Claude AI · OCR by Tesseract · Graph by Neo4j/networkx · NEXUS Scoring · WhatsApp via Twilio · Reports by fpdf2")

