import base64
import json
import time
from typing import Any, Optional

import httpx
from loguru import logger

from backend.config import settings


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # remove ```json / ``` and trailing ```
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


def _safe_json_loads(text: str) -> Any:
    t = _strip_fences(text)
    try:
        return json.loads(t)
    except Exception:
        # attempt to locate a JSON object inside the text
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(t[start : end + 1])
        raise


class LLMClient:
    """
    Anthropic wrapper with retry + logging.

    ask(prompt: str, image_b64: str | None = None) -> str
    - If image_b64 provided, send as vision message
    - 3 attempts exponential backoff
    - strips markdown fences for JSON workflows
    """

    def __init__(self) -> None:
        self.model = "claude-opus-4-6"

    def ask(self, prompt: str, image_b64: str | None = None, system_prompt: str | None = None) -> str:
        """
        Anthropic Messages API via httpx (works regardless of anthropic SDK version).
        """
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("LLMClient.ask called without ANTHROPIC_API_KEY -> DEMO mode")
            return json.dumps(
                {
                    "demo": True,
                    "message": "[DEMO DATA] Anthropic API key missing; returning deterministic mock JSON.",
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
            )

        for attempt in range(1, 4):
            try:
                logger.info("Anthropic call attempt={} model={}", attempt, self.model)
                t0 = time.time()
                payload = {
                    "model": self.model,
                    "max_tokens": 1200,
                    "temperature": 0,
                    "system": system_prompt
                    or "You are a precise extraction engine. If asked for JSON, output ONLY valid JSON.",
                    "messages": [{"role": "user", "content": self._build_content(prompt=prompt, image_b64=image_b64)}],
                }
                headers = {
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                with httpx.Client(timeout=60) as client:
                    resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                resp.raise_for_status()
                msg = resp.json()
                dt = time.time() - t0
                blocks = msg.get("content", []) if isinstance(msg, dict) else []
                out = "".join([b.get("text", "") for b in blocks if b.get("type") == "text"])
                logger.info("Anthropic response chars={} latency_s={:.2f}", len(out), dt)
                return _strip_fences(out)
            except Exception as e:
                wait = 2 ** (attempt - 1)
                logger.exception("Anthropic call failed attempt={} wait_s={} err={}", attempt, wait, str(e))
                time.sleep(wait)
        raise RuntimeError("Anthropic call failed after 3 attempts")

    def ask_json(self, prompt: str, image_b64: str | None = None, system_prompt: str | None = None) -> Any:
        return _safe_json_loads(self.ask(prompt=prompt, image_b64=image_b64, system_prompt=system_prompt))

    def _build_content(self, prompt: str, image_b64: Optional[str]) -> list[dict]:
        if not image_b64:
            return [{"type": "text", "text": prompt}]
        # Anthropic expects base64 data; use image/jpeg by default.
        return [
            {"type": "text", "text": prompt},
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64},
            },
        ]


def image_file_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

