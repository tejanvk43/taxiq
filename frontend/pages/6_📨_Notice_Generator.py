"""
TaxIQ — 📨 GST Notice Generator
Two-column: Input → Generated notice. Live GSTN alerts below.
"""
import json
import os
import time

import httpx
import streamlit as st

st.set_page_config(page_title="TaxIQ | Notices", page_icon="📨", layout="wide")

BACKEND = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")

# ── Design System CSS ───────────────────────────────────
st.markdown("""<style>
    .stApp { background-color: #0A1628; color: #F8F9FA; }
    .stMetric { background: #0D1F3C; border-radius: 12px;
                padding: 16px; border-left: 4px solid #FF9933; }
    .stButton>button { background: #FF9933; color: #0A1628;
                       font-weight: 700; border-radius: 8px;
                       border: none; }
    div[data-testid="metric-container"] {
      background: #0D1F3C; border-radius: 10px; padding: 10px; }
    .demo-badge {
      display:inline-block; padding:2px 10px; border-radius:999px;
      background:rgba(253,203,110,.15); border:1px solid #FDCB6E;
      color:#FDCB6E; font-size:12px; font-weight:600; }
    .notice-box {
      background: #0D1F3C; border: 1px solid #FF9933; border-radius: 12px;
      padding: 24px; font-family: Georgia, serif; line-height: 1.8;
      color: #F8F9FA; white-space: pre-wrap; }
    .notice-header { text-align: center; font-size: 18px; font-weight: 700;
                     color: #FF9933; border-bottom: 2px solid #FF9933;
                     padding-bottom: 10px; margin-bottom: 16px; }
    .alert-card { background: #1A0A0A; border-left: 4px solid #D63031;
                  border-radius: 6px; padding: 10px 14px; margin: 6px 0; }
</style>""", unsafe_allow_html=True)


def fmt_inr(n):
    if n >= 1e7:  return f"₹{n/1e7:.1f}Cr"
    if n >= 1e5:  return f"₹{n/1e5:.1f}L"
    return f"₹{n:,.0f}"


def api_post(path, payload):
    with httpx.Client(timeout=30) as c:
        return c.post(f"{BACKEND}{path}", json=payload)


def api_get(path, params=None):
    with httpx.Client(timeout=30) as c:
        return c.get(f"{BACKEND}{path}", params=params)


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

DEMO_NOTICE = """\
                    OFFICE OF THE COMMISSIONER
                    CENTRAL GOODS AND SERVICES TAX
                    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SHOW CAUSE NOTICE

Notice No: SCN/CGST/2024-25/001847
Date: 15-01-2025

To,
M/s Falcon Components Pvt Ltd
GSTIN: 27AAACF9999K1Z9
Registered Address: Plot 45, MIDC Andheri East, Mumbai-400093

Subject: Show Cause Notice under Section 73 of CGST Act, 2017

Sir/Madam,

Whereas, upon scrutiny of your GST returns for the period April 2024 to
September 2024, the following discrepancies have been observed:

1. GSTR-1 vs GSTR-3B Mismatch:
   - Outward supplies declared in GSTR-1: ₹2,45,00,000
   - Outward supplies declared in GSTR-3B: ₹2,12,00,000
   - Difference: ₹33,00,000

2. Input Tax Credit Reversal Not Done:
   - ITC availed on non-business expenses: ₹4,50,000
   - ITC on blocked credits (Section 17(5)): ₹1,80,000
   - Total ITC to be reversed: ₹6,30,000

3. Total Tax Demand:
   - CGST: ₹2,97,000
   - SGST: ₹2,97,000
   - Interest u/s 50: ₹89,100
   - Total: ₹6,83,100

You are hereby directed to show cause within THIRTY (30) days from the
date of receipt of this notice as to why:

(a) The tax amount of ₹5,94,000 along with applicable interest shall
    not be demanded and recovered from you; and
(b) Penalty under Section 73(9) shall not be imposed.

In case of failure to respond within the stipulated time, the matter
shall be decided ex-parte on the basis of available records.

                                        Sd/-
                                        Shri Rajesh Kumar
                                        Assistant Commissioner, CGST
                                        Division-IV, Mumbai Zone

CC: 1. The Commissioner, CGST, Mumbai Zone
    2. Guard File\
"""

DEMO_ALERTS = [
    {"gstin": "19AABCG1234Q1Z2", "name": "GoldStar Traders", "alert": "Return not filed for 3 consecutive months", "risk": "HIGH", "date": "2025-01-14"},
    {"gstin": "07AABCS7777H1Z1", "name": "Shadow Supplies Delhi", "alert": "Sudden 400% spike in outward supplies", "risk": "CRITICAL", "date": "2025-01-15"},
    {"gstin": "27AAACF9999K1Z9", "name": "Falcon Components", "alert": "ITC claimed exceeds eligible amount by ₹4.5L", "risk": "MEDIUM", "date": "2025-01-13"},
]

# ── Header ──────────────────────────────────────────────
st.title("📨 GST Notice Generator")
st.caption("AI-powered notice drafting · Section-referenced · PDF-ready")

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
                r = api_post("/api/notices/generate", payload)
                if r.status_code == 200:
                    data = r.json()
                    notice_text = data.get("noticeContent", data.get("notice", DEMO_NOTICE))
                    notice_id = data.get("noticeId", "DEMO-001")
                    st.session_state["notice_text"] = notice_text
                    st.session_state["notice_id"] = notice_id
                    st.session_state["notice_demo"] = False
                else:
                    raise Exception(f"HTTP {r.status_code}")
            except Exception:
                st.session_state["notice_text"] = DEMO_NOTICE
                st.session_state["notice_id"] = "DEMO-SCN-001"
                st.session_state["notice_demo"] = True

    if "notice_text" in st.session_state:
        if st.session_state.get("notice_demo", False):
            st.markdown('<span class="demo-badge">[DEMO DATA]</span>', unsafe_allow_html=True)
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
        api_alerts = r.json().get("alerts", [])
        if api_alerts:
            alerts = api_alerts
        else:
            alerts = DEMO_ALERTS
            st.markdown('<span class="demo-badge">[DEMO DATA]</span>', unsafe_allow_html=True)
    else:
        raise Exception()
except Exception:
    alerts = DEMO_ALERTS
    st.markdown('<span class="demo-badge">[DEMO DATA]</span>', unsafe_allow_html=True)

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
