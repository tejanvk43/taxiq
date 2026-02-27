import re
from typing import Dict

from backend.utils.llm_client import LLMClient


_KEYWORDS = {
    "80C": [
        "ppf",
        "elss",
        "lic",
        "nsc",
        "life insurance",
        "mutual fund",
        "provident fund",
        "tuition fee",
    ],
    "80D": ["health insurance", "mediclaim", "star health", "max bupa", "hdfc ergo"],
    "NPS": ["nps", "national pension", "pension scheme"],
    "HOME_LOAN": ["home loan", "housing loan", "emi"],
    "MEDICAL": ["hospital", "pharmacy", "medical", "clinic"],
    "FOOD": ["swiggy", "zomato", "restaurant", "cafe"],
    "SHOPPING": ["amazon", "flipkart", "myntra"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def classify_transaction(description: str, amount: float) -> Dict:
    """
    Keyword match first; else call Claude.
    Returns: {category, tax_section, is_deductible, confidence}
    """
    d = _norm(description)

    for section, keys in _KEYWORDS.items():
        if any(k in d for k in keys):
            if section in {"80C", "80D"}:
                return {"category": section, "tax_section": section, "is_deductible": True, "confidence": 0.92}
            if section == "NPS":
                return {"category": "NPS", "tax_section": "80CCD1B", "is_deductible": True, "confidence": 0.9}
            if section == "HOME_LOAN":
                return {"category": "HOME_LOAN", "tax_section": "24B", "is_deductible": True, "confidence": 0.85}
            if section == "MEDICAL":
                return {"category": "MEDICAL", "tax_section": "80D", "is_deductible": False, "confidence": 0.55}
            return {"category": section, "tax_section": "", "is_deductible": False, "confidence": 0.75}

    # LLM fallback
    llm = LLMClient()
    prompt = (
        "Classify this Indian bank transaction into a category and whether it is tax-deductible.\n"
        "Return ONLY valid JSON with keys: category, tax_section, is_deductible, confidence.\n"
        f"Description: {description}\nAmount: {amount}\n"
    )
    try:
        data = llm.ask_json(prompt)
        return {
            "category": str(data.get("category", "OTHER")),
            "tax_section": str(data.get("tax_section", "")),
            "is_deductible": bool(data.get("is_deductible", False)),
            "confidence": float(data.get("confidence", 0.5)),
        }
    except Exception:
        return {"category": "OTHER", "tax_section": "", "is_deductible": False, "confidence": 0.4}

