"""
TaxIQ — Unified Design System
Shared CSS, helpers, and layout utilities for all Streamlit pages.
"""
import os
import httpx

BACKEND_URL = os.getenv("TAXIQ_BACKEND_URL", "http://localhost:8000")

# ── Indian Rupee formatter ──────────────────────────────
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


def fmt_inr(n):
    """Compact INR formatter for large values."""
    if n >= 1e7:  return f"₹{n/1e7:.1f}Cr"
    if n >= 1e5:  return f"₹{n/1e5:.1f}L"
    return f"₹{n:,.0f}"


# ── API helpers ─────────────────────────────────────────
def api_get(path: str, params=None, timeout: int = 30):
    with httpx.Client(timeout=timeout) as c:
        return c.get(f"{BACKEND_URL}{path}", params=params)


def api_post(path: str, json_body=None, files=None, data=None, timeout: int = 60):
    with httpx.Client(timeout=timeout) as c:
        return c.post(f"{BACKEND_URL}{path}", json=json_body, files=files, data=data)


# ── Master CSS ──────────────────────────────────────────
TAXIQ_CSS = """
<style>
/* ───── Base Dark Theme ───── */
:root {
    --bg-primary:   #0A1628;
    --bg-card:      #0D1F3C;
    --bg-card-alt:  #111D35;
    --border:       #1E3A5F;
    --accent:       #FF9933;
    --accent-glow:  rgba(255,153,51,0.15);
    --green:        #00B894;
    --green-glow:   rgba(0,184,148,0.15);
    --red:          #D63031;
    --red-glow:     rgba(214,48,49,0.12);
    --yellow:       #FDCB6E;
    --yellow-glow:  rgba(253,203,110,0.15);
    --blue:         #74B9FF;
    --text:         #F8F9FA;
    --text-muted:   #8899AA;
    --radius:       12px;
    --radius-sm:    8px;
}

.stApp,
section.main,
div[data-testid="stAppViewContainer"] {
    background-color: var(--bg-primary) !important;
    color: var(--text);
}
div[data-testid="stHeader"] {
    background: rgba(10,22,40,0.85) !important;
    backdrop-filter: blur(12px);
}

/* ───── Sidebar ───── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #070F1E 0%, #0D1F3C 100%) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span {
    color: var(--text-muted) !important;
}

/* ───── Metric Cards ───── */
div[data-testid="metric-container"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: var(--radius);
    padding: 16px 20px;
    transition: border-color 0.2s, box-shadow 0.2s;
}
div[data-testid="metric-container"]:hover {
    border-color: var(--accent);
    box-shadow: 0 0 20px var(--accent-glow);
}
div[data-testid="metric-container"] label {
    color: var(--text-muted) !important;
    font-size: 13px !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-weight: 700;
}

/* ───── Buttons ───── */
.stButton > button {
    background: linear-gradient(135deg, #FF9933, #E67E22) !important;
    color: var(--bg-primary) !important;
    font-weight: 700 !important;
    border-radius: var(--radius-sm) !important;
    border: none !important;
    padding: 10px 24px !important;
    transition: transform 0.15s, box-shadow 0.2s !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 13px !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px var(--accent-glow) !important;
}
.stButton > button:active {
    transform: translateY(0px);
}

/* ───── DataFrames ───── */
.stDataFrame,
div[data-testid="stDataFrame"] {
    background: var(--bg-card) !important;
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
}

/* ───── Expanders ───── */
div[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}

/* ───── Tabs ───── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm);
    color: var(--text-muted);
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: var(--bg-primary) !important;
}

/* ───── Text Inputs / Selects ───── */
.stTextInput input,
.stNumberInput input,
.stSelectbox > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
}
.stTextInput input:focus,
.stNumberInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
}

/* ───── Progress bars ───── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--accent), var(--green)) !important;
    border-radius: 4px;
}

/* ───── Dividers ───── */
hr {
    border-color: var(--border) !important;
    opacity: 0.5;
}

/* ───── Info / Success / Warning / Error boxes ───── */
div[data-testid="stAlert"] {
    border-radius: var(--radius) !important;
    border: none !important;
}

/* ───── Section Headers ───── */
.section-header {
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    padding-bottom: 8px;
    margin-bottom: 16px;
    border-bottom: 2px solid var(--accent);
    display: flex;
    align-items: center;
    gap: 10px;
}

/* ───── Card Components ───── */
.tiq-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 12px;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.tiq-card:hover {
    border-color: var(--accent);
    box-shadow: 0 4px 20px var(--accent-glow);
}

/* ───── Grade Badges ───── */
.grade-aaa { background: var(--green); color: var(--bg-primary); padding: 4px 14px;
             border-radius: 6px; font-weight: 800; font-size: 16px; }
.grade-a   { background: var(--yellow); color: var(--bg-primary); padding: 4px 14px;
             border-radius: 6px; font-weight: 800; font-size: 16px; }
.grade-b   { background: var(--accent); color: var(--bg-primary); padding: 4px 14px;
             border-radius: 6px; font-weight: 800; font-size: 16px; }
.grade-d   { background: var(--red); color: var(--text); padding: 4px 14px;
             border-radius: 6px; font-weight: 800; font-size: 16px; }

/* ───── Status Pills ───── */
.pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 6px;
}
.pill-green  { background: var(--green-glow); border: 1px solid var(--green); color: var(--green); }
.pill-red    { background: var(--red-glow);   border: 1px solid var(--red);   color: var(--red); }
.pill-yellow { background: var(--yellow-glow);border: 1px solid var(--yellow);color: var(--yellow); }
.pill-blue   { background: rgba(116,185,255,.15); border: 1px solid var(--blue); color: var(--blue); }

/* ───── Kanban Headers ───── */
.kanban-header-risk { background: var(--red); color:#FFF; padding:8px 16px;
                      border-radius: var(--radius) var(--radius) 0 0; font-weight:700;
                      font-size: 14px; letter-spacing: 0.3px; }
.kanban-header-prog { background: var(--yellow); color: var(--bg-primary); padding:8px 16px;
                      border-radius: var(--radius) var(--radius) 0 0; font-weight:700;
                      font-size: 14px; }
.kanban-header-done { background: var(--green); color: var(--bg-primary); padding:8px 16px;
                      border-radius: var(--radius) var(--radius) 0 0; font-weight:700;
                      font-size: 14px; }

/* ───── Notice Box ───── */
.notice-box {
    background: var(--bg-card);
    border: 1px solid var(--accent);
    border-radius: var(--radius);
    padding: 28px;
    font-family: Georgia, 'Times New Roman', serif;
    line-height: 1.9;
    color: var(--text);
    white-space: pre-wrap;
}
.notice-header {
    text-align: center;
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
    border-bottom: 2px solid var(--accent);
    padding-bottom: 12px;
    margin-bottom: 20px;
}

/* ───── Alert Cards ───── */
.alert-card {
    background: var(--bg-card);
    border-left: 4px solid var(--red);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 12px 16px;
    margin: 8px 0;
    transition: background 0.2s;
}
.alert-card:hover {
    background: var(--bg-card-alt);
}

/* ───── Audit Trail ───── */
.audit-hop {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid var(--border);
}
.audit-hop:last-child { border-bottom: none; }
.audit-icon {
    width: 36px; height: 36px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
}
.audit-icon-pass { background: var(--green-glow); border: 2px solid var(--green); }
.audit-icon-fail { background: var(--red-glow);   border: 2px solid var(--red); }
.audit-icon-warn { background: var(--yellow-glow);border: 2px solid var(--yellow); }

/* ───── File Upload ───── */
.stFileUploader {
    background: var(--bg-card) !important;
    border: 2px dashed var(--border) !important;
    border-radius: var(--radius) !important;
}

/* ───── Scrollbar ───── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ───── Page Title ───── */
.page-title {
    font-size: 32px;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), #E67E22);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}
.page-subtitle {
    color: var(--text-muted);
    font-size: 14px;
    margin-bottom: 20px;
}

/* ───── Ingestion Cards ───── */
.ingest-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    text-align: center;
    transition: all 0.2s;
}
.ingest-card:hover {
    border-color: var(--accent);
    box-shadow: 0 8px 32px var(--accent-glow);
    transform: translateY(-2px);
}
.ingest-icon {
    font-size: 48px;
    margin-bottom: 12px;
}
.ingest-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 4px;
}
.ingest-desc {
    font-size: 13px;
    color: var(--text-muted);
}
</style>
"""


def inject_css():
    """Inject the unified TaxIQ CSS into the current Streamlit page."""
    import streamlit as st
    st.markdown(TAXIQ_CSS, unsafe_allow_html=True)


# ── Chart theme defaults ────────────────────────────────
CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0A1628",
    plot_bgcolor="#0D1F3C",
    font_color="#F8F9FA",
    font=dict(family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=20, b=20),
)

COLORS = {
    "accent":  "#FF9933",
    "green":   "#00B894",
    "red":     "#D63031",
    "yellow":  "#FDCB6E",
    "blue":    "#74B9FF",
    "purple":  "#A29BFE",
    "pink":    "#FD79A8",
}
