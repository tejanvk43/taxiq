from __future__ import annotations

import os
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_sample_invoices() -> None:
    """
    Generates 3 realistic-ish invoice JPGs into data/sample_invoices/ if missing.
    This keeps the repository text-only while still providing real images for OCR.
    """
    out_dir = _root() / "data" / "sample_invoices"
    out_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 4):
        p = out_dir / f"invoice_{i}.jpg"
        if p.exists():
            continue
        _render_invoice(p, variant=i)
        logger.info("Generated sample invoice image: {}", str(p))


def _render_invoice(path: Path, variant: int) -> None:
    w, h = 1240, 1754  # A4-ish @ 150dpi
    img = Image.new("RGB", (w, h), (250, 250, 250))
    d = ImageDraw.Draw(img)

    try:
        font_h = ImageFont.truetype("arial.ttf", 44)
        font_b = ImageFont.truetype("arial.ttf", 28)
        font_m = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font_h = ImageFont.load_default()
        font_b = ImageFont.load_default()
        font_m = ImageFont.load_default()

    # Header bar
    d.rectangle([0, 0, w, 120], fill=(10, 22, 40))
    d.text((40, 30), "TAXIQ DEMO INVOICE", fill=(255, 153, 51), font=font_h)

    vendor = [
        ("GoldStar Traders", "27AABCG1234Q1Z2"),
        ("Falcon Components", "27AAACF9999K1Z9"),
        ("Trident Electronics", "27AAACG2014A1Z9"),
    ][(variant - 1) % 3]

    buyer = ("Aarohan Metals Pvt Ltd", "27AAACG1000A1Z5")
    inv_no = f"GS-INV-00{variant}"
    inv_date = ["2024-01-18", "2024-02-18", "2024-03-18"][(variant - 1) % 3]

    y = 160
    d.text((40, y), f"Vendor: {vendor[0]}", fill=(20, 20, 20), font=font_b)
    y += 40
    d.text((40, y), f"Vendor GSTIN: {vendor[1]}", fill=(20, 20, 20), font=font_b)
    y += 40
    d.text((40, y), f"Buyer: {buyer[0]}", fill=(20, 20, 20), font=font_b)
    y += 40
    d.text((40, y), f"Buyer GSTIN: {buyer[1]}", fill=(20, 20, 20), font=font_b)
    y += 40
    d.text((40, y), f"Invoice No: {inv_no}", fill=(20, 20, 20), font=font_b)
    y += 40
    d.text((40, y), f"Invoice Date: {inv_date}", fill=(20, 20, 20), font=font_b)

    # Table
    y += 60
    x0 = 40
    x1 = w - 40
    d.rectangle([x0, y, x1, y + 52], outline=(40, 40, 40), fill=(235, 235, 235))
    d.text((x0 + 10, y + 12), "HSN", fill=(10, 22, 40), font=font_m)
    d.text((x0 + 160, y + 12), "Description", fill=(10, 22, 40), font=font_m)
    d.text((x0 + 760, y + 12), "Taxable", fill=(10, 22, 40), font=font_m)
    d.text((x0 + 920, y + 12), "CGST", fill=(10, 22, 40), font=font_m)
    d.text((x0 + 1030, y + 12), "SGST", fill=(10, 22, 40), font=font_m)

    lines = [
        ("8471", "Computer parts", 100000.0),
        ("7308", "Metal fabrication", 50000.0),
    ]
    if variant == 1:
        lines = [("8471", "Computer parts", 100000.0)]
    if variant == 2:
        lines = [("7308", "Metal fabrication", 85000.0)]

    y += 52
    taxable_total = 0.0
    for hsn, desc, txval in lines:
        cgst = round(txval * 0.09, 2)
        sgst = round(txval * 0.09, 2)
        taxable_total += txval
        d.rectangle([x0, y, x1, y + 46], outline=(80, 80, 80), fill=(250, 250, 250))
        d.text((x0 + 10, y + 10), hsn, fill=(20, 20, 20), font=font_m)
        d.text((x0 + 160, y + 10), desc, fill=(20, 20, 20), font=font_m)
        d.text((x0 + 760, y + 10), f"{txval:,.2f}", fill=(20, 20, 20), font=font_m)
        d.text((x0 + 920, y + 10), f"{cgst:,.2f}", fill=(20, 20, 20), font=font_m)
        d.text((x0 + 1030, y + 10), f"{sgst:,.2f}", fill=(20, 20, 20), font=font_m)
        y += 46

    cgst_total = round(taxable_total * 0.09, 2)
    sgst_total = round(taxable_total * 0.09, 2)
    total = round(taxable_total + cgst_total + sgst_total, 2)

    y += 40
    d.text((x0 + 760, y), f"Taxable Value: {taxable_total:,.2f}", fill=(20, 20, 20), font=font_b)
    y += 34
    d.text((x0 + 760, y), f"CGST @9%: {cgst_total:,.2f}", fill=(20, 20, 20), font=font_b)
    y += 34
    d.text((x0 + 760, y), f"SGST @9%: {sgst_total:,.2f}", fill=(20, 20, 20), font=font_b)
    y += 34
    d.text((x0 + 760, y), f"TOTAL INVOICE VALUE: {total:,.2f}", fill=(10, 22, 40), font=font_b)

    y += 70
    d.text((40, y), "This is a TaxIQ DEMO invoice for OCR parsing.", fill=(80, 80, 80), font=font_m)

    img.save(str(path), quality=92)


def ensure_dirs() -> None:
    (_root() / "data" / "sample_bank_statements").mkdir(parents=True, exist_ok=True)
    (_root() / "data" / "mock_gstn").mkdir(parents=True, exist_ok=True)


def ensure_sample_data() -> None:
    ensure_dirs()
    ensure_sample_invoices()

