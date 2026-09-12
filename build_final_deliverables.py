from pathlib import Path
import sys, zipfile
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from src.reports import make_docx, make_pdf, make_xlsx

ROOT = Path(__file__).parent
OUT = ROOT / 'deliverables'
DATA = ROOT / 'test_data' / 'BizLens_Test_Sales_Data.csv'
df = pd.read_csv(DATA, parse_dates=['Date'])

# -------------------------
# Evidence-grounded metrics
# -------------------------
def pct(a, b):
    return (b / a - 1) * 100 if a else None

def period_sum(frame, metric, q):
    return float(frame.loc[frame.Date.dt.quarter == q, metric].sum())

def qrev(region=None, q=None):
    x = df if region is None else df[df.Region == region]
    g = x.groupby(x.Date.dt.quarter).Revenue.sum()
    return float(g.get(q, 0)) if q else g

q3, q4 = qrev(q=3), qrev(q=4)
south = df[df.Region == 'South']
sq3, sq4 = qrev('South', 3), qrev('South', 4)
s3, s4 = south[south.Date.dt.quarter == 3], south[south.Date.dt.quarter == 4]
sla3 = s3.SLA_Achievement_Rate.mean() * 100
sla4 = s4.SLA_Achievement_Rate.mean() * 100
tpo3 = s3.Support_Tickets.sum() / s3.Orders.sum()
tpo4 = s4.Support_Tickets.sum() / s4.Orders.sum()


def change_table(dim, region='South'):
    x = df[df.Region == region] if region else df
    p = x.assign(Period=x.Date.dt.quarter).groupby(['Period', dim]).Revenue.sum().unstack(0).fillna(0)
    rows = []
    for g, r in p.iterrows():
        a, b = float(r.get(3, 0)), float(r.get(4, 0))
        rows.append((g, a, b, b-a, pct(a, b)))
    return sorted(rows, key=lambda z: z[3])

products = change_table('Product')
segments = change_table('Customer_Segment')
channels = change_table('Channel')
regions = change_table('Region', None)

# Canonical business objective for this portfolio case study.
OBJECTIVE = ('Understand why revenue performance weakened in Q4, identify the regions, products and customer segments requiring management attention, and agree actions that can improve retention and delivery performance.')

EVIDENCE = [
    ('E-001', 'Sales dataset', '1,200 rows covering Jan–Dec 2025; fields include revenue, orders, customers, cancellations, SLA achievement and support tickets.', 'Full connected dataset'),
    ('E-002', 'Overall revenue', f'Q3 revenue ₹{q3:,.0f}; Q4 revenue ₹{q4:,.0f}; movement {pct(q3,q4):+.1f}%.', 'All regions, Q3→Q4'),
    ('E-003', 'South revenue', f'Q3 revenue ₹{sq3:,.0f}; Q4 revenue ₹{sq4:,.0f}; movement {pct(sq3,sq4):+.1f}%.', 'South, Q3→Q4'),
    ('E-004', 'South SLA', f'SLA achievement {sla3:.1f}% in Q3 to {sla4:.1f}% in Q4, a {sla4-sla3:+.1f} percentage-point movement.', 'South, Q3→Q4'),
    ('E-005', 'South support pressure', f'Support tickets/order {tpo3:.3f} to {tpo4:.3f}, a {pct(tpo3,tpo4):+.1f}% movement.', 'South, Q3→Q4'),
    ('E-006', 'South product mix', 'Cloud Suite -11.0%; Analytics Pro -10.5%; CRM Platform -4.3%; Security Plus +27.1%.', 'South, Q3→Q4'),
    ('E-007', 'South segment mix', 'SMB -21.6%; Mid-Market -18.5%; Enterprise +38.0%.', 'South, Q3→Q4'),
    ('E-008', 'South channel mix', 'Direct -11.7%; Online -5.7%; Partner +15.9%.', 'South, Q3→Q4'),
    ('E-009', 'Cancellation evidence', 'Only 1 recorded cancellation exists in the connected dataset. This is insufficient for a customer-level causal analysis.', 'Full connected dataset'),
    ('E-010', 'Business context', 'Management evidence identifies South as a priority area and raises delivery/SLA and cancellation concerns. Customer-level linkage is required before causal interpretation.', 'Business documents'),
]

def md_table(rows, headers):
    out = '| ' + ' | '.join(headers) + ' |\n| ' + ' | '.join(['---'] * len(headers)) + ' |\n'
    for r in rows:
        out += '| ' + ' | '.join(str(x).replace('|','/') for x in r) + ' |\n'
    return out

def bullets(items):
    return '\n'.join('- ' + str(x) for x in items)

def evidence_lines(ids=None):
    chosen = EVIDENCE if ids is None else [e for e in EVIDENCE if e[0] in ids]
    return md_table([(i, c, claim, scope) for i,c,claim,scope in chosen], ['ID','Source','Evidence','Period / aggregation'])

