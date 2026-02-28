"""
TaxIQ — 📥 Mock Data Ingestion
Ingest GSTR-1, GSTR-2B, Purchase Register, e-Invoice data for reconciliation & analysis.
"""
import os
import sys
import time

import httpx
import pandas as pd
import streamlit as st

# Add parent to path for theme import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, api_get, api_post, fmt_inr, BACKEND_URL

st.set_page_config(page_title="TaxIQ | Data Ingestion", page_icon="📥", layout="wide")
inject_css()

# ── Page Header ─────────────────────────────────────────
st.markdown('<div class="page-title">📥 Data Ingestion Pipeline</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Ingest GSTR-1, GSTR-2B, Purchase Register &amp; e-Invoice data for reconciliation and analysis</div>', unsafe_allow_html=True)

# ── Current Status ──────────────────────────────────────
st.markdown("### 📊 Ingestion Status")

try:
    status_resp = api_get("/api/ingest/status")
    if status_resp.status_code == 200:
        status = status_resp.json()
    else:
        status = {"sources": {}, "total_records": 0}
except Exception:
    status = {"sources": {}, "total_records": 0}

sources = status.get("sources", {})
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Records", status.get("total_records", 0))
s2.metric("GSTR-1", sources.get("gstr1", {}).get("total_records", 0))
s3.metric("GSTR-2B", sources.get("gstr2b", {}).get("total_records", 0))
s4.metric("Purchase Reg.", sources.get("purchase_register", {}).get("total_records", 0))
s5.metric("e-Invoice", sources.get("einvoice", {}).get("total_records", 0))

st.divider()

# ── Ingestion Cards ─────────────────────────────────────
st.markdown("### 🔄 Ingest Data Sources")

# Input parameters
p1, p2 = st.columns(2)
with p1:
    gstin_input = st.text_input("GSTIN for ingestion", value="29AAACN0001A1Z5", max_chars=15)
