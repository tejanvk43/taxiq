import json
import os
import sys
import random

import httpx
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, inr, fmt_inr, api_get, api_post, BACKEND_URL

st.set_page_config(page_title="TaxIQ | GST Filing", page_icon="📸", layout="wide")
inject_css()

st.markdown('<div class="page-title">📸 GST Invoice OCR Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Upload invoice (JPG/PNG/PDF) → OCR → Parsed Invoice → GSTR‑1 entry</div>', unsafe_allow_html=True)

left, right = st.columns([0.4, 0.6], gap="large")

with left:
    file = st.file_uploader("Upload invoice", type=["jpg", "jpeg", "png", "pdf"])
    user_gstin = st.text_input("Your GSTIN (buyer)", value="27AAACG1000A1Z5")
    if "gst_period" not in st.session_state:
        st.session_state["gst_period"] = "2024-02"
    period = st.text_input("Period (YYYY-MM)", value=st.session_state["gst_period"])
    st.session_state["gst_period"] = period

    process = st.button("Process Invoice", use_container_width=True, type="primary", disabled=file is None)

with right:
    if process and file is not None:
        messages = ["Reading invoice...", "Extracting GSTIN...", "Calculating tax...", "Building GSTR-1..."]
        with st.spinner(random.choice(messages)):
            try:
                with httpx.Client(timeout=120) as client:
                    res = client.post(
                        f"{BACKEND_URL}/gst/process-invoice",
                        files={"file": (file.name, file.getvalue(), file.type or "application/octet-stream")},
                    )
                if res.status_code != 200:
                    st.error(f"Could not process invoice: {res.text}")
                else:
                    data = res.json()
                    st.session_state["last_invoice"] = data
                    st.session_state["kpi_invoices"] = st.session_state.get("kpi_invoices", 0) + 1
            except Exception as e:
                st.error(f"Backend not reachable or error occurred: {e}")

    data = st.session_state.get("last_invoice")
    if not data:
        st.info("Upload an invoice and click **Process Invoice**. Sample invoices are auto-generated in `data/sample_invoices/` on backend start.")
    else:
        inv = data.get("invoice", {})
        gstr1 = data.get("gstr1_entry", {})
        conf = float(data.get("confidence_score", 0))
        warnings = data.get("warnings", [])

        badge = "🟢 High" if conf >= 0.8 else "🟡 Medium" if conf >= 0.6 else "🔴 Low"
        st.markdown(f"### Parsed Invoice  \n**Confidence:** {badge} ({conf:.2f})")

        if warnings:
            for w in warnings:
                if "[DEMO DATA]" in w:
                    st.warning(w)
                else:
                    st.info(w)

        st.table(
            {
                "Field": ["Vendor", "Vendor GSTIN", "Buyer GSTIN", "Invoice No", "Date", "Taxable", "CGST", "SGST", "IGST", "Total"],
                "Value": [
                    inv.get("vendor_name"),
                    inv.get("vendor_gstin"),
                    inv.get("buyer_gstin"),
                    inv.get("invoice_number"),
                    inv.get("invoice_date"),
                    inr(inv.get("taxable_value", 0)),
                    inr(inv.get("cgst", 0)),
                    inr(inv.get("sgst", 0)),
                    inr(inv.get("igst", 0)),
                    inr(inv.get("total_value", 0)),
                ],
            }
        )

        st.markdown("### GSTR‑1 Entry Preview")
        st.json(gstr1)

        colA, colB, colC = st.columns([0.45, 0.35, 0.2])
        with colA:
            if st.button("Add to Return", use_container_width=True):
                st.success("Added. (This demo stores invoices server-side and rebuilds return on demand.)")
        with colB:
            st.metric("This Month: Tax Liability (est.)", inr(data.get("gstr1_return_preview", {}).get("totals", {}).get("total_tax_liability", 0)))
        with colC:
            st.metric("Invoices", data.get("gstr1_return_preview", {}).get("totals", {}).get("invoices", 0))

        with st.expander("Full GSTR‑1 Return Viewer", expanded=False):
            st.json(data.get("gstr1_return_preview", {}))

        st.download_button(
            "Download GSTR‑1 JSON",
            data=json.dumps(data.get("gstr1_return_preview", {}), indent=2).encode("utf-8"),
            file_name=f"gstr1_{user_gstin}_{period}.json",
            mime="application/json",
            use_container_width=True,
        )

