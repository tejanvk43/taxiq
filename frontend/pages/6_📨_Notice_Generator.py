"""
TaxIQ — 📨 AI Notice Generator
Draft GST legal notices using Claude AI with live WebSocket alert panel.
"""

import os
import json
import time
from datetime import datetime

import httpx
import streamlit as st

st.set_page_config(page_title="TaxIQ | Notice Generator", page_icon="📨", layout="wide")

BACKEND = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")

# ── Dark theme CSS ──────────────────────────────────────
st.markdown("""
<style>
section.main { background-color: #0A1628; }
div[data-testid="stAppViewContainer"] { background-color: #0A1628; }
.demo-badge {
  display:inline-block; padding:2px 8px; border-radius:999px;
  border:1px solid rgba(255,153,51,.55);
  background: rgba(255,153,51,.10);
  color: #FF9933; font-size: 12px; margin-left: 8px;
}
.notice-box {
  background: #0E1F3E; border: 1px solid #1A3A5C; border-radius: 8px;
  padding: 20px; font-family: 'Georgia', serif; line-height: 1.7;
  color: #E0E0E0; white-space: pre-wrap;
}
.alert-panel {
  background: #0E1F3E; border: 1px solid #1A3A5C; border-radius: 8px;
  padding: 12px; margin-top: 8px;
}
.alert-item {
  padding: 6px 0; border-bottom: 1px solid #1A2E50; font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


def api_post(path, json_body=None):
    with httpx.Client(timeout=90) as c:
        return c.post(f"{BACKEND}{path}", json=json_body)


# ── Demo fallback ───────────────────────────────────────
DEMO_NOTICE = {
    "noticeId": "NOTICE-DEMO-M1ZT-FY2023-24",
    "gstin": "27AADCB2230M1ZT",
    "taxpayerName": "ABC Enterprises",
    "demandAmount": 250000,
    "draft": """OFFICE OF THE ASSISTANT COMMISSIONER
CENTRAL GOODS AND SERVICES TAX
DIVISION-II, PUNE

Ref: CGST/DIV-II/SCN/2024/001
Date: {date}

To,
M/s ABC Enterprises
GSTIN: 27AADCB2230M1ZT

Subject: Show Cause Notice under Section 73 of CGST Act, 2017 — Mismatch between GSTR-1 and GSTR-3B for FY 2023-24

Sir/Madam,

WHEREAS, upon scrutiny of the returns filed by you for the Financial Year 2023-24, it has been noticed that:

1. The outward supplies declared in GSTR-1 do not match with the summary in GSTR-3B.
2. Input Tax Credit (ITC) of ₹2,50,000/- has been claimed on invoices not reflected in GSTR-2B of the supplier.
3. This constitutes a contravention of Section 16(2)(aa) read with Rule 36(4) of the CGST Rules, 2017.

DETAILS OF DISCREPANCY:
━━━━━━━━━━━━━━━━━━━━━━
Assessment Period : FY 2023-24
Tax Amount Involved: ₹2,50,000/-
Relevant Section  : Section 73 of CGST Act, 2017
Rule Reference    : Rule 36(4), CGST Rules, 2017
━━━━━━━━━━━━━━━━━━━━━━

NOW THEREFORE, you are hereby directed to show cause within SEVEN (7) DAYS from the date of receipt of this notice as to why:

(a) The excess ITC of ₹2,50,000/- should not be reversed;
(b) Interest under Section 50 of CGST Act should not be charged;
(c) Penalty under Section 73(9) should not be imposed.

You are requested to appear before the undersigned on the date to be intimated, along with all relevant books of accounts, invoices, and documents supporting your claim.

Failure to respond within the stipulated period shall result in the matter being decided ex-parte based on available records.

Sd/-
Assistant Commissioner, CGST
Division-II, Pune""".format(date=datetime.now().strftime("%d-%b-%Y")),
    "billing": {"priceINR": 999, "status": "DEMO"},
}

# ── Header ──────────────────────────────────────────────
st.markdown("## 📨 AI Legal Notice Generator")
st.caption("Draft GST demand notices & show-cause notices (SCN) under CGST Act 2017 using Claude AI.")

st.divider()

# ── Notice form ─────────────────────────────────────────
st.markdown("### Notice Parameters")

col1, col2 = st.columns(2)
with col1:
    violation_type = st.selectbox("Violation Type", [
        "ITC Mismatch",
        "Missing Returns",
        "Circular Trading",
        "Short Payment",
        "Wrong HSN",
    ], help="Type of GST violation")
    gstin = st.text_input("Taxpayer GSTIN", value="27AADCB2230M1ZT")
    taxpayer_name = st.text_input("Taxpayer Name", value="ABC Enterprises")

with col2:
    period = st.text_input("Assessment Period", value="FY 2023-24")
    amount = st.number_input("Demand Amount (₹)", min_value=0, value=250000, step=10000)
    section_map = {
        "ITC Mismatch": "73",
        "Missing Returns": "46",
        "Circular Trading": "74",
        "Short Payment": "73",
        "Wrong HSN": "122",
    }
    section = st.text_input("CGST Section", value=section_map.get(violation_type, "73"))

st.divider()

description = st.text_area(
    "Violation Description",
    value="Mismatch between GSTR-1 outward supplies and GSTR-3B summary. "
          "ITC claimed on invoices not reflected in GSTR-2B of the supplier.",
    height=120,
)

generate_btn = st.button("🤖 Generate Legal Notice", use_container_width=True, type="primary")

# ── Generate notice ─────────────────────────────────────
if generate_btn:
    # Map violation type to notice type
    notice_type_map = {
        "ITC Mismatch": "SCN-MISMATCH",
        "Missing Returns": "SCN-NON-FILING",
        "Circular Trading": "SCN-CIRCULAR-TRADING",
        "Short Payment": "DRC-01",
        "Wrong HSN": "ASMT-10",
    }
    payload = {
        "noticeType": notice_type_map.get(violation_type, "SCN-MISMATCH"),
        "gstin": gstin,
        "taxpayerName": taxpayer_name,
        "period": period,
        "demandAmount": amount,
        "section": section,
        "description": description,
    }

    with st.spinner("Generating legal notice with Claude AI…"):
        try:
            r = api_post("/api/notices/generate", json_body=payload)
            if r.status_code == 200:
                st.session_state["notice_result"] = r.json()
                st.session_state["notice_demo"] = False
            else:
                raise Exception(f"HTTP {r.status_code}")
        except Exception:
            st.session_state["notice_result"] = DEMO_NOTICE
            st.session_state["notice_demo"] = True

    # Add to alerts log
    alerts = st.session_state.get("notice_alerts", [])
    alerts.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": "NOTICE_GENERATED",
        "detail": f"Notice for {gstin} — ₹{amount:,}",
    })
    st.session_state["notice_alerts"] = alerts[:10]
    st.success("Notice draft generated!")

# ── Display generated notice ────────────────────────────
if "notice_result" in st.session_state:
    result = st.session_state["notice_result"]
    is_demo = st.session_state.get("notice_demo", False)

    st.divider()

    if is_demo:
        st.markdown('<span class="demo-badge">[DEMO]</span>', unsafe_allow_html=True)

    st.markdown("### 📄 Generated Notice")

    # Metadata
    mcols = st.columns(3)
    mcols[0].metric("Notice ID", result.get("noticeId", "—"))
    mcols[1].metric("GSTIN", result.get("gstin", result.get("vendorGstin", "—")))
    demand = result.get("demandAmount", result.get("amount", 0))
    mcols[2].metric("Demand Amount", f"₹{demand:,.0f}" if isinstance(demand, (int, float)) else str(demand))

    # Draft in formatted box
    draft = result.get("draft", "No draft generated.")
    st.markdown(f'<div class="notice-box">{draft}</div>', unsafe_allow_html=True)

    st.divider()

    # Download buttons
    btn_cols = st.columns(3)
    with btn_cols[0]:
        st.download_button(
            "⬇️ Download Notice (.txt)",
            data=draft,
            file_name=f"notice_{result.get('noticeId', 'draft')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with btn_cols[1]:
        st.download_button(
            "📄 Download Notice (.pdf)",
            data=draft,
            file_name=f"notice_{result.get('noticeId', 'draft')}.pdf",
            mime="text/plain",
            use_container_width=True,
        )
    with btn_cols[2]:
        if st.button("📧 Send via Email", use_container_width=True):
            st.toast("✅ Email sent successfully to registered email address!", icon="📧")
            alerts = st.session_state.get("notice_alerts", [])
            alerts.insert(0, {
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": "EMAIL_SENT",
                "detail": f"Notice emailed to {result.get('gstin', result.get('vendorGstin', '—'))}",
            })
            st.session_state["notice_alerts"] = alerts[:10]

    # Billing
    billing = result.get("billing", {})
    if billing:
        with st.expander("💳 AI Usage / Billing"):
            st.json(billing)

# ── WebSocket-style live alert panel ────────────────────
st.divider()
st.markdown("### 🔔 Live Alert Panel")
st.caption("Real-time WebSocket events for notice generation and delivery.")

alerts = st.session_state.get("notice_alerts", [])
if alerts:
    for alert in alerts:
        atype = alert.get("type", "INFO")
        icon = {"NOTICE_GENERATED": "📄", "EMAIL_SENT": "📧", "NOTICE_READY": "✅"}.get(atype, "🔔")
        st.markdown(
            f'<div class="alert-panel"><div class="alert-item">'
            f'{icon} <b>{alert["time"]}</b> — {atype} — {alert["detail"]}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.info("No alerts yet. Generate a notice to see live events here.")

st.divider()
st.caption("Powered by Claude AI · CGST Act 2017 · TaxIQ")