with p2:
    period_input = st.selectbox("Tax Period", [
        "2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06",
        "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    ], index=0)

st.write("")

# Four ingestion cards
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        '<div class="ingest-card">'
        '<div class="ingest-icon">📋</div>'
        '<div class="ingest-title">GSTR-1</div>'
        '<div class="ingest-desc">Outward supplies filed by supplier</div>'
        '</div>', unsafe_allow_html=True
    )
    if st.button("⬇️ Ingest GSTR-1", use_container_width=True, key="btn_gstr1"):
        with st.spinner("Fetching GSTR-1 from GSTN..."):
            try:
                r = api_post(f"/api/ingest/gstr1?gstin={gstin_input}&period={period_input}")
                if r.status_code == 200:
                    data = r.json()
                    st.session_state["ingest_gstr1"] = data
                    st.success(f"✅ {data['records_ingested']} records ingested")
                else:
                    st.error(f"Failed: HTTP {r.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

with c2:
    st.markdown(
        '<div class="ingest-card">'
        '<div class="ingest-icon">📄</div>'
        '<div class="ingest-title">GSTR-2B</div>'
        '<div class="ingest-desc">Auto-populated inward supplies</div>'
        '</div>', unsafe_allow_html=True
    )
    if st.button("⬇️ Ingest GSTR-2B", use_container_width=True, key="btn_gstr2b"):
        with st.spinner("Fetching GSTR-2B from GSTN..."):
            try:
                r = api_post(f"/api/ingest/gstr2b?gstin={gstin_input}&period={period_input}")
                if r.status_code == 200:
                    data = r.json()
                    st.session_state["ingest_gstr2b"] = data
                    st.success(f"✅ {data['records_ingested']} records ingested")
                    if data.get("warnings"):
                        for w in data["warnings"][:5]:
                            st.warning(w)
                else:
                    st.error(f"Failed: HTTP {r.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

with c3:
    st.markdown(
        '<div class="ingest-card">'
        '<div class="ingest-icon">🧾</div>'
        '<div class="ingest-title">Purchase Register</div>'
        '<div class="ingest-desc">Upload CSV or generate mock data</div>'
        '</div>', unsafe_allow_html=True
    )
    pr_file = st.file_uploader("Upload CSV (optional)", type=["csv"], key="pr_upload",
                                label_visibility="collapsed")
    if st.button("⬇️ Ingest Purchase Reg.", use_container_width=True, key="btn_pr"):
        with st.spinner("Processing purchase register..."):
            try:
                if pr_file:
                    r = api_post(
                        f"/api/ingest/purchase-register?gstin={gstin_input}",
                        files={"file": (pr_file.name, pr_file.getvalue(), "text/csv")},
                    )
                else:
                    r = api_post(f"/api/ingest/purchase-register?gstin={gstin_input}")
                if r.status_code == 200:
                    data = r.json()
                    st.session_state["ingest_pr"] = data
                    st.success(f"✅ {data['records_ingested']} records ingested")
                else:
                    st.error(f"Failed: HTTP {r.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

with c4:
    st.markdown(
        '<div class="ingest-card">'
        '<div class="ingest-icon">🔐</div>'
        '<div class="ingest-title">e-Invoice</div>'
        '<div class="ingest-desc">IRN-validated electronic invoices</div>'
        '</div>', unsafe_allow_html=True
    )
    if st.button("⬇️ Ingest e-Invoices", use_container_width=True, key="btn_einv"):
        with st.spinner("Fetching from e-Invoice portal..."):
            try:
                r = api_post(f"/api/ingest/einvoice?gstin={gstin_input}&period={period_input}")
                if r.status_code == 200:
                    data = r.json()
                    st.session_state["ingest_einv"] = data
                    st.success(f"✅ {data['records_ingested']} records ingested")
                    if data.get("warnings"):
                        for w in data["warnings"][:5]:
                            st.warning(w)
                else:
                    st.error(f"Failed: HTTP {r.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

# ── Bulk Ingest All ─────────────────────────────────────
st.divider()

if st.button("🚀 Ingest All Sources at Once", use_container_width=True, type="primary"):
    progress = st.progress(0, text="Starting bulk ingestion...")
    results = {}

    sources_list = [
        ("GSTR-1", f"/api/ingest/gstr1?gstin={gstin_input}&period={period_input}"),
        ("GSTR-2B", f"/api/ingest/gstr2b?gstin={gstin_input}&period={period_input}"),
        ("Purchase Register", f"/api/ingest/purchase-register?gstin={gstin_input}"),
        ("e-Invoice", f"/api/ingest/einvoice?gstin={gstin_input}&period={period_input}"),
    ]

    for i, (name, endpoint) in enumerate(sources_list):
        progress.progress((i + 1) / len(sources_list), text=f"Ingesting {name}...")
        try:
            r = api_post(endpoint)
            if r.status_code == 200:
                data = r.json()
                results[name] = data["records_ingested"]
            else:
                results[name] = f"Error: HTTP {r.status_code}"
        except Exception as e:
            results[name] = f"Error: {e}"
        time.sleep(0.3)  # visual feedback

    progress.progress(1.0, text="✅ All sources ingested!")

    # Show results
    rc1, rc2, rc3, rc4 = st.columns(4)
    for col, (name, count) in zip([rc1, rc2, rc3, rc4], results.items()):
        with col:
            if isinstance(count, int):
                st.metric(name, f"{count} records")
            else:
                st.error(f"{name}: {count}")

    st.session_state["bulk_ingested"] = True

st.divider()

# ── Sample Data Viewer ──────────────────────────────────
st.markdown("### 📑 Ingested Data Viewer")

tab1, tab2, tab3, tab4 = st.tabs(["📋 GSTR-1", "📄 GSTR-2B", "🧾 Purchase Register", "🔐 e-Invoice"])

for tab, source_key, source_name in [
    (tab1, "gstr1", "GSTR-1"),
    (tab2, "gstr2b", "GSTR-2B"),
    (tab3, "purchase_register", "Purchase Register"),
    (tab4, "einvoice", "e-Invoice"),
]:
    with tab:
        try:
            r = api_get(f"/api/ingest/records/{source_key}?limit=50")
            if r.status_code == 200:
                records = r.json().get("records", [])
                if records:
                    df = pd.DataFrame(records)
                    # Clean up display
                    cols_to_hide = ["ingested_at", "source"]
                    display_cols = [c for c in df.columns if c not in cols_to_hide]
                    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
                    st.caption(f"Total {source_name} records: {r.json().get('total', 0)}")
                else:
                    st.info(f"No {source_name} data ingested yet. Click the ingest button above.")
            else:
                st.info(f"No {source_name} data available.")
        except Exception:
            st.info(f"Backend not reachable. Ingest {source_name} data to see records here.")

st.caption("Powered by TaxIQ Data Pipeline · Mock GSTN API · CSV Parser · e-Invoice IRP")
