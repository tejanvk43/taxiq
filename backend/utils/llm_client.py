import base64
import json
import time
from typing import Any, Optional

import httpx
from loguru import logger

from backend.config import settings


# ── Helpers ──────────────────────────────────────────────
def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


def _safe_json_loads(text: str) -> Any:
    t = _strip_fences(text)
    try:
        return json.loads(t)
    except Exception:
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(t[start : end + 1])
        raise


_DEMO_INVOICE = {
    "demo": True,
    "message": "[DEMO DATA] AI API unavailable; returning deterministic mock JSON.",
    "invoice": {
        "vendor_name": "GoldStar Traders [DEMO DATA]",
        "vendor_gstin": "27AABCG1234Q1Z2",
        "buyer_gstin": "27AAACN0001A1Z5",
        "invoice_number": "GS-INV-0007",
        "invoice_date": "2024-02-18",
        "total_value": 118000.0,
        "taxable_value": 100000.0,
        "cgst": 9000.0,
        "sgst": 9000.0,
        "igst": 0.0,
        "hsn_codes": [{"hsn": "8471", "taxable_value": 100000.0, "cgst": 9000.0, "sgst": 9000.0, "igst": 0.0}],
    },
}


# ── LLM Client (Google Gemini — FREE, vision-capable) ───
class LLMClient:
    """
    Google Gemini wrapper via REST API.
    Free tier: 15 RPM · 1 M tokens/min · 1 500 req/day.
    gemini-2.5-flash supports vision — invoice images sent natively.
    Falls back to DEMO JSON if key missing or API error.
    """

    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self) -> None:
        self.model = "gemini-2.5-flash"

    def ask(self, prompt: str, image_b64: str | None = None,
            system_prompt: str | None = None) -> str:
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            logger.warning("LLMClient.ask called without GOOGLE_API_KEY -> DEMO mode")
            return self._demo_json()

        url = self.GEMINI_URL.format(model=self.model) + f"?key={api_key}"

        # Build parts (text + optional inline image)
        parts: list[dict] = [{"text": prompt}]
        if image_b64:
            parts.append({"inlineData": {"mimeType": "image/jpeg", "data": image_b64}})

        body: dict[str, Any] = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1200},
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        for attempt in range(1, 4):
            try:
                logger.info("Gemini call attempt={} model={}", attempt, self.model)
                t0 = time.time()
                with httpx.Client(timeout=60) as client:
                    resp = client.post(url, json=body)
                if 400 <= resp.status_code < 500:
                    logger.warning("Gemini returned {} — {}", resp.status_code, resp.text[:200])
                    return self._demo_json()
                resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                dt = time.time() - t0
                logger.info("Gemini response chars={} latency_s={:.2f}", len(text), dt)
                return _strip_fences(text)
            except Exception as e:
                wait = 2 ** (attempt - 1)
                logger.exception("Gemini call failed attempt={} err={}", attempt, str(e))
                time.sleep(wait)

        logger.warning("Gemini call failed after 3 attempts — falling back to DEMO mode")
        return self._demo_json()

    def ask_json(self, prompt: str, image_b64: str | None = None,
                 system_prompt: str | None = None) -> Any:
        return _safe_json_loads(
            self.ask(prompt=prompt, image_b64=image_b64, system_prompt=system_prompt)
        )

    @staticmethod
    def _demo_json() -> str:
        return json.dumps(_DEMO_INVOICE)


def image_file_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

