"""
TaxIQ — Mock Data Ingestion API
Ingest GSTR-1, GSTR-2B, Purchase Register, e-Invoice mock data.
"""
from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from backend.services.mock_gstn import MockGSTNClient

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

# In-memory store for ingested data (hackathon-grade)
_ingested: Dict[str, List[Dict[str, Any]]] = {
    "gstr1": [],
    "gstr2b": [],
    "purchase_register": [],
    "einvoice": [],
}


class IngestStatus(BaseModel):
    source: str
    records_ingested: int
    job_id: str
    status: str
    timestamp: str
    warnings: List[str] = []
    sample_records: List[Dict[str, Any]] = []


@router.post("/gstr1")
async def ingest_gstr1(
    gstin: str = "29AAACN0001A1Z5",
    period: str = "2024-01",
) -> IngestStatus:
    """Ingest GSTR-1 filing data from mock GSTN API."""
    client = MockGSTNClient()
    data = await client.get_gstr1(gstin=gstin, period=period)
    invoices = data.get("invoices", [])

    records = []
    for inv in invoices:
        records.append({
            "source": "GSTR-1",
            "gstin": gstin,
            "period": period,
            "invoice_id": inv.get("invoiceId", ""),
            "irn": inv.get("irn", ""),
            "amount": inv.get("amount", 0),
            "tax_amount": inv.get("taxAmount", 0),
            "date": inv.get("date", ""),
            "status": inv.get("status", "FILED"),
            "ingested_at": datetime.utcnow().isoformat() + "Z",
        })

    _ingested["gstr1"].extend(records)

    return IngestStatus(
        source="GSTR-1",
        records_ingested=len(records),
        job_id=str(uuid.uuid4()),
        status="COMPLETE",
        timestamp=datetime.utcnow().isoformat() + "Z",
        warnings=[f"Filed status: {data.get('filed', False)}"],
        sample_records=records[:5],
    )


@router.post("/gstr2b")
async def ingest_gstr2b(
    gstin: str = "29AAACN0001A1Z5",
    period: str = "2024-01",
) -> IngestStatus:
    """Ingest GSTR-2B auto-populated data from mock GSTN API."""
    client = MockGSTNClient()

    # First get GSTR-1 and generate corresponding GSTR-2B
    gstr1_data = await client.get_gstr1(gstin=gstin, period=period)
    gstr1_invoices = gstr1_data.get("invoices", [])

    import random
    rng = random.Random(42)
    records = []
    warnings = []

    for inv in gstr1_invoices:
        r = rng.random()
        if r < 0.10:
            warnings.append(f"Invoice {inv.get('invoiceId', '')} missing in GSTR-2B (supplier not filed)")
            continue

        amount = inv.get("amount", 0)
        tax = inv.get("taxAmount", 0)

        if r < 0.25:
            factor = 1 + rng.uniform(-0.15, -0.03)
            amount = round(amount * factor, 2)
            tax = round(amount * 0.18, 2)
            warnings.append(f"Invoice {inv.get('invoiceId', '')} has value mismatch")

        records.append({
            "source": "GSTR-2B",
            "gstin": gstin,
            "period": period,
            "invoice_id": inv.get("invoiceId", ""),
            "supplier_gstin": gstin,
            "amount": amount,
            "tax_amount": tax,
            "itc_eligible": True,
            "action": "No Action" if r >= 0.25 else "Pending",
            "date": inv.get("date", ""),
            "ingested_at": datetime.utcnow().isoformat() + "Z",
        })

    _ingested["gstr2b"].extend(records)

    return IngestStatus(
        source="GSTR-2B",
        records_ingested=len(records),
        job_id=str(uuid.uuid4()),
        status="COMPLETE",
        timestamp=datetime.utcnow().isoformat() + "Z",
        warnings=warnings[:10],
        sample_records=records[:5],
    )


