import pandas as pd

from backend.tax_engine.classifier import classify_transaction


def _find_col(cols: list[str], candidates: list[str]) -> str | None:
    low = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in low:
            return low[cand.lower()]
    return None


def parse_bank_statement(csv_path: str) -> pd.DataFrame:
    """
    Parse common Indian bank CSVs and normalize:
    date, description, amount, txn_type
    Then add: tax_category, tax_section, is_deductible, confidence
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    date_col = _find_col(df.columns.tolist(), ["Date", "Txn Date", "Transaction Date", "Value Date"])
    desc_col = _find_col(df.columns.tolist(), ["Description", "Narration", "Particulars", "Remarks"])
    debit_col = _find_col(df.columns.tolist(), ["Debit", "Withdrawal", "Dr Amount", "Debit Amount"])
    credit_col = _find_col(df.columns.tolist(), ["Credit", "Deposit", "Cr Amount", "Credit Amount"])

    if not date_col or not desc_col or (not debit_col and not credit_col):
        raise ValueError("Unsupported bank CSV format. Expected columns like Date/Description and Debit/Credit.")

    # date parse (multi-format)
    df["_date"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True, infer_datetime_format=True)
    if df["_date"].isna().all():
        df["_date"] = pd.to_datetime(df[date_col], errors="coerce", format="%d-%m-%Y")

    df["_desc"] = df[desc_col].astype(str).fillna("")

    debit = df[debit_col].fillna(0) if debit_col else 0
    credit = df[credit_col].fillna(0) if credit_col else 0

    # normalize amount + txn_type
    amount = []
    txn_type = []
    for d, c in zip(pd.to_numeric(debit, errors="coerce").fillna(0), pd.to_numeric(credit, errors="coerce").fillna(0)):
        if c > 0:
            amount.append(float(c))
            txn_type.append("CREDIT")
        else:
            amount.append(float(d))
            txn_type.append("DEBIT")

    out = pd.DataFrame(
        {
            "date": df["_date"].dt.strftime("%Y-%m-%d"),
            "description": df["_desc"],
            "amount": amount,
            "txn_type": txn_type,
        }
    )

    # classify
    cats = []
    secs = []
    deduct = []
    conf = []
    for desc, amt in zip(out["description"].tolist(), out["amount"].tolist()):
        r = classify_transaction(description=desc, amount=float(amt))
        cats.append(r["category"])
        secs.append(r["tax_section"])
        deduct.append(bool(r["is_deductible"]))
        conf.append(float(r["confidence"]))

    out["tax_category"] = cats
    out["tax_section"] = secs
    out["is_deductible"] = deduct
    out["confidence"] = conf
    return out

