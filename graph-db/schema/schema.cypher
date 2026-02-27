// === NODE LABELS (DOCUMENTATION) ===
// (:Taxpayer {gstin, pan, name, state, type, registrationDate, nexusScore, riskLevel, complianceScore})
// (:Invoice  {invoiceId, irn, amount, taxAmount, igst, cgst, sgst, date, status})
// (:GSTR1    {filingId, period, filedOn, status})
// (:GSTR2B   {period, generatedOn})
// (:GSTR3B   {filingId, period, taxPaid, itcClaimed})
// (:EWayBill {ewbNumber, validUpto, distance, vehicleNumber})
// (:IRN      {irn, generatedOn, cancelledOn})
// (:FraudCluster {clusterId, type, confidence, totalAmount, detectedOn})
// (:LoanOffer    {offerId, amount, rate, tenor, status})
// (:NexusScore   {score, filingRate, itcReliability, networkRisk, lastUpdated})

// === RELATIONSHIPS (DOCUMENTATION) ===
// (Taxpayer)-[:ISSUED]->(Invoice)
// (Taxpayer)-[:RECEIVED]->(Invoice)
// (Invoice)-[:FILED_IN]->(GSTR1)
// (Invoice)-[:REFLECTED_IN]->(GSTR2B)
// (Invoice)-[:HAS_IRN]->(IRN)
// (Invoice)-[:VALIDATED_BY]->(EWayBill)
// (Taxpayer)-[:FILED]->(GSTR3B)
// (Taxpayer)-[:PART_OF]->(FraudCluster)
// (Taxpayer)-[:ELIGIBLE_FOR]->(LoanOffer)
// (Taxpayer)-[:HAS_SCORE]->(NexusScore)

// === INDEXES ===
CREATE INDEX invoice_date IF NOT EXISTS FOR (i:Invoice) ON (i.date);
CREATE INDEX invoice_status IF NOT EXISTS FOR (i:Invoice) ON (i.status);
CREATE INDEX taxpayer_state IF NOT EXISTS FOR (t:Taxpayer) ON (t.state);
CREATE INDEX taxpayer_risk IF NOT EXISTS FOR (t:Taxpayer) ON (t.riskLevel);
