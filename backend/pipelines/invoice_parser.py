import re
from typing import Any, Dict

from backend.config import settings
from backend.models.invoice import Invoice
from backend.pipelines.ocr_pipeline import extract_text_from_image
from backend.utils.llm_client import LLMClient, image_file_to_b64


_GSTIN_RE = re.compile(r"\b\d{2}[A-Z0-9]{10}\d[A-Z0-9][A-Z0-9]Z[A-Z0-9]\b", re.IGNORECASE)


def _gstin_present(text: str) -> bool:
    return bool(_GSTIN_RE.search(text or ""))


def parse_invoice(image_path: str) -> Invoice:
    """
    Image -> OCR -> Claude JSON extraction -> Invoice model.
    DEMO fallback if no Anthropic key.
    """
    raw_text = extract_text_from_image(image_path)

    system_prompt = (
        "You are an Indian GST invoice parser. Extract all fields "
        "strictly as JSON. Indian invoices contain: vendor name, "
        "GSTIN (format: 2 digits + 10 chars + 1 digit + 1 char + 1 char), "
        "HSN codes, CGST/SGST/IGST amounts. Return ONLY valid JSON, "
        "no markdown, no explanation."
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

    invoice = Invoice(**inv_dict, demo_data=demo)

    # Spec: If GSTIN is missing, set confidence_score < 0.5
    if not invoice.vendor_gstin:
        invoice.confidence_score = min(invoice.confidence_score, 0.45)

    return invoice

