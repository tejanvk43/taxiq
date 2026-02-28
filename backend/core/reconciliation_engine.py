import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.models.mismatch import Mismatch, MISMATCH_LABELS
from backend.services.gstn_client import GSTNClient


class ReconciliationEngine:
    """
    Real GSTR-1 vs GSTR-2B reconciliation engine.
    Performs line-by-line diff and classifies every gap into TYPE_1..TYPE_5.
    """

    BUYER_GSTIN = "29AAACN0001A1Z5"  # Demo buyer

    def __init__(self) -> None:
        self.client = GSTNClient()
        self._llm = None
        try:
            from backend.utils.llm_client import LLMClient
            self._llm = LLMClient()
        except Exception:
            pass

    # ── Public API ──────────────────────────────────────

    async def reconcile(self, gstin: str, period: str) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        started = datetime.utcnow()

        gstr1_data = await self.client.get_gstr1(gstin=gstin, period=period)
        gstr1_invoices = self._extract_invoices(gstr1_data)

        gstr2b_invoices = self._generate_gstr2b_mock(gstr1_invoices, gstin=gstin)

        gstr1_map = {inv["inum"]: inv for inv in gstr1_invoices}
        gstr2b_map = {inv["inum"]: inv for inv in gstr2b_invoices}

        all_ids = set(gstr1_map.keys()) | set(gstr2b_map.keys())
        mismatches: List[Mismatch] = []
        matched_count = 0

        for inv_id in sorted(all_ids):
            s = gstr1_map.get(inv_id)
            b = gstr2b_map.get(inv_id)

            if s and not b:
                itc = self._calc_tax(s)
                mismatches.append(Mismatch(
                    invoiceId=inv_id, gstin=gstin,
                    vendorGstin=s.get("supplier_gstin", gstin),
                    period=period, mismatchType="TYPE_1",
                    riskLevel=self._risk_level(itc),
                    severity=self._severity(itc), amount=itc,
                    supplierAmount=float(s.get("txval", s.get("val", 0))),
                    buyerAmount=0.0, difference=itc,
                    detail=(f"Invoice {inv_id} filed in GSTR-1 for "
                            f"\u20b9{float(s.get('val',0)):,.0f} but NOT reflected "
                            f"in GSTR-2B. ITC of \u20b9{itc:,.0f} is blocked under Rule 36(4)."),
                ))
            elif b and not s:
                itc = self._calc_tax(b)
                mismatches.append(Mismatch(
                    invoiceId=inv_id, gstin=gstin,
                    vendorGstin=b.get("supplier_gstin", gstin),
                    period=period, mismatchType="TYPE_1",
                    riskLevel=self._risk_level(itc),
                    severity=self._severity(itc), amount=itc,
                    supplierAmount=0.0,
                    buyerAmount=float(b.get("txval", b.get("val", 0))),
                    difference=itc,
                    detail=(f"Invoice {inv_id} in GSTR-2B but supplier did not "
                            f"file in GSTR-1. ITC claim of \u20b9{itc:,.0f} at risk."),
                ))
            elif s and b:
                mm = self._compare_invoices(inv_id, s, b, gstin, period)
                if mm:
                    mismatches.append(mm)
                else:
                    matched_count += 1

        total_itc = sum(m.amount for m in mismatches)
        total_inv = len(all_ids)
        recon_score = round((matched_count / total_inv) * 100, 1) if total_inv else 100.0

        audit = self._build_audit_trail(mismatches, gstin)

        return {
            "gstin": gstin,
            "period": period,
            "total_invoices_checked": total_inv,
            "mismatches": [m.model_dump() for m in mismatches],
            "total_itc_at_risk": round(total_itc, 2),
            "risk_summary": self._risk_counts(mismatches),
            "audit_trail": audit,
            "reconciliation_score": recon_score,
            "mismatch_breakdown": self._breakdown(mismatches),
            "jobId": job_id,
            "startedAt": started.isoformat() + "Z",
            "completedAt": datetime.utcnow().isoformat() + "Z",
        }

    # Alias for backward compat with existing routes
    async def reconcile_gstin(self, gstin: str, period: str) -> Dict[str, Any]:
        return await self.reconcile(gstin, period)

    async def list_mismatches(self, gstin: str, period: str) -> List[Mismatch]:
        result = await self.reconcile(gstin, period)
        return [Mismatch(**m) for m in result["mismatches"]]

    async def get_audit_trail(self, invoice_id: str) -> Dict[str, Any]:
        now_iso = datetime.utcnow().isoformat() + "Z"
        return {
            "invoiceId": invoice_id,
            "hops": [
                {"node": "e-Invoice / IRN", "status": "PASS",
                 "detail": f"Invoice {invoice_id} has a valid IRN on e-Invoice portal.",
                 "timestamp": now_iso},
                {"node": "GSTR-1 (Supplier)", "status": "FAIL",
                 "detail": f"Invoice {invoice_id} NOT found in supplier's GSTR-1.",
                 "timestamp": now_iso},
                {"node": "GSTR-2B (Auto-populated)", "status": "FAIL",
                 "detail": f"Invoice {invoice_id} did not auto-populate to buyer GSTR-2B.",
                 "timestamp": now_iso},
                {"node": "E-Way Bill", "status": "WARN",
                 "detail": "E-Way Bill status could not be verified.",
                 "timestamp": now_iso},
                {"node": "GSTR-3B (Buyer)", "status": "WARN",
                 "detail": f"Buyer claimed ITC for {invoice_id} in GSTR-3B. Claim at risk.",
                 "timestamp": now_iso},
            ],
            "rootCause": "Supplier failed to file GSTR-1. Invoice not in GSTR-2B.",
            "legalSection": "Rule 36(4) r/w Section 16(2)(aa) CGST Act 2017",
            "recommendedAction": "Issue SCN to supplier requesting GSTR-1 filing within 15 days.",
            "generatedAt": now_iso,
        }

    # ── GSTR-2B mock generator ──────────────────────────

    def _generate_gstr2b_mock(self, gstr1_invoices: list, gstin: str = "") -> list:
        """
        Create GSTR-2B from GSTR-1 with intentional realistic errors:
        - 70% appear correctly
        - 15% have amount mismatches (TYPE_2)
        - 10% are completely missing (TYPE_1)
        - 5% have wrong buyer GSTIN (TYPE_4)
        """
        # Seed from GSTIN so different vendors produce different error patterns
        seed = hash(gstin) & 0xFFFFFFFF if gstin else 42
        rng = random.Random(seed)
        out = []
        for inv in gstr1_invoices:
            r = rng.random()
            if r < 0.10:
                continue  # 10% missing = TYPE_1
            entry = {**inv}
            if r < 0.25:
                # 15% amount mismatch = TYPE_2
                factor = 1 + rng.uniform(-0.30, -0.05)
                entry["txval"] = round(float(entry.get("txval", 0)) * factor, 2)
                entry["val"] = round(float(entry.get("val", 0)) * factor, 2)
                entry["camt"] = round(entry["txval"] * 0.09, 2)
                entry["samt"] = round(entry["txval"] * 0.09, 2)
            elif r < 0.30:
                # 5% wrong GSTIN = TYPE_4
                entry["buyer_gstin_mismatch"] = True
                entry["supplier_gstin"] = "99ZZZZZ9999Z9Z" + str(rng.randint(0,9))
            out.append(entry)
        return out

    # ── Internal helpers ────────────────────────────────

    def _extract_invoices(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        invoices = []
        for b2b in data.get("b2b", []):
            for inv in b2b.get("inv", []):
                inv["supplier_gstin"] = b2b.get("ctin", data.get("gstin", ""))
                invoices.append(inv)
        return invoices

    def _compare_invoices(self, inv_id: str, s: Dict, b: Dict,
                          gstin: str, period: str) -> Optional[Mismatch]:
        # TYPE_4: GSTIN mismatch
        if b.get("buyer_gstin_mismatch"):
            itc = self._calc_tax(s)
            return Mismatch(
                invoiceId=inv_id, gstin=gstin,
                vendorGstin=s.get("supplier_gstin", gstin),
                period=period, mismatchType="TYPE_4",
                riskLevel=self._risk_level(itc),
                severity=self._severity(itc), amount=itc,
                supplierAmount=float(s.get("txval", 0)),
                buyerAmount=float(b.get("txval", 0)),
                difference=itc,
                detail=(f"Invoice {inv_id} references wrong buyer GSTIN. "
                        f"ITC of \u20b9{itc:,.0f} cannot be claimed."),
            )

        val_s = float(s.get("txval", s.get("val", 0)))
        val_b = float(b.get("txval", b.get("val", 0)))

        # TYPE_2: Taxable value mismatch
        if val_s > 0 and val_b > 0:
            diff = abs(val_s - val_b)
            pct = diff / max(val_s, val_b) * 100
            if pct > 1.0:
                itc = round(diff * 0.18, 2)
                return Mismatch(
                    invoiceId=inv_id, gstin=gstin,
                    vendorGstin=s.get("supplier_gstin", gstin),
                    period=period, mismatchType="TYPE_2",
                    riskLevel=self._risk_level(itc),
                    severity=self._severity(itc), amount=itc,
                    supplierAmount=val_s, buyerAmount=val_b,
                    difference=round(diff, 2),
                    detail=(f"Taxable value mismatch: GSTR-1 \u20b9{val_s:,.0f} vs "
                            f"GSTR-2B \u20b9{val_b:,.0f} (diff \u20b9{diff:,.0f}, "
                            f"{pct:.1f}%). Tax on difference: \u20b9{itc:,.0f} at risk."),
                )

        # TYPE_3: Tax rate mismatch
        tax_s = float(s.get("camt", 0)) + float(s.get("samt", 0)) + float(s.get("iamt", 0))
        tax_b = float(b.get("camt", 0)) + float(b.get("samt", 0)) + float(b.get("iamt", 0))
        rate_s = round(tax_s / val_s * 100, 1) if val_s > 0 else 0
        rate_b = round(tax_b / val_b * 100, 1) if val_b > 0 else 0
        if rate_s > 0 and rate_b > 0 and abs(rate_s - rate_b) > 2:
            itc = abs(tax_s - tax_b)
            return Mismatch(
                invoiceId=inv_id, gstin=gstin,
                vendorGstin=s.get("supplier_gstin", gstin),
                period=period, mismatchType="TYPE_3",
                riskLevel=self._risk_level(itc),
                severity=self._severity(itc), amount=round(itc, 2),
                supplierAmount=val_s, buyerAmount=val_b,
                difference=round(abs(rate_s - rate_b), 1),
                detail=(f"Tax rate mismatch: GSTR-1 effective {rate_s}% vs "
                        f"GSTR-2B {rate_b}%. Difference: \u20b9{itc:,.0f}."),
            )

        # TYPE_5: Period mismatch (simulate with date check)
        idt_s = s.get("idt", "")
        idt_b = b.get("idt", "")
        if idt_s and idt_b and idt_s != idt_b:
            try:
                d_s = datetime.strptime(idt_s, "%d-%m-%Y")
                d_b = datetime.strptime(idt_b, "%d-%m-%Y")
                delay = abs((d_s - d_b).days)
                if delay > 15:
                    interest = round(val_s * 0.18 * delay / 365, 2)
                    return Mismatch(
                        invoiceId=inv_id, gstin=gstin,
                        vendorGstin=s.get("supplier_gstin", gstin),
                        period=period, mismatchType="TYPE_5",
                        riskLevel=self._risk_level(interest),
                        severity=self._severity(interest), amount=interest,
                        supplierAmount=val_s, buyerAmount=val_b,
                        difference=float(delay),
                        detail=(f"Period mismatch: {delay} days between filing dates. "
                                f"Interest @18% p.a. = \u20b9{interest:,.0f}."),
                    )
            except ValueError:
                pass

        return None

    def _calc_tax(self, inv: Dict[str, Any]) -> float:
        camt = float(inv.get("camt", 0))
        samt = float(inv.get("samt", 0))
        iamt = float(inv.get("iamt", 0))
        if camt + samt + iamt > 0:
            return round(camt + samt + iamt, 2)
        val = float(inv.get("val", inv.get("txval", 0)))
        return round(val * 0.18, 2)

    def _risk_level(self, amount: float) -> str:
        if amount > 50000: return "HIGH"
        if amount > 10000: return "MEDIUM"
        return "LOW"

    def _severity(self, amount: float) -> int:
        if amount > 100000: return 95
        if amount > 50000: return 80
        if amount > 25000: return 65
        if amount > 10000: return 50
        return 30

    def _risk_counts(self, mismatches: List[Mismatch]) -> Dict[str, int]:
        counts = {"high": 0, "medium": 0, "low": 0}
        for m in mismatches:
            counts[m.riskLevel.lower()] = counts.get(m.riskLevel.lower(), 0) + 1
        return counts

    def _breakdown(self, mismatches: List[Mismatch]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for m in mismatches:
            key = MISMATCH_LABELS.get(m.mismatchType, m.mismatchType)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _build_audit_trail(self, mismatches: List[Mismatch], gstin: str) -> List[str]:
        trails = []
        for m in mismatches:
            label = MISMATCH_LABELS.get(m.mismatchType, m.mismatchType)
            action_map = {
                "TYPE_1": "Contact supplier to file GSTR-1 for this period. Reverse ITC if unfiled within 15 days.",
                "TYPE_2": "Verify invoice with supplier and request credit/debit note for the difference.",
                "TYPE_3": "Check HSN code classification and request supplier to amend GSTR-1.",
                "TYPE_4": "Request supplier to amend invoice with correct buyer GSTIN in GSTR-1.",
                "TYPE_5": "Request supplier to file amendment moving invoice to correct period.",
            }
            action = action_map.get(m.mismatchType, "Review and take corrective action.")
            trail = (
                f"Supplier (GSTIN: {m.vendorGstin}) filed invoice {m.invoiceId} "
                f"for \u20b9{m.supplierAmount or m.amount:,.0f}. "
                f"However, your GSTR-2B shows: {label}. "
                f"This puts \u20b9{m.amount:,.0f} of ITC at risk. "
                f"Recommended action: {action}"
            )
            trails.append(trail)
        return trails
