# TaxIQ — India's Unified Tax Intelligence Platform

TaxIQ is a single platform combining **7 intelligent modules** for end-to-end GST compliance, fraud detection, tax optimization, and vendor risk management — plus a **WhatsApp bot** for Kirana-store owners and **cross-layer GST?ITR deduction discovery**.

## Modules

1. **?? GST Invoice OCR Agent** — Invoice photo/PDF ? OCR ? structured invoice ? **GSTR-1 JSON**
2. **??? ITC Fraud Detection Agent** — Knowledge graph ? cycle detection ? shell company topology ? risk scores + interactive graph
3. **?? Personal Tax Saver Agent** — Bank CSV ? classification ? 80C/80D gaps ? old vs new regime + **hidden deductions from GST data** + **investment calendar** + PDF report
4. **?? GSTR Reconciliation** — GSTR-1 vs GSTR-2B comparison ? 5 mismatch types (TYPE_1–5) ? audit trail
5. **?? NEXUS Vendor Scores** — 5-factor compliance scoring ? AAA–D grades ? radar charts ? OCEN loan eligibility
6. **?? AI Notice Generator** — LLM-powered GST notice/SCN drafting under CGST Act 2017 ? PDF download ? live alerts
7. **?? ITC Recovery Pipeline** — Kanban-style tracking: At Risk ? In Progress ? Recovered ? funnel + trend charts
8. **?? WhatsApp Bot** — Vernacular GST filing for Kirana stores via Twilio (image ? OCR ? confirm ? file)
9. **?? Cross-Layer Enricher** — Scans GST invoices (HSN codes) to discover missed ITR deductions (80C/80D/24b)
10. **?? Investment Calendar** — Month-by-month plan to fill 80C/80D gaps before March 31

## Architecture

```
+-----------------------------------------------------------------+
¦                      PRESENTATION LAYER                        ¦
¦  Streamlit Multi-Page App (7 pages + landing)                  ¦
¦  +------++------++------++------++------++------++------+     ¦
¦  ¦ OCR  ¦¦Fraud ¦¦ Tax  ¦¦Recon ¦¦Vendor¦¦Notice¦¦ ITC  ¦     ¦
¦  ¦Filing¦¦Graph ¦¦Saver ¦¦cile  ¦¦Score ¦¦Gen AI¦¦Recov ¦     ¦
¦  +------++------++------++------++------++------++------+     ¦
+-----+-------+-------+-------+-------+-------+-------+----------+
      ¦       ¦       ¦       ¦       ¦       ¦       ¦
      ?       ?       ?       ?       ?       ?       ?
+-----------------------------------------------------------------+
¦                     APPLICATION LAYER                          ¦
¦  FastAPI  (8 direct routes + 18 api_router + 3 WhatsApp = 29)  ¦
¦  +----------------+  +--------------------------------------+  ¦
¦  ¦ TaxIQ Agents   ¦  ¦ NEXUS Core Engines                   ¦  ¦
¦  ¦ • GST Agent    ¦  ¦ • NEXUSScorer (5-factor)              ¦  ¦
¦  ¦ • Fraud Agent  ¦  ¦ • ReconciliationEngine (5 types)      ¦  ¦
¦  ¦ • Tax Saver    ¦  ¦ • FraudDetector (cycle + shell)       ¦  ¦
¦  ¦ • OCR Pipeline ¦  ¦ • NoticeGenerator (LLM)               ¦  ¦
¦  ¦ • LLM Client   ¦  ¦ • ITCRecovery (pipeline)              ¦  ¦
¦  +----------------+  ¦ • CrossLayerEnricher (GST?ITR)        ¦  ¦
¦                      ¦ • InvestmentCalendar                   ¦  ¦
¦                      +--------------------------------------+  ¦
¦  +--------------+ +--------------+ +----------------------+   ¦
¦  ¦ GSTN Client  ¦ ¦ WebSocket    ¦ ¦ Celery + Redis       ¦   ¦
¦  ¦ (mock/real)  ¦ ¦ (live alerts)¦ ¦ (async task queue)   ¦   ¦
¦  +--------------+ +--------------+ +----------------------+   ¦
¦  +----------------------------------------------------------+  ¦
¦  ¦ WhatsApp Bot (Twilio webhook ? state machine ? OCR)      ¦  ¦
¦  +----------------------------------------------------------+  ¦
+-----------------------------------------------------------------+
      ¦               ¦               ¦
      ?               ?               ?
+-----------------------------------------------------------------+
¦                       DATA LAYER                               ¦
¦  +----------+  +----------+  +----------+  +----------+       ¦
¦  ¦PostgreSQL¦  ¦  Neo4j   ¦  ¦  Redis   ¦  ¦networkx  ¦       ¦
¦  ¦  (SQL)   ¦  ¦ (graph)  ¦  ¦ (cache)  ¦  ¦(fallback)¦       ¦
¦  ¦ optional ¦  ¦ optional ¦  ¦ optional ¦  ¦ built-in ¦       ¦
¦  +----------+  +----------+  +----------+  +----------+       ¦
+-----------------------------------------------------------------+
```