# -------------------------
# Narrative deliverables
# -------------------------
exec_sections = [
('Document control', 'Document ID: EBR-001\nVersion: 3.0\nStatus: Final portfolio case study\nPurpose: Management decision support\nBusiness objective: ' + OBJECTIVE),
('1. Executive decision', f'The connected 2025 sales data shows total revenue declined {abs(pct(q3,q4)):.1f}% from Q3 to Q4. South is the management priority and declined {abs(pct(sq3,sq4)):.1f}% in the same comparison. South SLA achievement fell {abs(sla4-sla3):.1f} percentage points and support tickets per order increased {pct(tpo3,tpo4):+.1f}%. The evidence supports a focused investigation and service-recovery effort, but it does not establish that service deterioration caused cancellations.'),
('2. What management should know', bullets([
    f'South is the priority business focus: revenue moved from ₹{sq3:,.0f} to ₹{sq4:,.0f} Q3→Q4.',
    f'Service performance weakened in the same period: SLA moved {sla3:.1f}% → {sla4:.1f}%.',
    f'Support pressure increased: tickets/order moved {tpo3:.3f} → {tpo4:.3f}.',
    'Cloud Suite and Analytics Pro declined in South; Enterprise and Partner growth partially offset pressure.',
    'Only one cancellation is recorded, so customer-level retention conclusions remain unvalidated.'
])),
('3. Concentration and offsets', md_table(
    [('South', f'₹{sq3:,.0f}', f'₹{sq4:,.0f}', f'{pct(sq3,sq4):+.1f}%', 'Priority from business context'),
     ('North', 'Full-dataset regional result', 'See analysis pack', 'Largest percentage decline', 'Not selected as management focus'),
     ('East', 'Full-dataset regional result', 'See analysis pack', 'Positive movement', 'Offset'),
     ('West', 'Full-dataset regional result', 'See analysis pack', 'Near-flat movement', 'Context')],
    ['Area','Q3','Q4','Movement','Interpretation'])),
('4. Evidence register', evidence_lines()),
('5. Decision requested', bullets([
    'Approve a focused Operations review of South delivery and SLA breach detail.',
    'Approve a Customer Success data request for customer/order-level cancellation reasons and affected orders.',
    'Ask Sales and Product to review absolute revenue loss in declining South pockets before any broad pricing/product response.',
    'Assign accountable owners and review dates for the evidence requests.'
])),
('6. Guardrails', bullets([
    'Do not treat South as the largest raw regional decline unless the regional comparison is explicitly being discussed.',
    'Do not call SLA deterioration a confirmed root cause of cancellations.',
    'Do not invent KPI targets, ROI, savings or implementation cost.',
    'Treat the supplied dataset as a controlled portfolio dataset rather than a production source of truth.'
]))
]

brd_sections = [
('Document control', 'Document ID: BRD-001\nVersion: 3.0\nStatus: Final portfolio case study\nOwner: Business Analysis\nApproval status: Pending business validation\nBusiness objective: ' + OBJECTIVE),
('1. Business problem', f'Q4 revenue weakened by {abs(pct(q3,q4)):.1f}% versus Q3. South is highlighted by the supplied business context and shows a {abs(pct(sq3,sq4)):.1f}% revenue decline, lower SLA achievement and higher support pressure. The organisation needs to determine which commercial and operational factors require action and whether service performance is actually linked to customer cancellations.'),
('2. Objectives', bullets([
    'BO-01 Explain the Q3→Q4 revenue movement using period-aligned evidence.',
    'BO-02 Determine where the deterioration is concentrated, with South as the management focus from business context.',
    'BO-03 Assess product, customer-segment and channel contributors.',
    'BO-04 Validate or reject the proposed service-to-cancellation relationship using customer/order-level evidence.',
    'BO-05 Convert validated findings into owned actions, measures, dependencies and review cadence.'
])),
('3. Scope', bullets(['2025 commercial performance; Q3→Q4 comparison; regional, product, segment and channel analysis; South service indicators; cancellation evidence sufficiency; recommendations and BA delivery artefacts.'])) ,
('4. Out of scope', bullets(['Pricing or product redesign decisions without supporting analysis; production system replacement; causal claims without linkage; financial ROI calculations without approved cost/benefit assumptions.'])),
('5. Stakeholders', md_table([
    ('Management / Business Owner','Decision and prioritisation','Outcome, risk, target'),
    ('Operations','Service / delivery owner','SLA, delivery failure, recovery'),
    ('Customer Success','Retention evidence owner','Cancellation reasons and affected accounts'),
    ('Sales','Commercial owner','High-value accounts and revenue pockets'),
    ('Product','Product context owner','Product decline and mix'),
    ('Analytics / BA','Analysis and traceability','Evidence, requirements, decision support')], ['Stakeholder','Primary responsibility','Decision interest'])),
('6. AS-IS business state', bullets([
    'Management has commercial and operational evidence, but the evidence is not yet joined at customer/order level.',
    'South performance is weaker in Q4 and service signals deteriorated in the same period.',
    'Business stakeholders have raised cancellation and delivery concerns.',
    'The current evidence identifies where to investigate but does not prove the individual-level cause of cancellation.'
])),
('7. TO-BE business state', bullets([
    'A period-aligned performance view identifies the priority area and its absolute impact.',
    'Commercial, service and retention evidence can be joined at customer/order level where permitted.',
    'Each finding is labelled observed, hypothesis or evidence gap.',
    'Approved actions have accountable owners, success measures, dependencies and review dates.'
])),
('8. Business requirements', md_table([
    ('BR-01','Provide reliable commercial KPI baselines','High','FR-01','E-001,E-002'),
    ('BR-02','Analyse performance by region, product, segment and channel','High','FR-02','E-003,E-006,E-007,E-008'),
    ('BR-03','Compare aligned periods and quantify movement','High','FR-03','E-002,E-003'),
    ('BR-04','Identify and explain the management priority area without false ranking claims','High','FR-04','E-010'),
    ('BR-05','Assess service indicators alongside commercial movement','High','FR-05','E-004,E-005'),
    ('BR-06','Assess cancellation evidence only when volume/linkage is sufficient','High','FR-06','E-009,E-010'),
    ('BR-07','Separate observed evidence from hypotheses and gaps','High','FR-07','E-009,E-010'),
    ('BR-08','Retain source evidence IDs for material findings','High','FR-08','E-001–E-010'),
    ('BR-09','Identify evidence needed to validate causal explanations','High','FR-09','E-009,E-010'),
    ('BR-10','Provide management-ready analysis outputs','Medium','FR-10','E-001–E-010')], ['ID','Business requirement','Priority','FR link','Evidence'])),
('9. KPI and success measures', md_table([
    ('South revenue', f'₹{sq3:,.0f} → ₹{sq4:,.0f}', f'{pct(sq3,sq4):+.1f}%', 'Target to be approved', 'Monthly'),
    ('South SLA', f'{sla3:.1f}% → {sla4:.1f}%', f'{sla4-sla3:+.1f} pp', 'Target to be approved', 'Weekly'),
    ('Support tickets/order', f'{tpo3:.3f} → {tpo4:.3f}', f'{pct(tpo3,tpo4):+.1f}%', 'Target to be approved', 'Weekly'),
    ('Cancellations', '1 recorded', 'Insufficient baseline', 'Define after richer data', 'Monthly')], ['KPI','Baseline','Observed movement','Target','Cadence'])),
('10. Business rules and constraints', bullets([
    'Use Q3→Q4 as the primary executive comparison in this case study.',
    'Use later periods only as monitoring context, not as a substitute for the primary business comparison.',
    'A relationship between service and cancellation is not causal until customer/order-level linkage is available.',
    'Business targets and financial benefits require explicit approval or source evidence.'
])),
('11. Open questions', bullets([
    'Do customers with SLA breaches cancel at a higher rate?',
    'Which South products contribute the largest absolute revenue loss?',
    'Do support events precede cancellation events?',
    'Is the decline operational, product-specific, channel-specific, segment-specific, or combined?'
])),
('12. Approval', md_table([('Business Owner','','Pending'),('Operations Owner','','Pending'),('Customer Success Owner','','Pending'),('Analytics / BA','','Pending')], ['Role','Name','Status']))
]

