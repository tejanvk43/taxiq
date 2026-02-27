"""
TaxIQ — WhatsApp Bot for Kirana Store GST Filing
Powered by Twilio. Webhook URL: POST /whatsapp/webhook
"""
from __future__ import annotations

import json
import os
import random
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import httpx
from loguru import logger


# ── Session store (Redis-backed with in-memory fallback) ────────
_mem_sessions: Dict[str, Dict] = {}
_redis_client = None


def _get_redis():
    """Lazy-init Redis client for session persistence."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.Redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        logger.info("WhatsApp sessions → Redis")
        return _redis_client
    except Exception:
        logger.info("WhatsApp sessions → in-memory (Redis unavailable)")
        _redis_client = False          # sentinel: don't retry
        return None


def _load_session(phone: str) -> Dict:
    """Load session from Redis or in-memory."""
    r = _get_redis()
    if r:
        raw = r.get(f"wa_session:{phone}")
        if raw:
            return json.loads(raw)
    elif phone in _mem_sessions:
        return _mem_sessions[phone]
    return {
        "invoices": [],
        "pending_invoice": None,
        "total_tax": 0,
        "total_taxable": 0,
    }


def _save_session(phone: str, session: Dict):
    """Persist session to Redis or in-memory."""
    r = _get_redis()
    if r:
        r.set(f"wa_session:{phone}", json.dumps(session), ex=86400)  # 24h TTL
    else:
        _mem_sessions[phone] = session


class WhatsAppBot:
    """
    WhatsApp bot for Kirana store GST filing.
    Supports invoice OCR, GSTR-1 status, filing, and tax advice.
    """

    def __init__(self):
        self.client = None
        self.from_number = os.getenv(
            "TWILIO_WHATSAPP_NUMBER",
            "whatsapp:+14155238886",
        )
        try:
            from twilio.rest import Client
            sid = os.getenv("TWILIO_ACCOUNT_SID", "")
            token = os.getenv("TWILIO_AUTH_TOKEN", "")
            if sid and token and not sid.startswith("ACxx"):
                self.client = Client(sid, token)
                logger.info("Twilio WhatsApp client initialized")
            else:
                logger.info("Twilio credentials not set — running in mock mode")
        except ImportError:
            logger.warning("twilio package not installed — WhatsApp bot in mock mode")

    def send_message(self, to: str, body: str) -> str:
        """Send plain text WhatsApp message. Returns message SID."""
        to_fmt = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        if self.client:
            try:
                msg = self.client.messages.create(
                    from_=self.from_number,
                    to=to_fmt,
                    body=body,
                )
                return msg.sid
            except Exception as e:
                logger.error(f"Twilio send failed: {e}")
                return f"MOCK-SID-{random.randint(10000, 99999)}"
        logger.info(f"[MOCK] WhatsApp → {to_fmt}: {body[:80]}...")
        return f"MOCK-SID-{random.randint(10000, 99999)}"

    def handle_incoming(
        self,
        from_number: str,
        body: str,
        media_url: Optional[str] = None,
    ) -> str:
        """
        Process incoming WhatsApp message and return response text.

        State machine:
        1. Image → OCR → parsed details → "Reply YES to add to GSTR-1"
        2. YES → confirm added → "Reply STATUS for summary"
        3. STATUS → GSTR-1 summary
        4. FILE → mock submission
        5. TAX → quick tax advice in Hindi
        6. Anything else → help menu
        """
        session = _load_session(from_number)

        body_upper = body.strip().upper()

        # 1. Image received → real OCR + Gemini parse
        if media_url:
            parsed = self._real_ocr(media_url)
            session["pending_invoice"] = parsed
            _save_session(from_number, session)
            return (
                f"📸 Invoice Parsed!\n\n"
                f"Vendor: {parsed['vendor']}\n"
                f"GSTIN: {parsed['gstin']}\n"
                f"Invoice #: {parsed.get('invoice_number', 'N/A')}\n"
                f"Amount: ₹{parsed['amount']:,.0f}\n"
                f"Tax: ₹{parsed['tax']:,.0f}\n"
                f"Date: {parsed['date']}\n"
                f"HSN: {parsed['hsn']}\n"
                f"Confidence: {parsed.get('confidence', 0):.0%}\n\n"
                f"Reply *YES* to add to GSTR-1\n"
                f"Reply *NO* to discard"
            )

        # 2. YES → confirm invoice
        if body_upper == "YES":
            pending = session.get("pending_invoice")
            if not pending:
                return "No pending invoice. Send an invoice image first! 📸"
            session["invoices"].append(pending)
            session["total_taxable"] += pending["amount"]
            session["total_tax"] += pending["tax"]
            session["pending_invoice"] = None
            count = len(session["invoices"])
            _save_session(from_number, session)
            return (
                f"✅ Invoice added to GSTR-1!\n\n"
                f"You have {count} invoice{'s' if count > 1 else ''} this month.\n"
                f"Total taxable: ₹{session['total_taxable']:,.0f}\n"
                f"Total tax: ₹{session['total_tax']:,.0f}\n\n"
                f"Reply *STATUS* for filing summary\n"
                f"Reply *FILE* to submit GSTR-1"
            )

        # 3. STATUS → summary
        if body_upper == "STATUS":
            count = len(session.get("invoices", []))
            _save_session(from_number, session)
            if count == 0:
                return (
                    "📊 GSTR-1 Summary:\n\n"
                    "No invoices added yet this month.\n"
                    "Send invoice images to get started! 📸"
                )
            return (
                f"📊 Your GSTR-1 Summary:\n\n"
                f"Invoices: {count}\n"
                f"Total Taxable: ₹{session['total_taxable']:,.0f}\n"
                f"Total Tax: ₹{session['total_tax']:,.0f}\n"
                f"Period: {datetime.now().strftime('%B %Y')}\n\n"
                f"Reply *FILE* to submit\n"
                f"Reply *TAX* for savings advice"
            )

        # 4. FILE → mock submission
        if body_upper == "FILE":
            count = len(session.get("invoices", []))
            if count == 0:
                return "No invoices to file! Send invoice images first 📸"
            arn = f"ARN-{datetime.now().strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
            response = (
                f"🎉 GSTR-1 Filed Successfully!\n\n"
                f"ARN: {arn}\n"
                f"Invoices: {count}\n"
                f"Total Tax: ₹{session['total_tax']:,.0f}\n"
                f"Period: {datetime.now().strftime('%B %Y')}\n\n"
                f"[DEMO] This is a simulated filing.\n"
                f"Track at: http://localhost:8501"
            )
            # Reset session
            session["invoices"] = []
            session["pending_invoice"] = None
            session["total_tax"] = 0
            session["total_taxable"] = 0
            _save_session(from_number, session)
            return response

        # 5. TAX → quick tax advice in Hindi
        if body_upper == "TAX":
            _save_session(from_number, session)
            return (
                "💡 Tax Savings Tips:\n\n"
                "1. ELSS म्यूचुअल फंड में SIP शुरू करें — 80C के तहत ₹1.5L तक\n"
                "   Start ELSS SIP — up to ₹1.5L under 80C\n\n"
                "2. स्वास्थ्य बीमा लें — 80D के तहत ₹25,000 तक\n"
                "   Health insurance — up to ₹25K under 80D\n\n"
                "3. NPS में निवेश करें — 80CCD(1B) के तहत अतिरिक्त ₹50,000\n"
                "   NPS for extra ₹50K under 80CCD(1B)\n\n"
                "आज ही शुरू करें! हर रुपया बचत आपके भविष्य के लिए है। 🙏"
            )

        # 6. NO → discard pending
        if body_upper == "NO":
            session["pending_invoice"] = None
            _save_session(from_number, session)
            return "Invoice discarded. Send another image or type *STATUS*."

        # 7. Help menu (default)
        _save_session(from_number, session)
        return (
            "🙏 *TaxIQ WhatsApp Bot*\n\n"
            "Send me invoice photos and I'll help you file GST!\n\n"
            "Commands:\n"
            "📸 Send invoice image → auto-parse\n"
            "*YES* → confirm & add to GSTR-1\n"
            "*STATUS* → view GSTR-1 summary\n"
            "*FILE* → submit GSTR-1 return\n"
            "*TAX* → get tax saving tips (Hindi)\n\n"
            "Powered by TaxIQ 🇮🇳"
        )

    def send_fraud_alert(self, to: str, gstin: str, risk_score: float) -> str:
        """
        Send proactive fraud alert to user.
        Only sends if risk_score > 0.6.
        """
        if risk_score <= 0.6:
            return ""
        pct = int(risk_score * 100)
        body = (
            f"⚠️ *TaxIQ Fraud Alert*\n\n"
            f"One of your vendors (GSTIN: {gstin[:4]}...{gstin[-4:]}) "
            f"has a high fraud risk score of {pct}%.\n\n"
            f"Review this vendor before your next GSTR-1 filing.\n"
            f"Open TaxIQ: https://taxiq.in/fraud/{gstin}"
        )
        return self.send_message(to, body)

    @staticmethod
    def _mock_ocr(media_url: str) -> Dict:
        """Mock OCR result for demo purposes."""
        rng = random.Random(hash(media_url) % 10000)
        vendors = [
            ("Rathi Steel Corp", "27AAECR4512K1ZM", "7308"),
            ("Patel Electronics", "24ABCPD6789Q1ZN", "8517"),
            ("Sharma Packaging", "07AABCS7777H1Z1", "3923"),
            ("Kumar Traders", "33ABDCK3456N1ZT", "4901"),
        ]
        v = rng.choice(vendors)
        amount = rng.randint(10000, 200000)
        return {
            "vendor": v[0],
            "gstin": v[1],
            "hsn": v[2],
            "amount": amount,
            "tax": round(amount * 0.18, 2),
            "date": datetime.now().strftime("%d-%m-%Y"),
            "invoice_number": f"INV-{rng.randint(1000, 9999)}",
        }

    def _real_ocr(self, media_url: str) -> Dict:
        """
        Download image from Twilio → run OCR + Gemini pipeline → return parsed dict.
        Falls back to mock OCR if pipeline fails.
        """
        try:
            # Download image from Twilio (requires auth for sandbox)
            logger.info(f"Downloading media from: {media_url}")
            sid = os.getenv("TWILIO_ACCOUNT_SID", "")
            token = os.getenv("TWILIO_AUTH_TOKEN", "")

            headers = {}
            auth = (sid, token) if sid and token else None

            r = httpx.get(media_url, auth=auth, follow_redirects=True, timeout=30, headers=headers)
            if r.status_code != 200:
                logger.warning(f"Media download failed: {r.status_code}")
                return self._mock_ocr(media_url)

            # Determine file extension from content-type
            ct = r.headers.get("content-type", "image/jpeg")
            ext = ".jpg"
            if "png" in ct:
                ext = ".png"
            elif "pdf" in ct:
                ext = ".pdf"

            # Save to temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix="wa_invoice_")
            tmp.write(r.content)
            tmp.flush()
            tmp.close()
            logger.info(f"Saved media to: {tmp.name} ({len(r.content)} bytes)")

            # Run invoice parsing pipeline (OCR + Gemini)
            from backend.pipelines.invoice_parser import parse_invoice
            invoice = parse_invoice(tmp.name)

            # Clean up temp file
            try:
                Path(tmp.name).unlink()
            except OSError:
                pass

            # Extract HSN codes
            hsn_str = ", ".join(h.hsn for h in invoice.hsn_codes) if invoice.hsn_codes else "N/A"

            return {
                "vendor": invoice.vendor_name or "Unknown",
                "gstin": invoice.vendor_gstin or "Not found",
                "hsn": hsn_str,
                "amount": float(invoice.taxable_value),
                "tax": float(invoice.cgst + invoice.sgst + invoice.igst),
                "date": invoice.invoice_date or datetime.now().strftime("%d-%m-%Y"),
                "invoice_number": invoice.invoice_number or "N/A",
                "confidence": invoice.confidence_score,
                "demo": invoice.demo_data,
            }

        except Exception as e:
            logger.error(f"Real OCR failed, falling back to mock: {e}")
            return self._mock_ocr(media_url)