## Quick Start

**Python requirement:** Python **3.11** (pinned packages are not compatible with 3.13).

### 5-Command Setup

```bash
cd taxiq
docker compose up -d          # Postgres + Neo4j + Redis
py -3.11 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\uvicorn.exe backend.main:app --reload --port 8000
```

Then (new terminal):

```bash
cd taxiq
.\.venv\Scripts\streamlit.exe run frontend\app.py
```

### Optional: Celery Workers

```bash
celery -A backend.tasks.celery_app worker --loglevel=info
celery -A backend.tasks.celery_app beat --loglevel=info
```

### Notes

- If Neo4j/Postgres/Redis aren't running, TaxIQ still works in **DEMO mode** (networkx + in-memory fallbacks).
- All NEXUS endpoints serve deterministic demo data and don't require external services.
- Every Streamlit page has a `[DEMO DATA]` badge when running without backend services.

## API Keys Setup

| Key | Source | Required? |
|-----|--------|-----------|
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com/) | Optional (demo mode without) |
| `NEO4J_*` | Local Docker | Optional (networkx fallback) |
| `DATABASE_URL` | Local Docker | Optional (in-memory fallback) |
| `REDIS_URL` | Local Docker | Optional (Celery won't run) |
| `GSTN_API_KEY` | GSP Provider | Optional (mock GSTN client) |
| `TWILIO_ACCOUNT_SID` | [Twilio Console](https://console.twilio.com/) | Optional (mock WhatsApp) |
| `TWILIO_AUTH_TOKEN` | Twilio Console | Optional |
| `TWILIO_WHATSAPP_NUMBER` | Twilio Sandbox | Optional |

If keys/services are missing, TaxIQ runs in **DEMO mode** and clearly labels outputs as `[DEMO DATA]`.

## API Endpoints (29 total)

### Original TaxIQ (direct routes — 8 routes)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | GET | `/health` | Health check |
| 2 | POST | `/gst/process-invoice` | OCR + parse invoice |
| 3 | GET | `/gst/gstr1-return` | Build GSTR-1 JSON |
| 4 | POST | `/fraud/load-mock` | Load sample fraud network |
| 5 | POST | `/fraud/run` | Run cycle detection |
| 6 | GET | `/fraud/graph-data` | Get pyvis visualization data |
| 7 | POST | `/tax/analyze` | Tax savings analysis |
| 8 | POST | `/tax/report-pdf` | Download PDF report |

### NEXUS GST (api_router — 18 routes)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 9 | GET | `/api/graph/traverse/{gstin}` | Invoice chain traversal |
| 10 | GET | `/api/graph/network/{gstin}` | Network topology |
| 11 | GET | `/api/graph/fraud-rings` | Fraud ring detection |
| 12 | POST | `/api/graph/shortest-path` | Shortest path between GSTINs |
| 13 | GET | `/api/fraud/rings` | Circular trading rings |
| 14 | GET | `/api/fraud/shell-companies` | Shell company detection |
| 15 | POST | `/api/reconcile/run` | Run GSTR reconciliation |
| 16 | GET | `/api/reconcile/status/{job_id}` | Reconciliation job status |
| 17 | GET | `/api/reconcile/mismatches/{gstin}` | List mismatches (filterable) |
| 18 | GET | `/api/reconcile/audit-trail/{id}` | 5-hop document trail |
| 19 | GET | `/api/vendors/score/{gstin}` | NEXUS compliance score |
| 20 | GET | `/api/vendors/list` | All vendors (filterable) |
| 21 | GET | `/api/vendors/{gstin}/history` | Score history |
| 22 | POST | `/api/notices/generate` | AI notice draft |
| 23 | GET | `/api/notices/{id}/pdf` | Download notice PDF |
| 24 | POST | `/api/notices/{id}/send` | Send notice via email |
| 25 | GET | `/api/recovery/pipeline` | ITC recovery Kanban |
| 26 | WS | `/ws/alerts/{gstin}` | Real-time alerts stream |

### WhatsApp Bot (3 routes)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 27 | POST | `/whatsapp/webhook` | Twilio incoming webhook (TwiML) |
| 28 | GET | `/whatsapp/test` | Test bot with simulated message |
| 29 | GET | `/whatsapp/status` | Bot status + stats |

## Demo Walkthrough for Judges (5 minutes)

> **Pre-requisite:** Backend running on `:8000`, Streamlit on `:8501`.
> All pages work in **DEMO mode** — no external services needed.

| Time | Page | Exact Steps |
|------|------|-------------|
| 0:00–0:30 | **Landing** (`app.py`) | Point out 7 KPI cards, system status pills, dark navy + saffron theme. |
| 0:30–1:15 | **?? GST Filing** | Upload any invoice image/PDF ? click **Process Invoice** ? see OCR-parsed fields. Click **Build GSTR-1** ? download JSON. |
| 1:15–2:00 | **??? Fraud Graph** | Click **Load Sample Data** ? click **Run Detection** ? explore interactive network graph. Note flagged circular rings and shell companies. |
| 2:00–2:45 | **?? Tax Saver** | Upload `data/sample_bank_statements/bank_statement.csv` ? click **Analyze** ? see regime comparison + gap analysis + **Hidden Deductions** section + **Investment Calendar** with Gantt chart. |
| 2:45–3:15 | **?? Reconciliation** | Enter GSTIN ? select period ? click **Run Reconciliation** ? view 5 mismatch types (metric cards + bar chart + audit trail expanders). |
| 3:15–3:45 | **?? Vendor Scores** | Click **Load All Vendors** ? scroll scorecard grid (AAA–D grade badges, radar charts, loan eligibility). Drill-down ? score breakdown + history chart. |
| 3:45–4:15 | **?? Notice Generator** | Fill form ? click **Generate Notice** ? read formatted SCN draft. Click **Send Email** (toast) or **Download PDF**. See live GSTN alerts below. |
| 4:15–4:45 | **?? ITC Recovery** | View Kanban board (3 columns with action buttons). Note funnel chart + 6-month recovery trend line. |
| 4:45–5:00 | **Wrap-up** | Highlight: works offline in DEMO mode, 29 API endpoints, WhatsApp bot, cross-layer GST?ITR, investment calendar, Claude AI optional. |

## What Makes TaxIQ Unique

| Feature | Why It Matters |
|---------|---------------|
| **Cross-Layer Enricher** | No other tool scans GST invoices to find missed ITR deductions (80C/80D). This bridges GST and ITR intelligently. |
| **WhatsApp Bot** | Kirana store owners can file GST by sending invoice photos on WhatsApp — in Hindi. No app download needed. |
| **Investment Calendar** | Month-by-month actionable plan to fully utilize 80C/80D limits before March 31. |
| **NEXUS 5-Factor Scoring** | Goes beyond simple compliance — measures filing regularity, ITC accuracy, turnover consistency, network trust, amendment frequency. |
| **5 Mismatch Types** | TYPE_1 (Missing), TYPE_2 (Value), TYPE_3 (Rate), TYPE_4 (GSTIN), TYPE_5 (Period) — comprehensive reconciliation. |
| **Kanban ITC Recovery** | Visual pipeline from mismatch detection to recovered amount, with actionable buttons at each stage. |
| **Full DEMO Mode** | Every page works without any external service. `[DEMO DATA]` badges make it clear for judges. |

## Mock Data

| File | Description |
|------|-------------|
| `data/sample_bank_statements/bank_statement.csv` | 90 rows, Jan–Mar 2024 (salary, rent, LIC, ELSS, PPF, insurance + spending) |
| `data/mock_gstn/fraud_network.json` | 22 GSTINs, 20 ITC edges, 5-node circular ring + star patterns |
| `data/mock_gstn/gstr1_mock.json` | 10 invoices with HSN codes for reconciliation demo |
| `data/mock_gstn/gstr2b_mock.json` | Same invoices with intentional mismatches (TYPE_1, TYPE_2, TYPE_4) |
| `data/mock_gstn/purchase_register.csv` | 15 purchase rows for cross-referencing |
| `data/sample_invoices/` | Auto-generated JPGs on first run (repo stays text-only) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit multi-page (7 pages + landing) |
| Backend | FastAPI + Uvicorn (29 endpoints) |
| OCR | pytesseract + Pillow + OpenCV |
| LLM | Anthropic Claude (claude-opus-4-6) |
| Graph | Neo4j driver + networkx fallback |
| SQL | PostgreSQL + SQLAlchemy |
| Task Queue | Celery + Redis |
| Real-time | WebSocket (per-GSTIN alerts) |
| WhatsApp | Twilio API (mock mode without creds) |
| Visualization | Plotly (dark theme), pyvis |
| Reports | fpdf2 |
| ML | scikit-learn (risk scoring) |
| Config | python-dotenv |

## Docker Services

| Service | Image | Ports |
|---------|-------|-------|
| postgres | postgres:16-alpine | 5432 |
| neo4j | neo4j:5.17 + APOC | 7474, 7687 |
| redis | redis:7-alpine | 6379 |
| celery_worker | app image | — |
| celery_beat | app image | — |

## Graph Database

Neo4j schema files are in `graph-db/`:
- `schema/constraints.cypher` — uniqueness constraints
- `schema/schema.cypher` — 10 node labels, 10 relationship types, 4 indexes
- `seed/seed_data.cypher` — demo taxpayers, invoices, fraud cluster
