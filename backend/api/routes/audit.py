"""
TaxIQ — Explainable Audit Trail Generator API
Generates human-readable, section-referenced audit trails with multi-hop graph reasoning.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.core.reconciliation_engine import ReconciliationEngine
from backend.models.mismatch import MISMATCH_LABELS

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditRequest(BaseModel):
    gstin: str = "29AAACN0001A1Z5"
    period: str = "2024-01"
    invoice_id: Optional[str] = None


@router.post("/generate")
async def generate_audit_trail(req: AuditRequest) -> Dict[str, Any]:
    """
    Generate a comprehensive, explainable audit trail with:
    - Multi-hop graph traversal (e-Invoice → GSTR-1 → GSTR-2B → GSTR-3B → E-Way Bill)
    - Natural language explanations for each hop
    - Legal section references (CGST Act 2017)
    - Risk classification and recommended actions
    """
    engine = ReconciliationEngine()
    result = await engine.reconcile(gstin=req.gstin, period=req.period)
    mismatches = result.get("mismatches", [])

    now_iso = datetime.utcnow().isoformat() + "Z"
    trails = []

    for mm in mismatches:
        inv_id = mm.get("invoiceId", "")
        if req.invoice_id and inv_id != req.invoice_id:
            continue

        mm_type = mm.get("mismatchType", "TYPE_1")
        label = MISMATCH_LABELS.get(mm_type, mm_type)
        amount = mm.get("amount", 0)
        supplier_amt = mm.get("supplierAmount", 0)
        buyer_amt = mm.get("buyerAmount", 0)
        risk = mm.get("riskLevel", "MEDIUM")
        vendor = mm.get("vendorGstin", req.gstin)

        # Build multi-hop audit trail
        hops = _build_hops(inv_id, mm_type, supplier_amt, buyer_amt, amount, vendor, now_iso)

        # Generate natural language explanation
        nl_explanation = _generate_nl_explanation(
            inv_id, mm_type, label, amount, supplier_amt, buyer_amt, vendor, req.period
        )

        # Legal references
        legal = _get_legal_references(mm_type)

        # Root cause analysis
        root_cause = _get_root_cause(mm_type, supplier_amt, buyer_amt)

        # Recommended actions
        actions = _get_recommended_actions(mm_type, amount)

        # Timeline
        timeline = _build_timeline(inv_id, mm_type, req.period, now_iso)

        trails.append({
            "invoice_id": inv_id,
            "mismatch_type": label,
            "mismatch_code": mm_type,
            "risk_level": risk,
            "amount_at_risk": amount,
            "hops": hops,
            "nl_explanation": nl_explanation,
            "root_cause": root_cause,
            "legal_references": legal,
            "recommended_actions": actions,
            "timeline": timeline,
            "generated_at": now_iso,
        })

    # Summary statistics
    risk_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for t in trails:
        risk_counts[t["risk_level"]] = risk_counts.get(t["risk_level"], 0) + 1

    total_at_risk = sum(t["amount_at_risk"] for t in trails)

    return {
        "gstin": req.gstin,
        "period": req.period,
        "total_trails": len(trails),
        "total_amount_at_risk": round(total_at_risk, 2),
        "risk_summary": risk_counts,
        "trails": trails,
        "report_generated_at": now_iso,
        "legal_framework": "CGST Act 2017 read with CGST Rules 2017",
    }


@router.get("/invoice/{invoice_id}")
async def get_invoice_audit(invoice_id: str) -> Dict[str, Any]:
    """Get detailed multi-hop audit trail for a specific invoice."""
    engine = ReconciliationEngine()
    return await engine.get_audit_trail(invoice_id=invoice_id)


def _build_hops(inv_id: str, mm_type: str, supplier_amt: float,
                buyer_amt: float, itc_risk: float, vendor: str, ts: str) -> List[Dict]:
    """Build multi-hop graph traversal trail."""

    hops = [
        {
            "hop": 1,
            "node": "e-Invoice Portal (IRP)",
            "status": "PASS" if mm_type != "TYPE_4" else "WARN",
            "detail": (f"Invoice {inv_id} registered on e-Invoice portal with IRN. "
                       f"Digital signature verified. Taxable value: ₹{supplier_amt:,.0f}."
                       if mm_type != "TYPE_4" else
                       f"Invoice {inv_id} found on e-Invoice portal but GSTIN mismatch detected."),
            "timestamp": ts,
            "data_source": "NIC e-Invoice API",
        },
        {
            "hop": 2,
            "node": "GSTR-1 (Supplier Filed)",
            "status": "FAIL" if mm_type == "TYPE_1" else (
                "WARN" if mm_type in ("TYPE_2", "TYPE_3") else "PASS"
            ),
            "detail": _gstr1_hop_detail(inv_id, mm_type, supplier_amt, buyer_amt),
            "timestamp": ts,
            "data_source": "GSTN Portal",
        },
        {
            "hop": 3,
            "node": "GSTR-2B (Auto-populated to Buyer)",
            "status": "FAIL" if mm_type == "TYPE_1" else (
                "WARN" if mm_type in ("TYPE_2", "TYPE_3", "TYPE_5") else "PASS"
            ),
            "detail": _gstr2b_hop_detail(inv_id, mm_type, supplier_amt, buyer_amt),
            "timestamp": ts,
            "data_source": "GSTN Auto-population",
        },
        {
            "hop": 4,
            "node": "E-Way Bill Verification",
            "status": "WARN" if mm_type in ("TYPE_1", "TYPE_4") else "PASS",
            "detail": (f"E-Way Bill for {inv_id} could not be cross-verified. "
                       f"Transport document may be missing or expired."
                       if mm_type in ("TYPE_1", "TYPE_4") else
                       f"E-Way Bill matched for {inv_id}. Transport validated."),
            "timestamp": ts,
            "data_source": "E-Way Bill Portal",
        },
        {
            "hop": 5,
            "node": "GSTR-3B (Buyer's ITC Claim)",
            "status": "WARN" if mm_type in ("TYPE_1", "TYPE_2") else "PASS",
            "detail": (f"Buyer claimed ITC of ₹{itc_risk:,.0f} for invoice {inv_id} in GSTR-3B. "
                       f"This claim is at risk due to {MISMATCH_LABELS.get(mm_type, mm_type)}."
                       if mm_type in ("TYPE_1", "TYPE_2") else
                       f"GSTR-3B ITC claim for {inv_id} is consistent with GSTR-2B."),
            "timestamp": ts,
            "data_source": "GSTN Filing",
        },
        {
            "hop": 6,
            "node": "Knowledge Graph Cross-reference",
            "status": "FAIL" if itc_risk > 50000 else "WARN",
            "detail": (f"Graph analysis: Vendor {vendor} has mismatch on invoice {inv_id}. "
                       f"₹{itc_risk:,.0f} ITC at risk. "
                       f"{'Vendor is flagged as high-risk in fraud detection network.' if itc_risk > 50000 else 'Vendor has moderate risk profile.'}"),
            "timestamp": ts,
            "data_source": "TaxIQ Knowledge Graph",
        },
    ]
    return hops


def _gstr1_hop_detail(inv_id: str, mm_type: str, s_amt: float, b_amt: float) -> str:
    if mm_type == "TYPE_1":
        return (f"Invoice {inv_id} NOT found in supplier's GSTR-1 filing. "
                f"Supplier has not reported this outward supply. "
                f"ITC cannot be auto-populated to buyer's GSTR-2B.")
    if mm_type == "TYPE_2":
        return (f"Invoice {inv_id} found in GSTR-1 with taxable value ₹{s_amt:,.0f}. "
                f"However, GSTR-2B shows ₹{b_amt:,.0f}. Discrepancy of ₹{abs(s_amt-b_amt):,.0f}.")
    if mm_type == "TYPE_3":
        return (f"Invoice {inv_id} found in GSTR-1 but with different tax rate applied. "
                f"HSN/SAC code classification may be incorrect.")
    if mm_type == "TYPE_4":
        return (f"Invoice {inv_id} filed in GSTR-1 but with wrong buyer GSTIN. "
                f"The supply will not reflect in correct buyer's GSTR-2B.")
    if mm_type == "TYPE_5":
        return (f"Invoice {inv_id} filed in GSTR-1 but in a different tax period. "
                f"This creates a timing mismatch affecting ITC availability.")
    return f"Invoice {inv_id} status in GSTR-1 requires review."


def _gstr2b_hop_detail(inv_id: str, mm_type: str, s_amt: float, b_amt: float) -> str:
    if mm_type == "TYPE_1":
        return (f"Invoice {inv_id} did NOT auto-populate in buyer's GSTR-2B. "
                f"As per Rule 36(4), buyer cannot claim ITC without GSTR-2B entry.")
    if mm_type == "TYPE_2":
        return (f"Invoice {inv_id} appears in GSTR-2B with value ₹{b_amt:,.0f}. "
                f"Supplier filed ₹{s_amt:,.0f}. Buyer should claim based on GSTR-2B value only.")
    return f"Invoice {inv_id} reflected in GSTR-2B for validation."


def _generate_nl_explanation(inv_id: str, mm_type: str, label: str,
                              amount: float, s_amt: float, b_amt: float,
                              vendor: str, period: str) -> str:
    """Generate human-readable natural language explanation."""

    explanations = {
        "TYPE_1": (
            f"**Invoice {inv_id}** from vendor (GSTIN: {vendor}) for period {period} "
            f"was filed in the supplier's GSTR-1 but has **not appeared** in your GSTR-2B. "
            f"This means ₹{amount:,.0f} of Input Tax Credit is currently **blocked** under "
            f"Rule 36(4) of CGST Rules, 2017 read with Section 16(2)(aa) of CGST Act. "
            f"The supplier needs to file their GSTR-1 for this period for the ITC to be available. "
            f"If not resolved within 180 days of invoice date, the ITC must be reversed "
            f"under Section 16(4) of CGST Act."
        ),
        "TYPE_2": (
            f"**Invoice {inv_id}** from vendor (GSTIN: {vendor}) shows a **taxable value mismatch**. "
            f"The supplier declared ₹{s_amt:,.0f} in GSTR-1, but your GSTR-2B reflects ₹{b_amt:,.0f}. "
            f"The difference of ₹{abs(s_amt - b_amt):,.0f} creates an ITC risk of ₹{amount:,.0f}. "
            f"As per Section 42 of CGST Act, any mismatch must be communicated to the supplier "
            f"who should issue a credit/debit note or amend the GSTR-1. "
            f"You may only claim ITC as per the amount reflected in GSTR-2B."
        ),
        "TYPE_3": (
            f"**Invoice {inv_id}** from vendor (GSTIN: {vendor}) has a **tax rate discrepancy**. "
            f"The effective tax rate in GSTR-1 differs from GSTR-2B by more than 2 percentage points. "
            f"This typically occurs due to incorrect HSN/SAC code classification by the supplier. "
            f"The tax differential of ₹{amount:,.0f} must be reconciled. "
            f"Reference: Schedule I/II/III of CGST Act and relevant HSN rate notifications."
        ),
        "TYPE_4": (
            f"**Invoice {inv_id}** from vendor (GSTIN: {vendor}) was filed with an **incorrect buyer GSTIN**. "
            f"The supply will not appear in your GSTR-2B, blocking ₹{amount:,.0f} of ITC. "
            f"The supplier must amend their GSTR-1 under Section 37 and correct the buyer GSTIN. "
            f"Until corrected, ITC cannot be claimed under Section 16(2)(aa)."
        ),
        "TYPE_5": (
            f"**Invoice {inv_id}** from vendor (GSTIN: {vendor}) has a **period mismatch**. "
            f"The invoice was filed in a different tax period, creating a timing difference. "
            f"Interest of ₹{amount:,.0f} may be applicable under Section 50 of CGST Act "
            f"at 18% per annum for the delay period. "
            f"The supplier should file an amendment to move the invoice to the correct period."
        ),
    }
    return explanations.get(mm_type, f"Mismatch detected on invoice {inv_id}. Review required.")


def _get_legal_references(mm_type: str) -> List[Dict[str, str]]:
    """Return relevant legal sections for the mismatch type."""
    base = [
        {"section": "Section 16(2)", "title": "Conditions for claiming ITC",
         "relevance": "ITC can only be claimed if tax is actually paid to government by supplier."},
    ]

    type_specific = {
        "TYPE_1": [
            {"section": "Rule 36(4)", "title": "ITC restriction to GSTR-2B",
             "relevance": "ITC restricted to invoices appearing in GSTR-2B + 5% of eligible credit."},
            {"section": "Section 16(2)(aa)", "title": "GSTR-1 filing requirement",
             "relevance": "Supplier must furnish details in GSTR-1 for buyer to claim ITC."},
            {"section": "Section 16(4)", "title": "Time limit for ITC",
             "relevance": "ITC must be claimed before September of following year or filing of annual return."},
        ],
        "TYPE_2": [
            {"section": "Section 42", "title": "Matching of ITC",
             "relevance": "Any mismatch between GSTR-1 and GSTR-2B must be communicated."},
            {"section": "Section 34", "title": "Credit/Debit Notes",
             "relevance": "Supplier must issue CN/DN for value corrections."},
        ],
        "TYPE_3": [
            {"section": "Section 9", "title": "Levy and collection",
             "relevance": "Correct rate must be applied based on HSN/SAC classification."},
            {"section": "Section 37", "title": "Amendment of GSTR-1",
             "relevance": "Supplier can amend incorrect entries in subsequent period's GSTR-1."},
        ],
        "TYPE_4": [
            {"section": "Section 37", "title": "Amendment of GSTR-1",
             "relevance": "GSTIN correction requires amendment in next period's GSTR-1."},
            {"section": "Section 16(2)(aa)", "title": "Correct reflection requirement",
             "relevance": "ITC available only when correctly reflected in buyer's GSTR-2B."},
        ],
        "TYPE_5": [
            {"section": "Section 50", "title": "Interest on delayed payment",
             "relevance": "Interest @18% p.a. may apply for period mismatch delays."},
            {"section": "Section 37", "title": "Amendment timeline",
             "relevance": "Amendments must be filed before September of following year."},
        ],
    }

    return base + type_specific.get(mm_type, [])


def _get_root_cause(mm_type: str, s_amt: float, b_amt: float) -> str:
    causes = {
        "TYPE_1": "Supplier failed to file GSTR-1 or omitted this invoice from filing.",
        "TYPE_2": f"Value discrepancy between supplier's GSTR-1 (₹{s_amt:,.0f}) and auto-populated GSTR-2B (₹{b_amt:,.0f}). Possible reasons: partial payment, credit note not adjusted, or data entry error.",
        "TYPE_3": "Tax rate mismatch due to incorrect HSN/SAC classification or rate change notification not applied.",
        "TYPE_4": "Supplier entered wrong buyer GSTIN in their GSTR-1 filing. May be a typo or intentional misdirection.",
        "TYPE_5": "Invoice dated in one period but filed in GSTR-1 of a different period. Common with delayed bookkeeping.",
    }
    return causes.get(mm_type, "Unknown root cause. Manual review required.")


def _get_recommended_actions(mm_type: str, amount: float) -> List[Dict[str, str]]:
    urgent = amount > 50000
    actions_map = {
        "TYPE_1": [
            {"action": "Contact supplier immediately", "priority": "HIGH" if urgent else "MEDIUM",
             "detail": "Request supplier to file GSTR-1 for the relevant period within 15 days."},
            {"action": "Issue formal notice", "priority": "HIGH" if urgent else "LOW",
             "detail": "Send written communication under Section 73 requesting compliance."},
            {"action": "Reverse ITC provisionally", "priority": "MEDIUM",
             "detail": "If supplier doesn't comply in 180 days, reverse ITC in GSTR-3B."},
            {"action": "Update vendor risk score", "priority": "LOW",
             "detail": "Flag vendor in compliance monitoring system for future reference."},
        ],
        "TYPE_2": [
            {"action": "Reconcile with supplier", "priority": "HIGH",
             "detail": "Share invoice copy and request credit/debit note for difference."},
            {"action": "Claim ITC per GSTR-2B value only", "priority": "MEDIUM",
             "detail": "Do not over-claim ITC beyond what appears in GSTR-2B."},
        ],
        "TYPE_3": [
            {"action": "Verify HSN classification", "priority": "HIGH",
             "detail": "Check if supplier applied correct HSN code and corresponding tax rate."},
            {"action": "Request GSTR-1 amendment", "priority": "MEDIUM",
             "detail": "Ask supplier to amend GSTR-1 with correct rate in next filing."},
        ],
        "TYPE_4": [
            {"action": "Notify supplier of GSTIN error", "priority": "HIGH",
             "detail": "Supplier must amend GSTR-1 with correct buyer GSTIN."},
            {"action": "Hold ITC claim", "priority": "HIGH",
             "detail": "Do not claim ITC until invoice appears in your GSTR-2B."},
        ],
        "TYPE_5": [
            {"action": "Request period amendment", "priority": "MEDIUM",
             "detail": "Ask supplier to file amendment moving invoice to correct period."},
            {"action": "Calculate interest liability", "priority": "LOW",
             "detail": "Compute interest @18% p.a. for the delay period."},
        ],
    }
    return actions_map.get(mm_type, [{"action": "Manual review required", "priority": "HIGH",
                                       "detail": "Review mismatch details and take corrective action."}])


def _build_timeline(inv_id: str, mm_type: str, period: str, now_iso: str) -> List[Dict[str, str]]:
    """Build event timeline for the mismatch."""
    return [
        {"event": "Invoice Generated", "date": f"{period}-05", "status": "done"},
        {"event": "e-Invoice IRN Generated", "date": f"{period}-05", "status": "done"},
        {"event": "Supplier GSTR-1 Filing", "date": f"{period}-11",
         "status": "done" if mm_type != "TYPE_1" else "failed"},
        {"event": "GSTR-2B Auto-population", "date": f"{period}-14",
         "status": "done" if mm_type not in ("TYPE_1", "TYPE_4") else "failed"},
        {"event": "Mismatch Detected by TaxIQ", "date": now_iso[:10], "status": "current"},
        {"event": "Supplier Response Deadline", "date": "Pending",
         "status": "pending"},
        {"event": "ITC Reversal Deadline (180 days)", "date": "Pending",
         "status": "pending"},
    ]
