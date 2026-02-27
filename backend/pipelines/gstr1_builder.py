from __future__ import annotations

from typing import Any, Dict

from backend.models.invoice import Invoice


def build_gstr1_entry(invoice: Invoice) -> Dict[str, Any]:
    """
    Build a minimal B2B GSTR-1 entry dict from an Invoice.
    Output format is a practical JSON structure used by this app.
    """
    return {
        "ctin": invoice.buyer_gstin or "",
        "inv": [
            {
                "inum": invoice.invoice_number,
                "idt": invoice.invoice_date,
                "val": round(invoice.total_value, 2),
                "pos": (invoice.buyer_gstin or "")[:2] or "00",
                "rchrg": "N",
                "etin": None,
                "itms": [
                    {
                        "num": i + 1,
                        "itm_det": {
                            "txval": round(line.taxable_value, 2),
                            "rt": 18,
                            "iamt": round(line.igst, 2),
                            "camt": round(line.cgst, 2),
                            "samt": round(line.sgst, 2),
                        },
                        "hsn": line.hsn,
                    }
                    for i, line in enumerate(invoice.hsn_codes or [])
                ],
            }
        ],
        "vendor": {"name": invoice.vendor_name, "gstin": invoice.vendor_gstin or ""},
    }


def build_gstr1_return(user_gstin: str, period: str, invoices: list[Invoice]) -> Dict[str, Any]:
    b2b = []
    hsn_summary = {}
    total_tax = 0.0

    for inv in invoices:
        b2b.append(build_gstr1_entry(inv))
        for line in inv.hsn_codes:
            h = hsn_summary.setdefault(
                line.hsn,
                {"hsn": line.hsn, "txval": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0},
            )
            h["txval"] += float(line.taxable_value)
            h["cgst"] += float(line.cgst)
            h["sgst"] += float(line.sgst)
            h["igst"] += float(line.igst)
        total_tax += float(inv.cgst + inv.sgst + inv.igst)

    return {
        "gstin": user_gstin,
        "fp": period,
        "b2b": b2b,
        "b2cs": [],
        "hsn_summary": list(hsn_summary.values()),
        "totals": {"invoices": len(invoices), "total_tax_liability": round(total_tax, 2)},
    }