prd_sections = [
('Document control','Document ID: PRD-001\nVersion: 3.0\nStatus: Final portfolio case study\nBusiness objective: '+OBJECTIVE),
('1. Product overview','BizLens is an evidence-first Business Analysis workspace. It connects business documents and structured data, quantifies changes, frames investigation hypotheses, identifies evidence gaps, supports recommendations and exports professional BA artefacts.'),
('2. User problem','A dashboard can show that performance changed without explaining where management should focus, what evidence supports the finding, what remains unknown, and what action should follow. BizLens is designed to bridge that gap.'),
('3. Target users', bullets(['Management / business decision makers','Operations and service owners','Customer Success and retention teams','Sales and Product stakeholders','Business Analysts / Analytics teams'])),
('4. Product outcomes', bullets(['A reviewer can understand the business problem and priority area quickly.','Quantitative findings remain period-aligned and traceable.','Hypotheses are not presented as confirmed causes.','Recommendations identify action, owner status, measure, dependency and evidence.','BA deliverables remain coherent across BRD, FRD, UAT and RTM.'])),
('5. Core journey','Understand context → connect evidence → establish baseline → compare aligned periods → identify priority area → decompose drivers → validate hypotheses → identify gaps → decide → deliver → monitor.'),
('6. Product requirements', md_table([
    ('P-01','Evidence ingestion and source register','High','Upload / connect'),
    ('P-02','Aligned-period KPI analysis','High','Data & Insights'),
    ('P-03','Priority-area and contributor analysis','High','Investigation'),
    ('P-04','Operational signal analysis','High','Investigation'),
    ('P-05','Evidence / hypothesis / gap classification','High','Investigation'),
    ('P-06','Decision-ready recommendations','High','Recommendations'),
    ('P-07','BA deliverable generation','Medium','BA Studio / Deliverables'),
    ('P-08','Traceability and UAT support','Medium','Deliverables')], ['ID','Product capability','Priority','Primary area'])),
('7. Non-goals', bullets(['Automated causal claims','Automatic business approval','Replacing operational source systems','Inventing targets, costs, ROI or customer outcomes'])),
('8. Success criteria', bullets(['Executive answer is understandable without a separate analyst explanation.','Material findings have evidence IDs or explicit validation dependencies.','Exported artefacts agree on objective, periods and evidence boundaries.','High-priority requirements map to functional behaviour and UAT.'])),
('9. Release approach', bullets(['Release 1: evidence ingestion and KPI analysis.','Release 2: investigation and recommendation workflow.','Release 3: professional BA artefact generation and traceability.','Production hardening: stakeholder validation, security, performance and governance.']))
]

