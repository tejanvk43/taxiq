// Minimal demo seed (100% optional — backend can run in mock mode without seed)
// Run after schema:
// :source /var/lib/neo4j/import/constraints.cypher
// :source /var/lib/neo4j/import/schema.cypher
// :source /var/lib/neo4j/import/seed_data.cypher

MERGE (a:Taxpayer {gstin:"29AAACN0001A1Z5"})
SET a.name="Nexus Demo Manufacturing", a.state="KA", a.type="REGULAR",
    a.registrationDate=date("2020-04-01"), a.nexusScore=86, a.riskLevel="LOW", a.complianceScore=90;

MERGE (b:Taxpayer {gstin:"19AABCG1234Q1Z2"})
SET b.name="GoldStar Traders", b.state="WB", b.type="REGULAR",
    b.registrationDate=date("2023-11-12"), b.nexusScore=18, b.riskLevel="HIGH", b.complianceScore=22;

MERGE (c:Taxpayer {gstin:"27AAACF9999K1Z9"})
SET c.name="Falcon Components", c.state="MH", c.type="REGULAR",
    c.registrationDate=date("2022-06-05"), c.nexusScore=52, c.riskLevel="MEDIUM", c.complianceScore=58;

MERGE (d:Taxpayer {gstin:"07AABCS7777H1Z1"})
SET d.name="Shadow Supplies", d.state="DL", d.type="REGULAR",
    d.registrationDate=date("2024-01-10"), d.nexusScore=33, d.riskLevel="HIGH", d.complianceScore=35;

WITH a,b,c,d
MERGE (inv1:Invoice {invoiceId:"INV-2024-001"})
SET inv1.irn="IRN-DEMO-001", inv1.amount=8420000, inv1.taxAmount=1515600, inv1.igst=0, inv1.cgst=757800, inv1.sgst=757800,
    inv1.date="2024-01-18", inv1.status="MISMATCH";

MERGE (g1:GSTR1 {filingId:"GSTR1-19-2024-01"})
SET g1.period="2024-01", g1.filedOn="2024-02-18", g1.status="FILED_LATE";

MERGE (g2b:GSTR2B {period:"2024-01"})
SET g2b.generatedOn="2024-02-12";

MERGE (g3b:GSTR3B {filingId:"GSTR3B-29-2024-01"})
SET g3b.period="2024-01", g3b.taxPaid=1200000, g3b.itcClaimed=990000;

MERGE (ewb:EWayBill {ewbNumber:"EWB-DEMO-9001"})
SET ewb.validUpto="2024-01-25", ewb.distance=320, ewb.vehicleNumber="KA01AB1234";

MERGE (b)-[:ISSUED {amount:8420000, taxAmount:1515600}]->(inv1)
MERGE (a)-[:RECEIVED]->(inv1)
MERGE (inv1)-[:FILED_IN]->(g1)
MERGE (inv1)-[:REFLECTED_IN]->(g2b)
MERGE (inv1)-[:VALIDATED_BY]->(ewb)
MERGE (a)-[:FILED]->(g3b);

// Seed a simple fraud cluster
MERGE (fc:FraudCluster {clusterId:"RING-001"})
SET fc.type="CIRCULAR_ITC", fc.confidence=0.84, fc.totalAmount=8420000, fc.detectedOn="2024-02-12";

MERGE (b)-[:PART_OF]->(fc)
MERGE (c)-[:PART_OF]->(fc)
MERGE (d)-[:PART_OF]->(fc);

// Create a circular ring via invoices (conceptual)
MERGE (inv2:Invoice {invoiceId:"INV-2024-002"})
SET inv2.irn="IRN-DEMO-002", inv2.amount=410000, inv2.taxAmount=73800, inv2.date="2024-01-09", inv2.status="FRAUD";
MERGE (inv3:Invoice {invoiceId:"INV-2024-003"})
SET inv3.irn="IRN-DEMO-003", inv3.amount=420000, inv3.taxAmount=75600, inv3.date="2024-01-11", inv3.status="FRAUD";
MERGE (inv4:Invoice {invoiceId:"INV-2024-004"})
SET inv4.irn="IRN-DEMO-004", inv4.amount=430000, inv4.taxAmount=77400, inv4.date="2024-01-13", inv4.status="FRAUD";

MERGE (b)-[:ISSUED {amount:410000, taxAmount:73800}]->(inv2)
MERGE (inv2)<-[:RECEIVED]-(c)
MERGE (c)-[:ISSUED {amount:420000, taxAmount:75600}]->(inv3)
MERGE (inv3)<-[:RECEIVED]-(d)
MERGE (d)-[:ISSUED {amount:430000, taxAmount:77400}]->(inv4)
MERGE (inv4)<-[:RECEIVED]-(b);
