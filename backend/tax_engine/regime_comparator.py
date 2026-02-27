from __future__ import annotations


def _cess(tax: float) -> float:
    return tax * 1.04


def calculate_old_regime_tax(income: float, deductions: float) -> float:
    """
    FY2024-25 OLD REGIME slabs:
      0-2.5L: 0%
      2.5-5L: 5%
      5-10L: 20%
      10L+: 30%
    + 4% cess
    + 87A: full rebate if taxable income <= 5L
    """
    taxable = max(0.0, income - max(0.0, deductions))
    if taxable <= 250000:
        tax = 0.0
    elif taxable <= 500000:
        tax = (taxable - 250000) * 0.05
    elif taxable <= 1000000:
        tax = 250000 * 0.05 + (taxable - 500000) * 0.20
    else:
        tax = 250000 * 0.05 + 500000 * 0.20 + (taxable - 1000000) * 0.30

    if taxable <= 500000:
        tax = 0.0
    return _cess(tax)


def calculate_new_regime_tax(income: float) -> float:
    """
    FY2024-25 NEW REGIME slabs (updated):
      0-3L: 0%
      3-7L: 5%
      7-10L: 10%
      10-12L: 15%
      12-15L: 20%
      15L+: 30%
    + 4% cess
    + 87A: full rebate if taxable income <= 7L
    Standard deduction: 75,000 (FY2024-25)
    """
    taxable = max(0.0, income - 75000.0)

    if taxable <= 300000:
        tax = 0.0
    elif taxable <= 700000:
        tax = (taxable - 300000) * 0.05
    elif taxable <= 1000000:
        tax = 400000 * 0.05 + (taxable - 700000) * 0.10
    elif taxable <= 1200000:
        tax = 400000 * 0.05 + 300000 * 0.10 + (taxable - 1000000) * 0.15
    elif taxable <= 1500000:
        tax = 400000 * 0.05 + 300000 * 0.10 + 200000 * 0.15 + (taxable - 1200000) * 0.20
    else:
        tax = (
            400000 * 0.05
            + 300000 * 0.10
            + 200000 * 0.15
            + 300000 * 0.20
            + (taxable - 1500000) * 0.30
        )

    if taxable <= 700000:
        tax = 0.0
    return _cess(tax)