frd_sections = [
('Document control','Document ID: FRD-001\nVersion: 3.0\nStatus: Final portfolio case study\nLinked BRD: BRD-001'),
('1. Purpose and scope','Define testable system behaviour supporting BizLens from evidence ingestion through analysis, investigation, recommendation and BA deliverable export.'),
('2. Functional requirements', md_table([
    ('FR-01','Display revenue, orders, customers and cancellation KPIs from connected data.','High','Dashboard','Core KPI values reconcile to source aggregation.','BR-01'),
    ('FR-02','Allow decomposition by region, product, customer segment and channel.','High','Analysis','Selected dimension produces consistent grouped results.','BR-02'),
    ('FR-03','Compare aligned periods using absolute and percentage movement.','High','Analysis','Q3→Q4 movement matches source aggregation.','BR-03'),
    ('FR-04','Represent the management focus separately from the largest numerical decline.','High','Investigation','Focus label has a business-context basis.','BR-04'),
    ('FR-05','Show SLA and support-ticket signals beside commercial movement.','High','Investigation','Operational metrics use the same comparison periods.','BR-05'),
    ('FR-06','Flag insufficient cancellation evidence and suppress causal interpretation.','High','Investigation','One-cancellation evidence is explicitly treated as insufficient.','BR-06'),
    ('FR-07','Classify findings as observed evidence, hypothesis or evidence gap.','High','Investigation','Every material conclusion has a classification.','BR-07'),
    ('FR-08','Carry evidence IDs into findings and exported recommendations.','High','Deliverables','Evidence IDs remain visible in exported output.','BR-08'),
    ('FR-09','Generate recommendations containing action, owner status, measure, dependency and evidence.','High','Recommendations','Required recommendation fields are present.','BR-09'),
    ('FR-10','Export coherent DOCX, PDF and XLSX BA artefacts.','Medium','Deliverables','Files open, contain expected sections and remain internally consistent.','BR-10')], ['ID','Functional behaviour','Priority','Area','Acceptance outcome','BR link'])),
('3. Data requirements', md_table([
    ('Revenue','Sales dataset','Numeric; non-null','Sum by period/dimension','Commercial KPI','E-002,E-003'),
    ('Orders','Sales dataset','Numeric; non-negative','Sum by period/dimension','Volume analysis','E-001'),
    ('SLA_Achievement_Rate','Sales dataset','Expected 0–1','Mean / agreed weighting','Service signal','E-004'),
    ('Support_Tickets','Sales dataset','Numeric; non-negative','Tickets / orders','Service pressure','E-005'),
    ('Cancellations','Sales dataset','Numeric; non-negative','Count/rate only when sufficient','Retention analysis','E-009'),
    ('Region/Product/Segment/Channel','Sales dataset','Categorical','Group-by','Driver analysis','E-003,E-006,E-007,E-008')], ['Element','Source','Validation','Transformation','Use','Evidence'])),
('4. Exception and validation rules', bullets(['Missing core fields: block affected analysis and state the missing evidence.','Period mismatch: do not compare unlike periods without an explicit label.','Insufficient cancellation volume: show the evidence gap and do not infer causality.','Conflicting source statements: retain both, identify the conflict and require validation.','Missing business targets: show actual baseline and mark target as pending approval.'])),
('5. Non-functional requirements', bullets(['NFR-01 Usable by non-technical business reviewers.','NFR-02 Material claims remain traceable to source evidence.','NFR-03 Missing evidence is visible rather than silently fabricated.','NFR-04 Exports remain readable and internally consistent.','NFR-05 Analysis should fail safely when required data is malformed or incomplete.'])),
('6. Acceptance and traceability','No high-priority functional requirement is considered complete until its BR, user story, UAT scenario and evidence boundary are mapped. UAT status remains Not Run until an actual execution is performed.')
]

process_sections = [
('Document control','Document ID: PRC-001\nVersion: 3.0\nStatus: Final portfolio case study\nBusiness objective: '+OBJECTIVE),
('1. Process purpose','Define the repeatable BA process for moving from a business concern to an evidence-backed management decision.'),
('2. AS-IS evidence flow','Business concern\n  ↓\nBusiness documents + dataset collected\n  ↓\nPerformance reviewed\n  ↓\nPatterns identified\n  ↓\nDriver discussion\n  ↓\nActions proposed\n  ↓\nEvidence gaps may remain'),
('3. AS-IS observations', bullets(['Commercial and operational evidence exists but is not fully joined at customer/order level.','The business focus comes from context and cannot be inferred solely from the largest percentage decline.','Cancellation concerns are reported in business evidence but the connected dataset has only one cancellation.','Ownership and target setting still require business confirmation.'])),
('4. TO-BE evidence-led flow','Business objective\n  ↓\nEvidence register\n  ↓\nBaseline + aligned-period comparison\n  ↓\nPriority area selection\n  ↓\nCommercial + operational decomposition\n  ↓\nHypothesis validation\n  ↓\nEvidence-gap decision\n  ↓\nRecommendation + owner + measure\n  ↓\nManagement decision\n  ↓\nMonitor outcome'),
('5. Process controls', bullets(['Use a primary comparison period for executive decisions.','Label aggregation scope for every material KPI.','Separate observed evidence from hypotheses.','Require a validation plan for causal hypotheses.','Do not assign confirmed owners where the evidence does not name them.'])),
('6. Handoffs', md_table([
    ('Context → Analysis','Objective, source register, business concern','BA / Analytics','Baseline accepted'),
    ('Analysis → Investigation','Priority area, contributor results, evidence IDs','BA / Operations','Hypotheses classified'),
    ('Investigation → Recommendation','Validated findings, evidence gaps, decision need','BA / Business Owner','Action selected'),
    ('Recommendation → Delivery','Owner, KPI, dependency, acceptance criteria','Delivery owner','Approved requirement'),
    ('Delivery → Monitoring','Baseline, target, cadence, evidence source','Process owner','Review cycle active')], ['Handoff','Inputs','Receiving role','Exit criterion'])),
('7. Process measures', md_table([('South revenue','Q3→Q4 baseline and next comparable period','Monthly'),('South SLA','Period-aligned SLA achievement','Weekly'),('Support tickets/order','Operational pressure indicator','Weekly'),('Evidence closure','Open evidence questions resolved','Weekly')], ['Measure','Definition','Cadence']))
]

rca_sections = [
('Document control','Document ID: RCA-001\nVersion: 3.0\nStatus: Final portfolio case study\nMethod: Period-aligned comparison + segmentation + operational signal review + evidence classification'),
('1. Problem statement', f'South revenue declined {abs(pct(sq3,sq4)):.1f}% from Q3 to Q4. SLA achievement fell {abs(sla4-sla3):.1f} percentage points and support tickets/order increased {pct(tpo3,tpo4):+.1f}%. The question is whether service deterioration is a contributor to the commercial decline and retention concern.'),
('2. Evidence register', evidence_lines()),
('3. Hypothesis assessment', md_table([
    ('H-01','South service deterioration contributed to the revenue decline.','Partially supported','E-003,E-004,E-005,E-010','Revenue and service moved adversely in the same period; no causal linkage.'),
    ('H-02','Cloud Suite decline is a material commercial contributor in South.','Supported as contribution signal','E-006','Revenue declined Q3→Q4; absolute impact should be reviewed before intervention.'),
    ('H-03','SMB/Mid-Market weakness contributes to South decline.','Supported as contribution signal','E-007','Both segments declined; Enterprise growth offsets part of the pressure.'),
    ('H-04','Direct/Online weakness contributes to South decline.','Supported as contribution signal','E-008','Both channels declined; Partner growth offsets part of the pressure.'),
    ('H-05','SLA breaches are causing cancellations.','Unvalidated','E-009,E-010','Only one cancellation is available and no customer/order linkage is present.')], ['ID','Hypothesis','Status','Evidence','Interpretation'])),
('4. Root-cause conclusion','No root cause is confirmed. The strongest current operational hypothesis is service-performance deterioration because it is period-aligned with the South decline and supported by business context. This remains a hypothesis, not a causal finding.'),
('5. Validation plan', bullets(['Obtain customer/order-level cancellation records and reasons.','Obtain SLA breach events and affected orders.','Join service and cancellation records on a common customer/order key where permitted.','Compare cancellation rates for breached versus unaffected orders/customers.','Check whether service events precede cancellation events.','Segment results by product, customer segment, region and channel.'])),
('6. Investigation outcome', 'The current analysis establishes where to investigate, what evidence supports the hypothesis and what evidence is missing. The appropriate next action is targeted validation rather than a blanket commercial intervention.')
]

