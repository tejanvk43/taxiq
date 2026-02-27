"""
TaxIQ — WhatsApp Twilio Webhook Router
"""
from fastapi import APIRouter, Form, Request, Response
from loguru import logger

from backend.utils.whatsapp_bot import WhatsAppBot

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
bot = WhatsAppBot()


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Twilio webhook endpoint.
    Receives incoming WhatsApp messages and returns TwiML XML response.
    Handles media (images) sent by the user for invoice OCR.
    """
    form = await request.form()
    from_number = form.get("From", "")
    body = form.get("Body", "")
    num_media = int(form.get("NumMedia", "0"))
    media_url = form.get("MediaUrl0") if num_media > 0 else None

    logger.info(
        f"WhatsApp incoming from={from_number} body={body[:50]} "
        f"num_media={num_media} media={media_url}"
    )

    response_text = bot.handle_incoming(from_number, body, media_url)

    # Escape XML special chars in response
    safe_text = (
        response_text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{safe_text}</Message>"
        "</Response>"
    )
    return Response(content=twiml, media_type="application/xml")


@router.get("/test")
async def test_whatsapp(to: str, message: str = "Hello from TaxIQ!"):
    """Test endpoint to send a WhatsApp message manually."""
    sid = bot.send_message(to, message)
    return {"status": "sent", "sid": sid, "to": to}


@router.post("/simulate")
async def simulate_message(
    phone: str = Form("+918919998149"),
    message: str = Form(""),
    image_url: str = Form(None),
):
    """
    Simulate an incoming WhatsApp message (for testing without Twilio webhook).
    POST /whatsapp/simulate with phone, message, and optional image_url.
    """
    from_fmt = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
    media = image_url if image_url and image_url.strip() else None
    response_text = bot.handle_incoming(from_fmt, message, media)
    return {"from": from_fmt, "message": message, "response": response_text}


@router.get("/status")
async def whatsapp_status():
    """Check if WhatsApp bot is configured."""
    return {
        "twilio_configured": bot.client is not None,
        "from_number": bot.from_number,
        "status": "active" if bot.client else "mock_mode",
    }
