from __future__ import annotations

from typing import Dict


_HINDI_PHRASES: Dict[str, str] = {
    "You can do this.": "आप यह कर सकते हैं।",
    "Start today.": "आज ही शुरू करें।",
    "Every rupee invested now saves tax later.": "आज निवेश किया गया हर रुपया बाद में कर बचाता है।",
}


def to_hindi(text: str) -> str:
    """
    Lightweight, deterministic translator for demo (no external APIs).
    If exact phrase not found, returns the input text.
    """
    t = (text or "").strip()
    return _HINDI_PHRASES.get(t, t)


def translate(text: str, lang: str = "hi") -> str:
    if lang.lower().startswith("hi"):
        return to_hindi(text)
    return text