# Data and analysis with explicit aggregation metadata.
regional_full = []
for region in sorted([x for x in df.Region.dropna().unique()]):
    r = df[df.Region == region]
    regional_full.append((region, f'₹{r.Revenue.sum():,.0f}', len(r), 'Full connected dataset, Jan–Dec 2025'))

data_sections = [
('Document control','Document ID: DBA-001\nVersion: 3.0\nStatus: Final portfolio case study'),
('1. Business question', OBJECTIVE),
('2. Data used','BizLens_Test_Sales_Data.csv; 1,200 rows, 12 columns, Jan–Dec 2025. The primary executive comparison is Q3→Q4. Full-dataset totals are labelled separately to avoid mixing aggregation scopes.'),
('3. Method', bullets(['Primary period: Q3→Q4 2025.','Secondary monitoring context may use later periods, but does not replace the primary comparison.','Revenue is analysed by region, product, customer segment and channel.','South SLA and support tickets/order are aligned to the same Q3→Q4 period.','Cancellation evidence is assessed for sufficiency before interpretation.'])),
('4. Executive findings', bullets([f'Total revenue changed {pct(q3,q4):+.1f}% from Q3 to Q4.', f'South revenue changed {pct(sq3,sq4):+.1f}% from Q3 to Q4.', f'South SLA changed {sla4-sla3:+.1f} percentage points.', f'South support tickets/order changed {pct(tpo3,tpo4):+.1f}%.', 'Cloud Suite and Analytics Pro declined in South; Enterprise and Partner were offsets.', 'Only one cancellation is recorded, so service-to-cancellation causality cannot be established.'])),
('5. Full-dataset regional context', md_table(regional_full, ['Region','Revenue total','Rows','Aggregation scope'])),
('6. South contributor detail', md_table([(g,f'₹{a:,.0f}',f'₹{b:,.0f}',f'₹{d:,.0f}',f'{c:+.1f}%') for g,a,b,d,c in products], ['Product','Q3 revenue','Q4 revenue','Absolute change','% change']) + '\n' + md_table([(g,f'₹{a:,.0f}',f'₹{b:,.0f}',f'₹{d:,.0f}',f'{c:+.1f}%') for g,a,b,d,c in segments], ['Segment','Q3 revenue','Q4 revenue','Absolute change','% change']) + '\n' + md_table([(g,f'₹{a:,.0f}',f'₹{b:,.0f}',f'₹{d:,.0f}',f'{c:+.1f}%') for g,a,b,d,c in channels], ['Channel','Q3 revenue','Q4 revenue','Absolute change','% change'])),
('7. Evidence register', evidence_lines()),
('8. Interpretation and limitations', bullets(['South is a management focus based on business context, not simply because it has the largest raw decline.','Product/segment/channel movements are contribution signals and should be ranked by absolute revenue impact before intervention.','Service deterioration is a correlated operational signal, not a confirmed root cause.','Cancellation analysis requires richer customer/order-level evidence.','Targets, costs and ROI are not supplied and are therefore not invented.']))
]

kpi_sections = [
('Document control','Document ID: KPI-001\nVersion: 3.0\nStatus: Final portfolio case study'),
('1. Executive KPI view', f'The primary KPI story is Q3→Q4. Total revenue declined {abs(pct(q3,q4)):.1f}%, while South declined {abs(pct(sq3,sq4)):.1f}% and South service indicators worsened.'),
('2. KPI scorecard', md_table([
    ('Total revenue', f'₹{q4:,.0f}', f'{pct(q3,q4):+.1f}%', 'Target not approved','E-002'),
    ('South revenue', f'₹{sq4:,.0f}', f'{pct(sq3,sq4):+.1f}%', 'Target not approved','E-003'),
    ('South SLA', f'{sla4:.1f}%', f'{sla4-sla3:+.1f} pp', 'Target not approved','E-004'),
    ('South support tickets/order', f'{tpo4:.3f}', f'{pct(tpo3,tpo4):+.1f}%', 'Target not approved','E-005'),
    ('Cancellations', '1 recorded', 'Insufficient baseline', 'Richer data required','E-009')], ['KPI','Q4 value','Q3→Q4 movement','Target/status','Evidence'])),
('3. Driver scorecard', md_table([(g,f'{d:,.0f}',f'{c:+.1f}%') for g,a,b,d,c in products], ['South product','Absolute Q3→Q4 change','% change']) + '\n' + md_table([(g,f'{d:,.0f}',f'{c:+.1f}%') for g,a,b,d,c in segments], ['South segment','Absolute Q3→Q4 change','% change']) + '\n' + md_table([(g,f'{d:,.0f}',f'{c:+.1f}%') for g,a,b,d,c in channels], ['South channel','Absolute Q3→Q4 change','% change'])),
('4. Monitoring plan', md_table([('Weekly','South SLA','Operations','Threshold to be approved'),('Weekly','Support tickets/order','Operations + CS','Threshold to be approved'),('Monthly','South revenue and mix','Business Owner / Sales','Target to be approved'),('Monthly','Cancellation rate','Customer Success','Only after richer data')], ['Cadence','Metric','Owner','Decision rule']))
]

