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
st.caption("India’s Unified Tax Intelligence Agent · GST OCR · ITC Fraud Graph · Personal Tax Saver")

cols = st.columns(3)
with cols[0]:
    st.metric("Invoices Processed", st.session_state.get("kpi_invoices", 0))
with cols[1]:
    st.metric("Tax Saved (est.)", inr(st.session_state.get("kpi_tax_saved", 0)))
with cols[2]:
    st.metric("Frauds Detected", st.session_state.get("kpi_frauds", 0))

st.divider()

nav = st.columns(3)
if hasattr(st, "page_link"):
    with nav[0]:
        st.page_link("pages/1_📸_GST_Filing.py", label="📸 GST Filing", use_container_width=True)
    with nav[1]:
        st.page_link("pages/2_🕸️_Fraud_Graph.py", label="🕸️ Fraud Graph", use_container_width=True)
    with nav[2]:
        st.page_link("pages/3_📊_Tax_Saver.py", label="📊 Tax Saver", use_container_width=True)
else:
    st.info("Use the left sidebar page selector to switch between 📸 GST Filing, 🕸️ Fraud Graph, and 📊 Tax Saver pages.")

st.divider()

st.markdown("### System Status")
try:
    r = api_get("/health")
    if r.status_code == 200:
        st.success("Backend is reachable.")
    else:
        st.warning(f"Backend responded with {r.status_code}.")
except Exception:
    st.warning("Backend is not reachable. Start it with: `uvicorn backend.main:app --reload --port 8000`")

st.caption("Powered by Claude AI (when configured) · OCR by Tesseract · Graph by Neo4j/networkx · Reports by fpdf2")

