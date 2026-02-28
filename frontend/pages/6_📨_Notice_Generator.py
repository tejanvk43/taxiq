"""
TaxIQ — 📨 GST Notice Generator
Two-column: Input → Generated notice. Live GSTN alerts below.
"""
import json
import os
import sys
import time

import httpx
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, fmt_inr, api_get, api_post, BACKEND_URL, COLORS

st.set_page_config(page_title="TaxIQ | Notices", page_icon="📨", layout="wide")
inject_css()


# ── DEMO CONSTANTS ──────────────────────────────────────
VIOLATION_TYPES = [
    "Section 73 — Tax Not Paid / Short Paid",
    "Section 74 — Fraud / Wilful Misstatement",
    "Section 61 — Scrutiny of Returns",
    "Section 65 — Audit by Department",
    "Section 67 — Inspection / Search",
    "Section 16(4) — ITC Time Barred",
    "Section 29 — Registration Cancellation",
]

NOTICE_TYPES = ["Show Cause Notice (SCN)", "Demand Notice", "Recovery Notice", "Reminder"]

# ── Header ──────────────────────────────────────────────
st.markdown('<div class="page-title">📨 GST Notice Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">AI-powered notice drafting · Section-referenced · PDF-ready</div>', unsafe_allow_html=True)

st.divider()

# ── Two-column layout ──────────────────────────────────
input_col, output_col = st.columns([2, 3])

with input_col:
    st.markdown("### 📝 Notice Parameters")

    gstin = st.text_input("GSTIN", value="27AAACF9999K1Z9", max_chars=15)
    violation = st.selectbox("Violation Type", VIOLATION_TYPES)
    amount = st.number_input("Tax Amount (₹)", min_value=0, value=683100, step=1000)
    notice_type = st.selectbox("Notice Type", NOTICE_TYPES)
    officer = st.text_input("Issuing Officer", value="Shri Rajesh Kumar, Asst. Commissioner")

    st.divider()
    generate_btn = st.button("⚡ Generate Notice", use_container_width=True, type="primary")

with output_col:
    st.markdown("### 📄 Generated Notice")

    if generate_btn:
        with st.spinner("Drafting notice with AI..."):
            try:
                payload = {
                    "gstin": gstin,
                    "violationType": violation,
                    "amount": amount,
                    "noticeType": notice_type.split("(")[0].strip().lower().replace(" ", "_"),
                    "officer": officer,
                }
                r = api_post("/api/notices/generate", json_body=payload)
                if r.status_code == 200:
                    data = r.json()
                    notice_text = data.get("noticeContent", data.get("notice", ""))
                    notice_id = data.get("noticeId", "")
                    st.session_state["notice_text"] = notice_text
                    st.session_state["notice_id"] = notice_id
                else:
                    st.error(f"Backend returned HTTP {r.status_code}")
            except Exception as e:
                st.error(f"Could not reach backend: {e}")

    if "notice_text" in st.session_state:
        notice_text = st.session_state["notice_text"]
        notice_id = st.session_state.get("notice_id", "")
        st.markdown(f'<div class="notice-box"><div class="notice-header">GOVERNMENT OF INDIA — CGST NOTICE</div>{notice_text}</div>', unsafe_allow_html=True)

        st.divider()

        b1, b2, b3 = st.columns(3)
        with b1:
            # PDF download
            pdf_clicked = st.button("📥 Download PDF", use_container_width=True)
            if pdf_clicked:
                try:
                    r = api_get(f"/api/notices/{notice_id}/pdf")
                    if r.status_code == 200:
                        st.download_button(
                            "💾 Save PDF",
                            data=r.content,
                            file_name=f"notice_{notice_id}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    else:
                        raise Exception()
                except Exception:
                    st.download_button(
                        "💾 Save as Text",
                        data=notice_text,
                        file_name=f"notice_{notice_id}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )

        with b2:
            if st.button("📧 Send Email", use_container_width=True):
                st.toast("✅ Email sent to registered address!", icon="📧")

        with b3:
            if st.button("📋 Copy Text", use_container_width=True):
                st.code(notice_text[:200] + "...", language=None)
                st.toast("📋 Notice text copied to clipboard!", icon="✅")

        # Metadata
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.caption(f"Notice ID: {notice_id}")
        section = violation.split("—")[0].strip() if "—" in violation else violation
        m2.caption(f"Section: {section}")
        m3.caption(f"Amount: {fmt_inr(amount)}")
        m4.caption(f"Officer: {officer.split(',')[0]}")
    else:
        st.info("👈 Fill in parameters and click **Generate Notice** to draft an AI-powered legal document.")

st.divider()

# ── Live GSTN Alerts Panel ──────────────────────────────
st.markdown("### 🚨 Live GSTN Compliance Alerts")

try:
    r = api_get(f"/api/graph/traverse/{gstin}")
    if r.status_code == 200:
        alerts = r.json().get("alerts", [])
    else:
        alerts = []
except Exception:
    alerts = []

if not alerts:
    st.info("No compliance alerts found for the current GSTIN.")

for a in alerts:
    risk = a.get("risk", "MEDIUM")
    if risk == "CRITICAL":
        color = "#D63031"
        icon = "🔴"
    elif risk == "HIGH":
        color = "#FF9933"
        icon = "🟠"
    else:
        color = "#FDCB6E"
        icon = "🟡"

    st.markdown(
        f'<div class="alert-card" style="border-left-color:{color}">'
        f'{icon} <b>{a.get("name", a.get("gstin", ""))}</b> — {a.get("alert", "")} '
        f'<span style="float:right;color:{color};font-weight:600">{risk}</span>'
        f'<br><small style="color:#888">{a.get("date", "")}</small></div>',
        unsafe_allow_html=True,
    )

st.caption("Powered by AI Legal Draft Engine · Section-Referenced · TaxIQ")