gap_sections = [
('Document control','Document ID: GAP-001\nVersion: 3.0\nStatus: Final portfolio case study'),
('1. Gap analysis purpose','Compare the current evidence and working process with the evidence quality required for a defensible management decision.'),
('2. Gap matrix', md_table([
    ('G-01','Revenue/service data exist but are not customer-linked','Customer/order-level service + retention view','Joinable SLA, support and cancellation evidence','Analytics + Customer Success','High','Open'),
    ('G-02','South service deterioration is visible but event detail is absent','Validated operational failure point','SLA breach/delivery event detail','Operations','High','Open'),
    ('G-03','Commercial dimensions can be segmented','Absolute-impact explanation for declining pockets','Product/segment/channel context','Sales + Product','Medium','Open'),
    ('G-04','KPI targets are not supplied','Approved targets and review thresholds','Business approval','Business Owner','Medium','Open'),
    ('G-05','Recommendations can be produced','Approved action ownership and governance','Decision log / owner confirmation','Business Owner','Medium','Open')], ['ID','Current state','Desired state','Closure evidence','Owner','Priority','Status'])),
('3. Closure sequence', bullets(['Close customer-level retention evidence gap.','Diagnose South SLA/delivery failure point.','Quantify absolute-impact commercial pockets.','Approve KPI targets and governance.','Implement selected action and monitor outcome.'])),
('4. Gap closure acceptance', bullets(['Source is identified.','Owner is confirmed.','Closure evidence is observable.','Result is reviewed by the business owner.']))
]

business_case_sections = [
('Document control','Document ID: BC-001\nVersion: 3.0\nStatus: Final portfolio case study'),
('1. Decision summary','The recommended course is a focused investigation and service-recovery programme rather than an immediate broad commercial intervention. This preserves optionality while the evidence gap is closed.'),
('2. Business problem', f'South revenue declined {abs(pct(sq3,sq4)):.1f}% Q3→Q4 while SLA performance weakened and support pressure increased. Business context also raises cancellation concerns, but the connected dataset has only one cancellation.'),
('3. Options', md_table([
    ('A','Immediate broad pricing/product intervention','Fast','High','Not recommended','Causal/commercial evidence is incomplete'),
    ('B','Focused investigation + service recovery','Moderate','Lower','Recommended','Directly addresses evidence-backed priority'),
    ('C','Wait without targeted action','Slow','High','Fallback only','Delays learning and recovery')], ['Option','Approach','Speed','Decision risk','Assessment','Reason'])),
('4. Expected benefits', bullets(['Faster identification of the operational failure point.','Better targeting of commercial intervention.','Reduced risk of acting on an unsupported causal assumption.','Clearer ownership and KPI governance.'])),
('5. Costs and assumptions','Expected effort is primarily analyst, Operations, Customer Success, Sales and Product time plus access to the required evidence. Monetary cost, savings and ROI are intentionally not estimated because the source evidence does not provide approved assumptions.'),
('6. Decision gates', md_table([('Gate 1','Customer/order-level retention evidence obtained','Business Owner','Proceed / hold'),('Gate 2','South operational cause validated','Operations + Business Owner','Recover / investigate further'),('Gate 3','Highest-impact commercial pocket quantified','Sales + Product','Targeted intervention / monitor'),('Gate 4','Target and owner approved','Business Owner','Implement / defer')], ['Gate','Evidence required','Decision owner','Decision']))
]

narrative = {
    '01_Executive_Brief': exec_sections,
    '02_BRD': brd_sections,
    '03_PRD': prd_sections,
    '04_FRD': frd_sections,
    '05_Process_Specification': process_sections,
    '06_RCA': rca_sections,
    '07_Data_Business_Analysis': data_sections,
    '08_KPI_Performance_Review': kpi_sections,
    '09_Gap_Analysis': gap_sections,
    '10_Business_Case': business_case_sections,
}
for name, sections in narrative.items():
    make_docx(OUT / f'{name}.docx', name.replace('_',' '), sections)
    make_pdf(OUT / f'{name}.pdf', name.replace('_',' '), sections)

# -------------------------
# Structured BA artefacts
# -------------------------
rtm = pd.DataFrame([
    ('BR-01','Core KPI baseline','FR-01','US-001','UAT-001','E-001,E-002','Core KPI totals reconcile to source aggregation','High','Open'),
    ('BR-02','Dimension analysis','FR-02','US-002','UAT-002','E-003,E-006,E-007,E-008','Region/product/segment/channel results reconcile to source grouping','High','Open'),
    ('BR-03','Aligned-period comparison','FR-03','US-003','UAT-003','E-002,E-003','Q3→Q4 absolute and percentage movement matches source aggregation','High','Open'),
    ('BR-04','Business focus identification','FR-04','US-004','UAT-004','E-010','Focus is labelled as business context, not falsely as largest decline','High','Open'),
    ('BR-05','Service signal analysis','FR-05','US-005','UAT-005','E-004,E-005','SLA and tickets/order use the same comparison period','High','Open'),
    ('BR-06','Cancellation evidence sufficiency','FR-06','US-006','UAT-006','E-009,E-010','Insufficient cancellation volume blocks causal interpretation','High','Open'),
    ('BR-07','Evidence classification','FR-07','US-007','UAT-007','E-009,E-010','Material findings are labelled evidence, hypothesis or gap','High','Open'),
    ('BR-08','Evidence traceability','FR-08','US-008','UAT-008','E-001–E-010','Export retains evidence IDs','High','Open'),
    ('BR-09','Validation-aware recommendations','FR-09','US-009','UAT-009','E-009,E-010','Recommendation includes action, owner status, measure and dependency','High','Open'),
    ('BR-10','Management-ready exports','FR-10','US-010','UAT-010','E-001–E-010','Exports are readable and internally consistent','Medium','Open'),
], columns=['BR ID','Business requirement','FR ID','User Story','UAT','Evidence','Acceptance criterion','Priority','Status'])

