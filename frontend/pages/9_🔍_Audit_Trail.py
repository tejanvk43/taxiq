"""
TaxIQ — 🔍 Explainable Audit Trail Generator
Multi-hop graph traversal with natural language explanations for audit support.
"""
import os
import sys

import httpx
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import inject_css, api_post, api_get, fmt_inr, BACKEND_URL, CHART_LAYOUT, COLORS

st.set_page_config(page_title="TaxIQ | Audit Trail", page_icon="🔍", layout="wide")
inject_css()

# ── Page Header ─────────────────────────────────────────
st.markdown('<div class="page-title">🔍 Explainable Audit Trail Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Multi-hop graph traversal · Natural language explanations · Legal section references · CGST Act 2017</div>', unsafe_allow_html=True)

# ── Input ───────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    gstin = st.text_input("GSTIN", value="27AADCB2230M1ZT", max_chars=15)
with col2:
    period = st.selectbox("Period", [
        "2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06",
        "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    ], index=0)
with col3:
    st.write("")
    st.write("")
    run_btn = st.button("🔍 Generate Audit Trail", use_container_width=True, type="primary")

# ── Run audit ───────────────────────────────────────────
if run_btn:
    with st.spinner("Running multi-hop graph traversal and generating explainable audit trail..."):
        try:
            r = api_post("/api/audit/generate", json_body={
                "gstin": gstin,
                "period": period,
            })
            if r.status_code == 200:
                st.session_state["audit_result"] = r.json()
            else:
                st.error(f"Backend returned HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            st.error(f"Could not reach backend: {e}")

# ── Display Results ─────────────────────────────────────
result = st.session_state.get("audit_result")
if not result:
    st.info("Enter a GSTIN and click **Generate Audit Trail** to create an explainable multi-hop audit report.")
    st.stop()

trails = result.get("trails", [])
st.divider()

# ── Summary Metrics ─────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Mismatches", result.get("total_trails", 0))
m2.metric("ITC At Risk", fmt_inr(result.get("total_amount_at_risk", 0)))
risk_summary = result.get("risk_summary", {})
m3.metric("🔴 HIGH Risk", risk_summary.get("HIGH", 0))
m4.metric("🟡 MEDIUM Risk", risk_summary.get("MEDIUM", 0))
m5.metric("🟢 LOW Risk", risk_summary.get("LOW", 0))

st.divider()

# ── Risk Distribution Chart ─────────────────────────────
st.markdown("### Risk Distribution")

left_chart, right_chart = st.columns([1, 1])

with left_chart:
    # Mismatch type breakdown
    type_counts = {}
    for t in trails:
        mt = t.get("mismatch_type", "Unknown")
        type_counts[mt] = type_counts.get(mt, 0) + 1

    if type_counts:
        fig_bar = go.Figure(go.Bar(
            y=list(type_counts.keys()),
            x=list(type_counts.values()),
            orientation="h",
            marker_color=[COLORS["red"], COLORS["accent"], COLORS["yellow"],
                          COLORS["blue"], COLORS["purple"]][:len(type_counts)],
            text=list(type_counts.values()),
            textposition="auto",
        ))
        fig_bar.update_layout(
            **CHART_LAYOUT,
            height=280,
            xaxis_title="Count",
            title=dict(text="Mismatches by Type", font=dict(size=14)),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with right_chart:
    # Risk level pie
    if risk_summary:
        labels = []
        values = []
        colors = []
        for level, color in [("HIGH", COLORS["red"]), ("MEDIUM", COLORS["yellow"]), ("LOW", COLORS["green"])]:
            if risk_summary.get(level, 0) > 0:
                labels.append(level)
                values.append(risk_summary[level])
                colors.append(color)

        if values:
            fig_pie = go.Figure(go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors),
                hole=0.55,
                textinfo="label+value",
                textfont=dict(color="#F8F9FA"),
            ))
            fig_pie.update_layout(
                **CHART_LAYOUT,
                height=280,
                showlegend=False,
                title=dict(text="Risk Level Distribution", font=dict(size=14)),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ── Detailed Audit Trails ──────────────────────────────
st.markdown("### 📋 Detailed Audit Trails")

for idx, trail in enumerate(trails):
    inv_id = trail.get("invoice_id", "")
    mm_type = trail.get("mismatch_type", "")
    risk = trail.get("risk_level", "MEDIUM")
    amount = trail.get("amount_at_risk", 0)

    risk_icons = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢", "CRITICAL": "🔴"}
    risk_icon = risk_icons.get(risk, "⚪")

    with st.expander(f"{risk_icon} {inv_id} — {mm_type} — {fmt_inr(amount)} at risk", expanded=(idx == 0)):

        # ── Natural Language Explanation ────────────────
        st.markdown("#### 💬 Natural Language Explanation")
        nl = trail.get("nl_explanation", "")
        st.markdown(
            f'<div class="tiq-card" style="border-left: 4px solid {COLORS["accent"]}">{nl}</div>',
            unsafe_allow_html=True,
        )

        st.write("")

        # ── Multi-Hop Graph Trail ──────────────────────
        st.markdown("#### 🔗 Multi-Hop Graph Traversal")

        hops = trail.get("hops", [])
        for hop in hops:
            status = hop.get("status", "PASS")
            status_map = {
                "PASS": ("✅", "audit-icon-pass", COLORS["green"]),
                "FAIL": ("❌", "audit-icon-fail", COLORS["red"]),
                "WARN": ("⚠️", "audit-icon-warn", COLORS["yellow"]),
            }
            icon, css_class, color = status_map.get(status, ("❓", "audit-icon-warn", COLORS["yellow"]))

            st.markdown(
                f'<div class="audit-hop">'
                f'<div class="audit-icon {css_class}">{icon}</div>'
                f'<div style="flex:1">'
                f'<div style="font-weight:700;color:{color};margin-bottom:2px">'
                f'Hop {hop.get("hop", "")} — {hop.get("node", "")}'
                f'<span class="pill pill-{"green" if status=="PASS" else "red" if status=="FAIL" else "yellow"}" '
                f'style="margin-left:8px">{status}</span></div>'
                f'<div style="color:var(--text);font-size:14px;line-height:1.6">{hop.get("detail", "")}</div>'
                f'<div style="color:var(--text-muted);font-size:12px;margin-top:4px">'
                f'Source: {hop.get("data_source", "")}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.write("")

        # ── Root Cause & Legal References ──────────────
        left_info, right_info = st.columns(2)

        with left_info:
            st.markdown("#### 🎯 Root Cause Analysis")
            st.markdown(
                f'<div class="tiq-card" style="border-left:4px solid {COLORS["red"]}">'
                f'{trail.get("root_cause", "Unknown")}</div>',
                unsafe_allow_html=True,
            )

        with right_info:
            st.markdown("#### 📚 Legal References")
            legal_refs = trail.get("legal_references", [])
            for ref in legal_refs:
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px solid var(--border)">'
                    f'<span style="color:{COLORS["accent"]};font-weight:700">{ref.get("section", "")}</span>'
                    f' — {ref.get("title", "")}'
                    f'<br><small style="color:var(--text-muted)">{ref.get("relevance", "")}</small></div>',
                    unsafe_allow_html=True,
                )

        st.write("")

        # ── Recommended Actions ────────────────────────
        st.markdown("#### ✅ Recommended Actions")
        actions = trail.get("recommended_actions", [])
        for act in actions:
            priority = act.get("priority", "MEDIUM")
            p_color = {"HIGH": COLORS["red"], "MEDIUM": COLORS["yellow"], "LOW": COLORS["green"]}.get(priority, COLORS["yellow"])
            st.markdown(
                f'<div class="tiq-card" style="border-left:4px solid {p_color};padding:12px 16px">'
                f'<span class="pill pill-{"red" if priority=="HIGH" else "yellow" if priority=="MEDIUM" else "green"}">'
                f'{priority}</span> '
                f'<strong>{act.get("action", "")}</strong>'
                f'<br><span style="color:var(--text-muted);font-size:13px">{act.get("detail", "")}</span></div>',
                unsafe_allow_html=True,
            )

        st.write("")

        # ── Timeline ───────────────────────────────────
        st.markdown("#### 📅 Event Timeline")
        timeline = trail.get("timeline", [])
        for ev in timeline:
            ev_status = ev.get("status", "pending")
            ev_color = {
                "done": COLORS["green"], "failed": COLORS["red"],
                "current": COLORS["accent"], "pending": COLORS["yellow"],
            }.get(ev_status, COLORS["yellow"])
            ev_icon = {
                "done": "✅", "failed": "❌", "current": "🔄", "pending": "⏳",
            }.get(ev_status, "⏳")

            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;padding:6px 0;'
                f'border-left:3px solid {ev_color};padding-left:12px;margin-bottom:4px">'
                f'{ev_icon} <strong>{ev.get("event", "")}</strong>'
                f'<span style="color:var(--text-muted);margin-left:auto">{ev.get("date", "")}</span></div>',
                unsafe_allow_html=True,
            )

st.divider()

# ── Download Audit Report ───────────────────────────────
st.markdown("### 📥 Export Audit Report")

report_lines = [
    "=" * 70,
    "TaxIQ — EXPLAINABLE AUDIT TRAIL REPORT",
    "=" * 70,
    f"GSTIN: {result.get('gstin', '')}",
    f"Period: {result.get('period', '')}",
    f"Generated: {result.get('report_generated_at', '')}",
    f"Legal Framework: {result.get('legal_framework', '')}",
    f"Total Mismatches: {result.get('total_trails', 0)}",
    f"Total ITC At Risk: ₹{result.get('total_amount_at_risk', 0):,.0f}",
    "",
]

for idx, trail in enumerate(trails):
    report_lines.append("-" * 70)
    report_lines.append(f"MISMATCH #{idx+1}: {trail.get('invoice_id', '')}")
    report_lines.append(f"Type: {trail.get('mismatch_type', '')}")
    report_lines.append(f"Risk Level: {trail.get('risk_level', '')}")
    report_lines.append(f"Amount at Risk: ₹{trail.get('amount_at_risk', 0):,.0f}")
    report_lines.append("")
    report_lines.append("EXPLANATION:")
    report_lines.append(trail.get("nl_explanation", "").replace("**", ""))
    report_lines.append("")
    report_lines.append("ROOT CAUSE:")
    report_lines.append(trail.get("root_cause", ""))
    report_lines.append("")
    report_lines.append("GRAPH TRAVERSAL HOPS:")
    for hop in trail.get("hops", []):
        report_lines.append(f"  [{hop.get('status','')}] Hop {hop.get('hop','')}: {hop.get('node','')} — {hop.get('detail','')}")
    report_lines.append("")
    report_lines.append("LEGAL REFERENCES:")
    for ref in trail.get("legal_references", []):
        report_lines.append(f"  {ref.get('section','')} — {ref.get('title','')}: {ref.get('relevance','')}")
    report_lines.append("")
    report_lines.append("RECOMMENDED ACTIONS:")
    for act in trail.get("recommended_actions", []):
        report_lines.append(f"  [{act.get('priority','')}] {act.get('action','')}: {act.get('detail','')}")
    report_lines.append("")

report_text = "\n".join(report_lines)

b1, b2 = st.columns(2)
with b1:
    st.download_button(
        "📄 Download Full Report (TXT)",
        data=report_text,
        file_name=f"audit_trail_{gstin}_{period}.txt",
        mime="text/plain",
        use_container_width=True,
    )
with b2:
    if st.button("📋 Copy to Clipboard", use_container_width=True):
        st.code(report_text[:500] + "...", language=None)
        st.toast("Report text ready to copy!", icon="📋")

st.caption("Powered by TaxIQ Audit Engine · Multi-hop Graph Traversal · CGST Act 2017 · Rule 36(4)")
