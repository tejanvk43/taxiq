-- TaxIQ Postgres schema (minimal but complete for demo)

CREATE TABLE IF NOT EXISTS invoices (
  id SERIAL PRIMARY KEY,
  invoice_number TEXT NOT NULL,
  invoice_date DATE NOT NULL,
  vendor_name TEXT NOT NULL,
  vendor_gstin TEXT,
  buyer_gstin TEXT,
  total_value NUMERIC NOT NULL,
  taxable_value NUMERIC NOT NULL,
  cgst NUMERIC NOT NULL DEFAULT 0,
  sgst NUMERIC NOT NULL DEFAULT 0,
  igst NUMERIC NOT NULL DEFAULT 0,
  confidence_score NUMERIC NOT NULL DEFAULT 1,
  raw_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoices_vendor_gstin ON invoices(vendor_gstin);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_date ON invoices(invoice_date);

CREATE TABLE IF NOT EXISTS bank_transactions (
  id SERIAL PRIMARY KEY,
  txn_date DATE NOT NULL,
  description TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  txn_type TEXT NOT NULL,
  tax_category TEXT,
  tax_section TEXT,
  is_deductible BOOLEAN NOT NULL DEFAULT FALSE,
  confidence NUMERIC NOT NULL DEFAULT 0.5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bank_txn_date ON bank_transactions(txn_date);