roadmap = pd.DataFrame([
    ('1','Evidence closure','Obtain cancellation reasons, affected orders and SLA breach events','Customer Success / Operations / Analytics','High','Open','Joinable customer/order evidence'),
    ('2','South service diagnosis','Identify delivery/SLA failure points and timing','Operations','High','Open','Validated operational explanation'),
    ('3','Commercial decomposition','Rank absolute revenue loss by product, segment and channel','Analytics / BA + Sales + Product','High','Open','Priority pocket selected'),
    ('4','Decision and approval','Approve intervention, owner, KPI target and cadence','Business Owner','High','Open','Decision recorded'),
    ('5','Implementation','Execute approved action and capture outcome','Accountable process owner','Medium','Future','Action implemented'),
    ('6','Monitoring','Review revenue, SLA, tickets/order and cancellation measures','Process owner','Medium','Future','Target tracked and reviewed')],
    columns=['Phase','Workstream','Deliverable','Owner','Priority','Status','Exit criterion'])

stories = pd.DataFrame([
    ('US-001','KPI visibility','As a manager, I want core commercial KPIs so that I can understand the scale of the Q4 change.','High','BR-01','E-001,E-002'),
    ('US-002','Segmentation','As an analyst, I want region, product, segment and channel views so that I can locate performance changes.','High','BR-02','E-003,E-006,E-007,E-008'),
    ('US-003','Period comparison','As a manager, I want aligned-period comparisons so that I can assess real movement.','High','BR-03','E-002,E-003'),
    ('US-004','Focus framing','As a decision maker, I want the management focus separated from raw ranking so that context is not confused with magnitude.','High','BR-04','E-010'),
    ('US-005','Service signals','As an Operations owner, I want SLA and support pressure beside revenue so that service deterioration is visible.','High','BR-05','E-004,E-005'),
    ('US-006','Retention evidence','As Customer Success, I want cancellation analysis to stop when evidence is insufficient so that unsupported causal claims are avoided.','High','BR-06','E-009,E-010'),
    ('US-007','Evidence boundary','As a decision maker, I want findings classified so that hypotheses are not mistaken for facts.','High','BR-07','E-009,E-010'),
    ('US-008','Traceability','As a BA, I want evidence IDs retained so that findings can be audited.','High','BR-08','E-001–E-010'),
    ('US-009','Decision support','As a manager, I want recommendations with validation dependencies so that actions are appropriately gated.','High','BR-09','E-009,E-010'),
    ('US-010','Executive output','As a manager, I want readable exports so that findings can be reviewed and shared.','Medium','BR-10','E-001–E-010')],
    columns=['Story ID','Epic','User story','Priority','BR ID','Evidence'])

usecases = pd.DataFrame([
    ('UC-001','Review performance','Management','New review cycle','Q3→Q4 performance reviewed','Source aggregation mismatch'),
    ('UC-002','Investigate South','BA / Operations','South identified as priority','Service and commercial contributors assessed','Operational detail unavailable'),
    ('UC-003','Validate retention hypothesis','Customer Success / Analytics','Cancellation concern raised','Hypothesis accepted, rejected or remains unvalidated','Insufficient cancellation volume'),
    ('UC-004','Select intervention','Business Owner','Investigation complete','Owned action selected','No approved target/owner'),
    ('UC-005','Monitor outcome','Process owner','Action implemented','KPI trend reviewed against approved target','Data refresh or target unavailable')],
    columns=['UC ID','Use case','Primary actor','Trigger','Main outcome','Exception'])

uat = pd.DataFrame([
    ('UAT-001','BR-01','Load dataset and verify KPI totals','Core KPI totals match source aggregation','High','Not Run','E-001,E-002'),
    ('UAT-002','BR-02','Change analysis dimension','Grouping updates correctly by selected dimension','High','Not Run','E-003,E-006,E-007,E-008'),
    ('UAT-003','BR-03','Compare Q3 and Q4','Absolute and percentage movement are correct','High','Not Run','E-002,E-003'),
    ('UAT-004','BR-04','Review focus label','South is presented as business focus, not largest raw decline','High','Not Run','E-010'),
    ('UAT-005','BR-05','Review service signals','SLA and tickets/order align to Q3→Q4','High','Not Run','E-004,E-005'),
    ('UAT-006','BR-06','Review cancellation evidence','One cancellation is flagged as insufficient and causal claim is blocked','High','Not Run','E-009'),
    ('UAT-007','BR-07','Inspect classification','Material findings show evidence/hypothesis/gap classification','High','Not Run','E-009,E-010'),
    ('UAT-008','BR-08','Export finding','Evidence IDs are retained in export','High','Not Run','E-001–E-010'),
    ('UAT-009','BR-09','Inspect recommendation','Action, owner status, measure, dependency and evidence are present','High','Not Run','E-009,E-010'),
    ('UAT-010','BR-10','Open exported BA pack','DOCX/PDF/XLSX files open and are coherent','Medium','Not Run','E-001–E-010')],
    columns=['UAT ID','BR ID','Scenario','Expected result','Priority','Status','Evidence'])

stake = pd.DataFrame([
    ('Management / Business Owner','Decision maker','High','High','Outcome, risk, target','Executive review + decision log','Pending confirmation'),
    ('Operations','Service/process owner','High','High','SLA, delivery failure','Investigation workshop + weekly review','Pending confirmation'),
    ('Customer Success','Retention evidence owner','High','High','Cancellation reasons','Data request + account review','Pending confirmation'),
    ('Sales','Commercial owner','Medium','High','High-value accounts','Commercial pocket review','Pending confirmation'),
    ('Product','Product context owner','Medium','Medium','Product decline and mix','Targeted product review','Pending confirmation'),
    ('Analytics / BA','Analysis owner','High','Medium','Evidence and traceability','Analysis + evidence register','Working role')],
    columns=['Stakeholder','Role','Interest','Influence','Key concerns','Engagement','Confirmation status'])

