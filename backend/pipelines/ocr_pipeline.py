import os
import re
from typing import List

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


def _preprocess(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
    return thr


def _clean_text(text: str) -> str:
    t = text.replace("\x0c", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _ocr_pil(pil_img: Image.Image) -> str:
    img = np.array(pil_img.convert("RGB"))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    prep = _preprocess(img_bgr)
    config = "--oem 3 --psm 6"
    try:
        return pytesseract.image_to_string(prep, config=config)
    except Exception:
        # If Tesseract isn't installed/configured, return empty string;
        # downstream invoice parser will fall back to DEMO LLM output.
        return ""


def extract_text_from_image(image_path: str) -> str:
    """
    Image/PDF -> OCR -> cleaned raw text.
    PDF inputs are converted to images via pdf2image.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    ext = os.path.splitext(image_path)[1].lower()
    texts: List[str] = []

    if ext == ".pdf":
        pages = convert_from_path(image_path, dpi=220)
        for p in pages:
            texts.append(_ocr_pil(p))
    else:
        pil_img = Image.open(image_path)
        texts.append(_ocr_pil(pil_img))

    return _clean_text("\n\n".join(texts))

