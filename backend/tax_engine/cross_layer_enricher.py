"""
TaxIQ — Cross-Layer Deduction Discovery
Scans GST invoices for missed ITR deductions. This is the unique moat.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger


class CrossLayerEnricher:
    """
    Scans invoices stored in PostgreSQL/memory and surfaces
    business purchases that may qualify as ITR deductions.
    This is the feature no competitor has: GST data → ITR deductions.
    """

    # Map GST HSN codes to potential income tax deductions
    HSN_TO_DEDUCTION: Dict[str, tuple] = {
        "8471": ("Computer/Laptop", "Section 32 Depreciation"),
        "8517": ("Mobile Phone", "Section 32 Depreciation"),
        "9403": ("Office Furniture", "Section 32 Depreciation"),
        "9801": ("Software", "Section 37 Business Expense"),
        "8504": ("UPS/Battery", "Section 37 Business Expense"),
        "4901": ("Books/Publications", "Section 37 Business Expense"),
        "9018": ("Medical Equipment", "Section 35AD"),
        "4820": ("Stationery", "Section 37 Business Expense"),
        "8443": ("Printer/Scanner", "Section 32 Depreciation"),
        "8528": ("Monitor/Display", "Section 32 Depreciation"),
        "9401": ("Office Chair", "Section 32 Depreciation"),
        "8415": ("Air Conditioner", "Section 32 Depreciation"),
    }

    # Map vendor name keywords to deductions
    VENDOR_KEYWORDS: Dict[str, tuple] = {
        "insurance": ("Insurance Premium", "Section 80D"),
        "health": ("Health Insurance", "Section 80D"),
        "star health": ("Health Insurance", "Section 80D"),
        "bajaj allianz": ("Insurance Premium", "Section 80D"),
        "nps": ("NPS Contribution", "Section 80CCD"),
        "pension": ("Pension Contribution", "Section 80CCD"),
        "hospital": ("Medical Expense", "Section 80DDB"),
        "school": ("Tuition Fees", "Section 80C"),
        "college": ("Tuition Fees", "Section 80C"),
        "academy": ("Education/Training", "Section 80C"),
        "university": ("Tuition Fees", "Section 80C"),
        "lic": ("Life Insurance", "Section 80C"),
        "mutual fund": ("ELSS/Mutual Fund", "Section 80C"),
        "elss": ("ELSS Tax Saver", "Section 80C"),
    }

    # Tax rate for estimation (30% slab + 4% cess)
    ESTIMATED_TAX_RATE = 0.312

    def __init__(self):
        self._llm = None
        try:
            from backend.utils.llm_client import LLMClient
            self._llm = LLMClient()
        except Exception:
            pass

    def find_missed_deductions(
        self,
        invoices: list,
        existing_deductions: dict,
    ) -> List[Dict[str, Any]]:
        """
        Scan GST invoices for missed ITR deductions.

        Args:
            invoices: List of invoice dicts with keys like
                      invoiceId, vendor_name, amount, hsn_code, etc.
            existing_deductions: Dict of already-claimed deductions
                                 keyed by section (e.g. {"80C": 120000})

        Returns:
            List of potential deductions sorted by estimated_tax_saved DESC.
        """
        claimed_sections = set(existing_deductions.keys())
        results: List[Dict[str, Any]] = []

        for inv in invoices:
            inv_id = inv.get("invoiceId", inv.get("inum", inv.get("InvoiceNo", "")))
            vendor = inv.get("vendor_name", inv.get("Vendor", inv.get("tradeName", "")))
            amount = float(inv.get("amount", inv.get("Amount", inv.get("txval", inv.get("val", 0)))))
            hsn = str(inv.get("hsn_code", inv.get("HSN", inv.get("hsn", ""))))

            if amount <= 0:
                continue

            # Strategy 1: HSN code match
            if hsn in self.HSN_TO_DEDUCTION:
                desc, section = self.HSN_TO_DEDUCTION[hsn]
                tax_saved = round(amount * self.ESTIMATED_TAX_RATE, 2)
                sec_key = section.split()[-1] if " " in section else section
                # Skip if already claimed under this section
                if sec_key in claimed_sections:
                    continue
                results.append({
                    "invoice_id": inv_id,
                    "vendor_name": vendor,
                    "amount": amount,
                    "hsn_code": hsn,
                    "suggested_deduction": desc,
                    "tax_section": section,
                    "estimated_tax_saved": tax_saved,
                    "confidence": 0.85,
                    "note": (
                        f"This ₹{amount:,.0f} purchase from {vendor} "
                        f"(HSN {hsn}: {desc}) may qualify under {section}."
                    ),
                })
                continue

            # Strategy 2: Vendor name keyword match
            vendor_lower = vendor.lower()
            matched = False
            for keyword, (desc, section) in self.VENDOR_KEYWORDS.items():
                if keyword in vendor_lower:
                    tax_saved = round(amount * self.ESTIMATED_TAX_RATE, 2)
                    sec_key = section.split()[-1] if " " in section else section
                    if sec_key in claimed_sections:
                        continue
                    results.append({
                        "invoice_id": inv_id,
                        "vendor_name": vendor,
                        "amount": amount,
                        "hsn_code": hsn,
                        "suggested_deduction": desc,
                        "tax_section": section,
                        "estimated_tax_saved": tax_saved,
                        "confidence": 0.70,
                        "note": (
                            f"This ₹{amount:,.0f} payment to {vendor} "
                            f"suggests {desc} — may qualify under {section}."
                        ),
                    })
                    matched = True
                    break

        # Sort by estimated_tax_saved DESC
        results.sort(key=lambda x: x["estimated_tax_saved"], reverse=True)
        return results

    def generate_enrichment_report(
        self,
        invoices: list,
        bank_deductions: dict,
    ) -> str:
        """
        Generate a plain English + Hindi summary of cross-layer findings.
        Uses Claude if available, else template.
        """
        missed = self.find_missed_deductions(invoices, bank_deductions)
        if not missed:
            return (
                "No additional deductions found in your GST invoices "
                "beyond what was identified in your bank statement.\n\n"
                "आपके GST चालान में कोई अतिरिक्त कटौती नहीं मिली।"
            )

        total_saved = sum(d["estimated_tax_saved"] for d in missed)
        count = len(missed)

        # Try LLM
        if self._llm:
            try:
                prompt = (
                    f"We found {count} potential deductions in GST invoices "
                    f"not present in bank statement analysis. "
                    f"Total potential tax saving: ₹{total_saved:,.0f}. "
                    f"Top finds: "
                    + "; ".join(
                        f"₹{d['amount']:,.0f} from {d['vendor_name']} → {d['tax_section']}"
                        for d in missed[:3]
                    )
                    + ". Write a concise 4-line summary in English, then 2 lines in Hindi."
                )
                return self._llm.ask(prompt)
            except Exception:
                pass

        # Template fallback
        lines = [
            f"We found {count} potential deductions in your GST invoices "
            f"that weren't in your bank statement analysis.",
            f"These could save you an additional ₹{total_saved:,.0f} in taxes.",
            "",
            "Top finds:",
        ]
        for i, d in enumerate(missed[:5], 1):
            lines.append(
                f"{i}. ₹{d['amount']:,.0f} purchase from {d['vendor_name']} "
                f"→ qualifies under {d['tax_section']}"
            )
        lines.append("")
        lines.append(
            f"हमें आपके GST चालान में {count} अतिरिक्त कटौतियाँ मिलीं "
            f"जो आपके बैंक स्टेटमेंट में नहीं थीं। "
            f"इनसे आप ₹{total_saved:,.0f} तक बचा सकते हैं।"
        )
        return "\n".join(lines)
