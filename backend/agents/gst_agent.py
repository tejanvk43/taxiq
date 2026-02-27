from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger
from sqlalchemy import text

from backend.database.postgres_client import postgres_client
from backend.graph.graph_builder import graph_store
from backend.models.invoice import Invoice
from backend.pipelines.gstr1_builder import build_gstr1_entry, build_gstr1_return
from backend.pipelines.invoice_parser import parse_invoice


@dataclass
class _InvoiceMemoryStore:
    items: List[Invoice] = field(default_factory=list)

    def add(self, inv: Invoice) -> None:
        self.items.append(inv)

    def list_for_period(self, user_gstin: str, period: str) -> List[Invoice]:
        # period = YYYY-MM
        out = []
        for i in self.items:
            if i.buyer_gstin == user_gstin and str(i.invoice_date).startswith(period):
                out.append(i)
        return out


_mem_store = _InvoiceMemoryStore()


class GSTAgent:
    def __init__(self) -> None:
        self._db_ready = False
        try:
            postgres_client.init_schema()
            self._db_ready = True
        except Exception as e:
            logger.warning("Postgres not ready; using in-memory invoice store. err={}", str(e))

    async def process_invoice(self, image_path: str) -> Dict[str, Any]:
        invoice = parse_invoice(image_path)
        gstr1_entry = build_gstr1_entry(invoice)

        warnings: List[str] = []
        if invoice.demo_data:
            warnings.append("[DEMO DATA] LLM key missing; invoice fields are mock.")
        if not invoice.vendor_gstin:
            warnings.append("Vendor GSTIN missing or low confidence.")

        # persist invoice (best-effort)
        stored = False
        if self._db_ready:
            try:
                with postgres_client.session() as s:
                    s.execute(
                        text(
                            """
                            INSERT INTO invoices (
                              invoice_number, invoice_date, vendor_name, vendor_gstin, buyer_gstin,
                              total_value, taxable_value, cgst, sgst, igst, confidence_score, raw_json
                            ) VALUES (
                              :invoice_number, :invoice_date, :vendor_name, :vendor_gstin, :buyer_gstin,
                              :total_value, :taxable_value, :cgst, :sgst, :igst, :confidence_score, :raw_json
                            )
                            """
                        ),
                        {
                            "invoice_number": invoice.invoice_number,
                            "invoice_date": invoice.invoice_date,
                            "vendor_name": invoice.vendor_name,
                            "vendor_gstin": invoice.vendor_gstin,
                            "buyer_gstin": invoice.buyer_gstin,
                            "total_value": invoice.total_value,
                            "taxable_value": invoice.taxable_value,
                            "cgst": invoice.cgst,
                            "sgst": invoice.sgst,
                            "igst": invoice.igst,
                            "confidence_score": invoice.confidence_score,
                            "raw_json": json.dumps(invoice.model_dump()),
                        },
                    )
                stored = True
            except Exception as e:
                logger.warning("Failed to store invoice in Postgres; falling back to memory. err={}", str(e))

        if not stored:
            _mem_store.add(invoice)

        # push to graph store (best-effort)
        try:
            await self.load_into_graph(invoice)
        except Exception as e:
            warnings.append(f"[DEMO DATA] Graph load skipped (Neo4j down or unavailable): {e}")

        return {
            "invoice": invoice.model_dump(),
            "gstr1_entry": gstr1_entry,
            "confidence_score": invoice.confidence_score,
            "warnings": warnings,
        }

    async def load_into_graph(self, invoice: Invoice) -> None:
        supplier = invoice.vendor_gstin or "27DEMOX0000X1Z9"
        buyer = invoice.buyer_gstin or "27AAACG1000A1Z5"
        await graph_store.create_gstin_node(gstin=supplier, name=invoice.vendor_name or "Supplier", state=supplier[:2], type="REGULAR")
        await graph_store.create_gstin_node(gstin=buyer, name="Buyer", state=buyer[:2], type="REGULAR")
        await graph_store.create_invoice_node(invoice_id=invoice.invoice_number, date=invoice.invoice_date, value=invoice.total_value, tax=(invoice.cgst + invoice.sgst + invoice.igst))
        await graph_store.link_supplier_buyer(supplier_gstin=supplier, buyer_gstin=buyer, invoice_id=invoice.invoice_number, itc_value=(invoice.cgst + invoice.sgst + invoice.igst))

    def build_gstr1_return(self, user_gstin: str, period: str) -> Dict[str, Any]:
        invoices: List[Invoice] = []
        if self._db_ready:
            try:
                with postgres_client.session() as s:
                    rows = s.execute(
                        text(
                            """
                            SELECT raw_json
                            FROM invoices
                            WHERE buyer_gstin = :gstin
                              AND to_char(invoice_date, 'YYYY-MM') = :period
                            ORDER BY invoice_date DESC
                            """
                        ),
                        {"gstin": user_gstin, "period": period},
                    ).fetchall()
                for (raw,) in rows:
                    invoices.append(Invoice(**(raw if isinstance(raw, dict) else json.loads(raw))))
            except Exception as e:
                logger.warning("Failed to read invoices from Postgres; using memory. err={}", str(e))

        if not invoices:
            invoices = _mem_store.list_for_period(user_gstin=user_gstin, period=period)

        payload = build_gstr1_return(user_gstin=user_gstin, period=period, invoices=invoices)
        payload["generatedAt"] = datetime.utcnow().isoformat() + "Z"
        if not self._db_ready:
            payload["note"] = "[DEMO DATA] Postgres not connected; return built from in-memory invoices."
        return payload

