# TaxIQ — India’s Unified Tax Intelligence Agent

TaxIQ is a single app that combines three agents:
1. **GST Invoice OCR Agent**: invoice photo/PDF → OCR → structured invoice → **GSTR‑1 JSON**
2. **ITC Fraud Detection Agent**: Knowledge graph → cycle detection → risk scores + graph visualization
3. **Personal Tax Saver Agent**: Bank CSV → classification → 80C/80D gaps → old vs new regime + PDF report

## Architecture (ASCII)

```
Streamlit UI (frontend/)
   |
   | HTTP (httpx)
   v
FastAPI (backend/main.py)
   |-- OCR (pytesseract + opencv)
   |-- LLM (Claude via Anthropic API) [optional]
   |-- Neo4j graph (neo4j driver) [optional]
   |-- networkx fallback (in-memory) [if Neo4j down]
   |-- PostgreSQL (SQLAlchemy) [optional]
   |-- fpdf2 (PDF report)
```

## Quick start

**Python requirement:** Python **3.11** (these pinned package versions are not compatible with Python 3.13).

### Quick start (5 commands)

```bash
cd taxiq
docker compose up -d
py -3.11 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\uvicorn.exe backend.main:app --reload --port 8000
```

Then (new terminal):

```bash
cd taxiq
.\.venv\Scripts\streamlit.exe run frontend\app.py
```

### Notes

- If Neo4j/Postgres aren’t running, TaxIQ still works in **DEMO mode** (networkx + in-memory fallbacks).

## API keys setup

- **Anthropic Claude**: create key in [Anthropic Console](https://console.anthropic.com/) and set `ANTHROPIC_API_KEY` in `.env`
- **Neo4j**: local docker uses `neo4j/taxiq123` at `bolt://localhost:7687`
- **Neo4j Browser**: `http://localhost:7474`

If keys/services are missing, TaxIQ runs in **DEMO mode** and clearly labels outputs as `[DEMO DATA]`.

## Demo walkthrough (judges)

1. Open Streamlit landing page → check KPI metrics
2. GST Filing → upload sample invoice → **Process Invoice** → view parsed invoice + GSTR‑1 entry → add to return → download JSON
3. Fraud Graph → **Load Sample Fraud Data** → view pyvis network → run detection → view circular chains + top risky GSTINs
4. Tax Saver → upload sample bank CSV → analyze → see regime comparison + gaps chart + Claude advice + download PDF

## Mock data

- `data/sample_bank_statements/bank_statement.csv`: 90 rows Jan–Mar 2024 (salary/rent/LIC/ELSS/PPF/insurance + realistic spends)
- `data/mock_gstn/fraud_network.json`: deterministic fraud scenarios
- `data/sample_invoices/`: invoice JPGs are **auto-generated on first run** if missing (so the repo stays text-only)

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Streamlit multi-page |
| Backend | FastAPI + Uvicorn |
| OCR | pytesseract + Pillow + OpenCV |
| LLM | Anthropic Claude (`claude-opus-4-6`) |
| Graph | Neo4j driver + networkx fallback |
| SQL | PostgreSQL + SQLAlchemy |
| Viz | Plotly (dark), pyvis |
| Reports | fpdf2 |
| Config | python-dotenv |

