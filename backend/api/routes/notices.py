from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from backend.core.notice_generator import NoticeGenerator
from backend.services.ws_manager import manager

router = APIRouter(prefix="/api/notices", tags=["notices"])


class NoticeRequest(BaseModel):
    noticeType: str = "SCN-MISMATCH"
    gstin: str = "27AADCB2230M1ZT"
    taxpayerName: Optional[str] = "ABC Enterprises"
    period: str = "FY 2023-24"
    demandAmount: float = 250000
    section: str = "73"
    description: Optional[str] = None
    additionalContext: Optional[str] = None


@router.post("/generate")
async def generate_notice(req: NoticeRequest):
    gen = NoticeGenerator()
    notice = await gen.generate(
        vendor_gstin=req.gstin,
        notice_type=req.noticeType,
        period=req.period,
        amount=req.demandAmount,
        section=req.section,
    )
    # Add extra fields from request
    notice["gstin"] = req.gstin
    notice["taxpayerName"] = req.taxpayerName
    notice["demandAmount"] = req.demandAmount
    notice["description"] = req.description

    await manager.broadcast(
        "29AAACN0001A1Z5",
        {"type": "NOTICE_READY", "payload": {"noticeId": notice["noticeId"], "vendor": req.gstin}},
    )
    return notice


@router.get("/{notice_id}/pdf")
async def download_notice_pdf(notice_id: str):
    return {"noticeId": notice_id, "status": "NOT_IMPLEMENTED", "hint": "Integrate reportlab/weasyprint to generate PDF."}


@router.post("/{notice_id}/send")
async def send_notice_email(notice_id: str):
    return {"noticeId": notice_id, "status": "NOT_IMPLEMENTED", "hint": "Integrate SendGrid/AWS SES for delivery."}
