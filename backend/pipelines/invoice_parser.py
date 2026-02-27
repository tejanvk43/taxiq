import re
from typing import Any, Dict

from backend.config import settings
from backend.models.invoice import Invoice
from backend.pipelines.ocr_pipeline import extract_text_from_image
from backend.utils.llm_client import LLMClient, image_file_to_b64


_GSTIN_RE = re.compile(r"\b\d{2}[A-Z0-9]{10}\d[A-Z0-9][A-Z0-9]Z[A-Z0-9]\b", re.IGNORECASE)


def _gstin_present(text: str) -> bool:
    return bool(_GSTIN_RE.search(text or ""))


# ── Field-name aliases the AI might return ──────────────
_FIELD_ALIASES: Dict[str, str] = {
    # invoice_number
    "invoice_no": "invoice_number",
    "inv_number": "invoice_number",
    "inv_no": "invoice_number",
    "bill_number": "invoice_number",
    "bill_no": "invoice_number",
    "number": "invoice_number",
    # invoice_date
    "date": "invoice_date",
    "inv_date": "invoice_date",
    "bill_date": "invoice_date",
    # total_value
    "total": "total_value",
    "total_amount": "total_value",
    "grand_total": "total_value",
    "invoice_total": "total_value",
    "amount": "total_value",
    "net_amount": "total_value",
    # taxable_value
    "taxable_amount": "taxable_value",
    "sub_total": "taxable_value",
    "subtotal": "taxable_value",
    "base_amount": "taxable_value",
    "pre_tax_amount": "taxable_value",
    # vendor
    "seller_name": "vendor_name",
    "supplier_name": "vendor_name",
    "seller_gstin": "vendor_gstin",
    "supplier_gstin": "vendor_gstin",
    # buyer
    "buyer_name": "buyer_gstin",  # rarely useful, but keep
    "recipient_gstin": "buyer_gstin",
    # tax
    "tax_amount": "igst",
    "gst_amount": "igst",
}


def _normalize_invoice_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map AI-returned field names to the canonical Invoice field names."""
    out: Dict[str, Any] = {}
    for key, val in raw.items():
        canonical = _FIELD_ALIASES.get(key.lower().strip(), key)
        # Don't overwrite a field that's already set with a canonical name
        if canonical not in out:
            out[canonical] = val

    # Derive missing fields from what we have
    tv = out.get("total_value")
    txv = out.get("taxable_value")
    cgst = float(out.get("cgst", 0) or 0)
    sgst = float(out.get("sgst", 0) or 0)
    igst = float(out.get("igst", 0) or 0)
    tax_total = cgst + sgst + igst

    if tv is not None and txv is None:
        out["taxable_value"] = float(tv) - tax_total
    elif txv is not None and tv is None:
        out["total_value"] = float(txv) + tax_total
    elif tv is None and txv is None:
        out["total_value"] = 0.0
        out["taxable_value"] = 0.0

    if "invoice_number" not in out:
        out["invoice_number"] = "UNKNOWN"
    if "invoice_date" not in out:
        from datetime import date
        out["invoice_date"] = date.today().isoformat()

    return out


def parse_invoice(image_path: str) -> Invoice:
    """
    Image -> OCR -> Claude JSON extraction -> Invoice model.
    DEMO fallback if no Anthropic key.
    """
    raw_text = extract_text_from_image(image_path)

    system_prompt = (
        "You are an Indian GST invoice parser. Extract the following "
        "fields strictly as JSON with EXACTLY these keys:\n"
        "  vendor_name (str), vendor_gstin (str or null), "
        "  buyer_gstin (str or null), invoice_number (str), "
        "  invoice_date (str YYYY-MM-DD), total_value (float), "
        "  taxable_value (float), cgst (float), sgst (float), igst (float), "
        "  hsn_codes (list of {code, description, value}).\n"
        "GSTIN format: 2 digits + 10 alphanumeric + 1 digit + 1 char + Z + 1 char.\n"
        "Return ONLY valid JSON, no markdown, no explanation."
    )

    llm = LLMClient()
    image_b64 = image_file_to_b64(image_path)
    payload: Dict[str, Any] = llm.ask_json(
        prompt=f"OCR_TEXT:\n{raw_text}",
        image_b64=image_b64,
        system_prompt=system_prompt,
    )

    # DEMO mode from llm_client returns wrapped JSON; normalize.
    if isinstance(payload, dict) and "invoice" in payload:
        inv_dict = payload["invoice"]
        demo = bool(payload.get("demo"))
    else:
        inv_dict = payload
        demo = settings.demo_mode

    invoice = Invoice(**_normalize_invoice_dict(inv_dict), demo_data=demo)

    # Spec: If GSTIN is missing, set confidence_score < 0.5
    if not invoice.vendor_gstin:
        invoice.confidence_score = min(invoice.confidence_score, 0.45)

    return invoice