raci = pd.DataFrame([
    ('Evidence request','Analytics / BA','Business Owner','Operations; Customer Success','Sales','Draft until owners confirm'),
    ('South SLA diagnosis','Operations','Business Owner','Analytics / BA','Management','Draft until owners confirm'),
    ('Retention validation','Customer Success','Business Owner','Analytics / BA; Operations','Management','Draft until owners confirm'),
    ('Commercial pocket review','Sales + Product','Business Owner','Analytics / BA','Operations','Draft until owners confirm'),
    ('Recommendation approval','Analytics / BA','Business Owner','Relevant owners','Management','Draft until owners confirm'),
    ('Monitoring','Process owner','Business Owner','Analytics / BA','Management','Draft until owners confirm')],
    columns=['Task','Responsible','Accountable','Consulted','Informed','Status'])

actions = pd.DataFrame([
    ('ACT-001','Obtain customer-level cancellation reasons and affected orders','Customer Success','High','Close retention evidence gap','Open','E-009,E-010','Customer/order-level evidence received'),
    ('ACT-002','Obtain South delivery/SLA breach detail','Operations','High','Validate service hypothesis','Open','E-004,E-005,E-010','Operational failure point identified'),
    ('ACT-003','Quantify absolute revenue loss by South product/segment/channel','Analytics / BA','High','Commercial prioritisation','Open','E-006,E-007,E-008','Priority pocket selected'),
    ('ACT-004','Review high-value South accounts after richer evidence is available','Sales','Medium','Targeted retention response','Open','E-007,E-010','Account list validated'),
    ('ACT-005','Approve KPI targets and review cadence','Business Owner','Medium','Governance','Open','E-002–E-005','Targets approved')],
    columns=['Action ID','Action','Suggested owner','Priority','Purpose','Status','Evidence','Completion criterion'])

for filename, data, sheet in [
    ('11_RTM.xlsx', rtm, 'RTM'),
    ('12_Implementation_Roadmap.xlsx', roadmap, 'Roadmap'),
    ('13_User_Stories.xlsx', stories, 'Stories'),
    ('14_Use_Cases.xlsx', usecases, 'Use Cases'),
    ('15_UAT_Scenarios.xlsx', uat, 'UAT'),
    ('16_Stakeholder_Analysis.xlsx', stake, 'Stakeholders'),
    ('17_RACI_Matrix.xlsx', raci, 'RACI'),
    ('18_Action_Plan.xlsx', actions, 'Actions')]:
    make_xlsx(OUT / filename, {sheet: data})

# Pack documentation
pack_readme = '''# BizLens Final BA Deliverables Pack

## Case objective
Understand why revenue performance weakened in Q4, identify the regions, products and customer segments requiring management attention, and agree actions that can improve retention and delivery performance.

## Evidence boundary
- Primary executive comparison: Q3→Q4 2025.
- South is the management priority because it is explicitly highlighted in the supplied business context and has aligned operational deterioration.
- South revenue declined 2.1% Q3→Q4; South SLA achievement fell and support tickets/order increased.
- Only 1 cancellation is recorded in the connected dataset, so a service-to-cancellation causal claim is not supportable.
- Full-dataset totals are explicitly labelled where shown, so aggregation scope is not confused with Q3→Q4 movement.
- Targets, ROI and monetary benefits are not invented where source evidence is absent.

## Deliverable map
1. Executive Brief — management decision and guardrails
2. BRD — business problem, scope, stakeholders, requirements and approval
3. PRD — product problem, users, capabilities and success criteria
4. FRD — testable functional behaviour, data rules and NFRs
5. Process Specification — AS-IS / TO-BE evidence-led BA flow and handoffs
6. RCA — hypothesis assessment, evidence and validation plan
7. Data & Business Analysis — methods, aggregation scope and contributor detail
8. KPI Performance Review — KPI baseline, movement and monitoring
9. Gap Analysis — current vs desired evidence/process state
10. Business Case — options, recommendation and decision gates
11. RTM — BRD → FRD → User Story → UAT → Evidence traceability
12. Implementation Roadmap — phased delivery and exit criteria
13. User Stories — user-centric backlog linked to requirements
14. Use Cases — triggers, actors, outcomes and exceptions
15. UAT Scenarios — executable acceptance scenarios, not claimed as passed
16. Stakeholder Analysis — influence, interest and confirmation status
17. RACI Matrix — draft governance assignments pending owner confirmation
18. Action Plan — evidence-backed actions with completion criteria

## Portfolio note
This is a controlled portfolio case study. Stakeholder names, approved targets, production data ownership and final implementation decisions remain business-validation items.
'''
(OUT / 'README.md').write_text(pack_readme, encoding='utf-8')
(OUT / 'INDEX.md').write_text('# BizLens Final Deliverables Index\n\nThe pack contains 18 coordinated BA artefacts. Start with `01_Executive_Brief`, then review `02_BRD`, `04_FRD`, `06_RCA`, `07_Data_Business_Analysis` and `11_RTM`.\n', encoding='utf-8')

# Rebuild nested pack.
pack = OUT / 'BizLens_Deliverables_Pack.zip'
if pack.exists(): pack.unlink()
with zipfile.ZipFile(pack, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        if p.name != pack.name:
            z.write(p, p.name)

# Keep the app release metadata aligned.
(ROOT / 'VERSION.txt').write_text('BizLens 4.1 FINAL CLEAN BA WORKSPACE\nFinal coordinated deliverables pack: 18 artefacts\n', encoding='utf-8')
print('BUILT FINAL DELIVERABLES:', len(narrative), 'document sets +', 8, 'structured artefacts')
