from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger

from backend.agents.fraud_agent import FraudAgent
from backend.agents.gst_agent import GSTAgent
from backend.agents.tax_saver_agent import TaxSaverAgent
from backend.database.postgres_client import postgres_client
from backend.graph.mock_data_loader import load_mock_fraud_data
from backend.utils.pdf_generator import generate_tax_report_pdf
from backend.utils.sample_data import ensure_sample_data


app = FastAPI(title="TaxIQ Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    ensure_sample_data()
    try:
        postgres_client.init_schema()
    except Exception as e:
        logger.warning("Postgres init skipped (not reachable): {}", str(e))


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "service": "taxiq-backend"}


@app.post("/gst/process-invoice")
async def gst_process_invoice(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only jpg/png/pdf supported")

    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / f"upload{suffix}"
        out_path.write_bytes(await file.read())

        agent = GSTAgent()
        result = await agent.process_invoice(str(out_path))

        # build return totals for the buyer gstin if present
        buyer = result["invoice"].get("buyer_gstin") or "27AAACG1000A1Z5"
        period = str(result["invoice"].get("invoice_date", "2024-01-01"))[:7]
        result["gstr1_return_preview"] = agent.build_gstr1_return(user_gstin=buyer, period=period)
        return result


@app.get("/gst/gstr1-return")
async def gst_build_return(user_gstin: str, period: str) -> Dict[str, Any]:
    agent = GSTAgent()
    return agent.build_gstr1_return(user_gstin=user_gstin, period=period)


@app.post("/fraud/load-mock")
async def fraud_load_mock() -> Dict[str, Any]:
    return await load_mock_fraud_data()


@app.post("/fraud/run")
async def fraud_run_detection() -> Dict[str, Any]:
    agent = FraudAgent()
    return await agent.run_detection()


@app.get("/fraud/graph-data")
async def fraud_graph_data() -> Dict[str, Any]:
    agent = FraudAgent()
    return await agent.get_graph_visualization_data()


@app.post("/tax/analyze")
async def tax_analyze(
    file: UploadFile = File(...),
    annual_income: float = Form(...),
    age: int = Form(...),
    has_senior_parents: bool = Form(False),
    name: str = Form("User"),
) -> Dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    if Path(file.filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Upload a CSV bank statement")

    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "bank.csv"
        out_path.write_bytes(await file.read())

        agent = TaxSaverAgent()
        try:
            return agent.analyze(str(out_path), annual_income=annual_income, age=age, has_senior_parents=has_senior_parents, name=name)
        except Exception as e:
            logger.exception("Tax analysis failed")
            raise HTTPException(status_code=400, detail=f"Could not parse/analyze CSV: {e}")


@app.post("/tax/report-pdf")
async def tax_report_pdf(payload: Dict[str, Any]) -> Any:
    # Write PDF to temp and return
    with tempfile.TemporaryDirectory() as td:
        pdf_path = os.path.join(td, "taxiq_report.pdf")
        generate_tax_report_pdf(pdf_path, payload)
        return FileResponse(pdf_path, media_type="application/pdf", filename="taxiq_report.pdf")