@router.post("/purchase-register")
async def ingest_purchase_register(
    file: UploadFile = File(None),
    gstin: str = "29AAACN0001A1Z5",
) -> IngestStatus:
    """Ingest Purchase Register from CSV upload or generate mock data."""
    import random
    rng = random.Random(99)
    records = []
    warnings = []

    if file and file.filename:
        content = await file.read()
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            for row in reader:
                records.append({
                    "source": "Purchase Register",
                    "gstin": gstin,
                    "vendor_name": row.get("vendor_name", row.get("Vendor", "")),
                    "vendor_gstin": row.get("vendor_gstin", row.get("GSTIN", "")),
                    "invoice_no": row.get("invoice_no", row.get("Invoice No", "")),
                    "amount": float(row.get("amount", row.get("Amount", 0))),
                    "tax_amount": float(row.get("tax_amount", row.get("Tax", 0))),
                    "date": row.get("date", row.get("Date", "")),
                    "hsn": row.get("hsn", row.get("HSN", "")),
                    "ingested_at": datetime.utcnow().isoformat() + "Z",
                })
        except Exception as e:
            warnings.append(f"CSV parse error: {str(e)}")
    else:
        # Generate mock purchase register
        vendors = [
            ("Falcon Components Pvt Ltd", "27AAACF9999K1Z9"),
            ("GoldStar Traders", "19AABCG1234Q1Z2"),
            ("Shadow Supplies Delhi", "07AABCS7777H1Z1"),
            ("Patel Chemicals Gujarat", "24ABCPD6789Q1ZN"),
            ("Kumar Traders Chennai", "33ABDCK3456N1ZT"),
        ]
        for i in range(20):
            vendor = vendors[i % len(vendors)]
            amount = rng.randint(25000, 500000)
            records.append({
                "source": "Purchase Register",
                "gstin": gstin,
                "vendor_name": vendor[0],
                "vendor_gstin": vendor[1],
                "invoice_no": f"PR-2024-{i+1:03d}",
                "amount": amount,
                "tax_amount": round(amount * 0.18, 2),
                "date": f"2024-01-{rng.randint(1,28):02d}",
                "hsn": rng.choice(["8471", "3004", "4901", "9971", "7308"]),
                "ingested_at": datetime.utcnow().isoformat() + "Z",
            })

    _ingested["purchase_register"].extend(records)

    return IngestStatus(
        source="Purchase Register",
        records_ingested=len(records),
        job_id=str(uuid.uuid4()),
        status="COMPLETE",
        timestamp=datetime.utcnow().isoformat() + "Z",
        warnings=warnings,
        sample_records=records[:5],
    )


@router.post("/einvoice")
async def ingest_einvoice(
    gstin: str = "29AAACN0001A1Z5",
    period: str = "2024-01",
) -> IngestStatus:
    """Ingest e-Invoice data with IRN validation from mock portal."""
    import random
    rng = random.Random(55)
    records = []
    warnings = []

    for i in range(15):
        irn_valid = rng.random() > 0.1
        amount = rng.randint(50000, 800000)
        records.append({
            "source": "e-Invoice",
            "gstin": gstin,
            "invoice_no": f"EINV-{period.replace('-','')}-{i+1:03d}",
            "irn": f"IRN{rng.randint(100000000,999999999)}" if irn_valid else "",
            "irn_status": "ACTIVE" if irn_valid else "NOT_GENERATED",
            "supplier_gstin": rng.choice([
                "27AAACF9999K1Z9", "19AABCG1234Q1Z2",
                "07AABCS7777H1Z1", "24ABCPD6789Q1ZN",
            ]),
            "amount": amount,
            "tax_amount": round(amount * 0.18, 2),
            "date": f"{period}-{rng.randint(1,28):02d}",
            "ack_no": f"ACK-{rng.randint(10000,99999)}" if irn_valid else "",
            "ack_date": f"{period}-{rng.randint(1,28):02d}" if irn_valid else "",
            "ingested_at": datetime.utcnow().isoformat() + "Z",
        })
        if not irn_valid:
            warnings.append(f"Invoice EINV-{period.replace('-','')}-{i+1:03d}: IRN not generated")

    _ingested["einvoice"].extend(records)

    return IngestStatus(
        source="e-Invoice",
        records_ingested=len(records),
        job_id=str(uuid.uuid4()),
        status="COMPLETE",
        timestamp=datetime.utcnow().isoformat() + "Z",
        warnings=warnings,
        sample_records=records[:5],
    )


@router.get("/status")
async def get_ingestion_status() -> Dict[str, Any]:
    """Get current ingestion status across all sources."""
    return {
        "sources": {
            "gstr1": {
                "total_records": len(_ingested["gstr1"]),
                "last_ingested": _ingested["gstr1"][-1]["ingested_at"] if _ingested["gstr1"] else None,
            },
            "gstr2b": {
                "total_records": len(_ingested["gstr2b"]),
                "last_ingested": _ingested["gstr2b"][-1]["ingested_at"] if _ingested["gstr2b"] else None,
            },
            "purchase_register": {
                "total_records": len(_ingested["purchase_register"]),
                "last_ingested": _ingested["purchase_register"][-1]["ingested_at"] if _ingested["purchase_register"] else None,
            },
            "einvoice": {
                "total_records": len(_ingested["einvoice"]),
                "last_ingested": _ingested["einvoice"][-1]["ingested_at"] if _ingested["einvoice"] else None,
            },
        },
        "total_records": sum(len(v) for v in _ingested.values()),
    }


@router.get("/records/{source}")
async def get_ingested_records(
    source: str,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Get ingested records for a specific source."""
    if source not in _ingested:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")
    records = _ingested[source]
    return {
        "source": source,
        "total": len(records),
        "records": records[offset:offset + limit],
    }
