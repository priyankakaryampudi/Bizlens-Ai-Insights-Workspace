"""Manual integration check for the newly-built pieces:
evidence register, extended recommendations, and the 5 new deliverable types.
Run directly with `python tests/test_new_features.py` - no streamlit runtime needed.
"""
import sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from src.ingest import read_tabular, extract_text, classify
from src.doc_intel import build_context
from src.evidence import build_evidence_register, evidence_by_id, source_line
from src.intelligence import decision_recommendations, investigation_brief
from src.studio import studio_sections
from src.reports import make_docx, make_pdf

DATA_DIR = ROOT / 'data'
objective = 'Understand what is driving regional revenue variation.'

artifacts = []
df = None
for f in DATA_DIR.iterdir():
    data = f.read_bytes()
    kind = classify(f.name)
    item = {'name': f.name, 'kind': kind, 'text': None}
    if kind == 'dataset':
        df = read_tabular(f.name, data)
    else:
        item['text'] = extract_text(f.name, data)
    artifacts.append(item)

assert df is not None, 'demo dataset failed to load'
sig, flags, _ = build_context(artifacts)
print('doc signal categories:', {k: len(v) for k, v in sig.items()})

register = build_evidence_register(artifacts, df, sig, objective)
assert register, 'evidence register is empty'
for item in register[:5]:
    print(item['evidence_id'], item['classification'], '-', item['claim'][:70])
assert evidence_by_id(register, register[0]['evidence_id']) is not None
print(source_line(register[0]))


# Business-facing analysis should not expose statistical coefficients as the
# primary explanation, and the supplied demo brief should align to the
# documented South-region focus.
assert all('r=' not in str(x) for x in investigation_brief(df, sig, objective).get('evidence', []))
assert all('r=' not in str(x) for x in investigation_brief(df, sig, objective).get('drivers', []))

recs = decision_recommendations(df, sig, [], objective, register)
assert recs, 'no recommendations produced'
types = {r['type'] for r in recs}
print('recommendation types:', types)
for r in recs:
    assert r['id'].startswith('REC-')
    assert 'dependencies' in r and 'risks' in r and 'decision_required' in r
print('recommendation field check OK')

# Final BA-quality assertions against the full test evidence: the business
# focus must not be mislabeled as the largest decline, and the executive answer
# must connect KPI -> focus -> operational signal.
TEST_DIR = ROOT / 'test_data'
test_df = read_tabular('BizLens_Test_Sales_Data.csv', (TEST_DIR/'BizLens_Test_Sales_Data.csv').read_bytes())
test_arts = []
for f in TEST_DIR.iterdir():
    kind = classify(f.name)
    if kind == 'dataset':
        continue
    test_arts.append({'name': f.name, 'kind': kind, 'text': extract_text(f.name, f.read_bytes())})
test_sig, _, _ = build_context(test_arts)
test_reg = build_evidence_register(test_arts, test_df, test_sig, '')
test_brief = investigation_brief(test_df, test_sig, '')
test_recs = decision_recommendations(test_df, test_sig, [], '', test_reg)
assert test_brief.get('lead_group') == 'South', 'document-supported business focus should be South'
assert 'business focus' in test_brief.get('executive_finding','')
assert 'r=' not in test_brief.get('executive_finding','')
assert 'SLA' in test_brief.get('executive_finding','')
assert any('South' in str(d.get('driver')) and d.get('category') == 'Business focus' for d in test_brief.get('drivers',[]))
assert not any(d.get('category') == 'Performance concentration' for d in test_brief.get('drivers',[]))
assert len(test_recs) <= 4, 'recommendations should be consolidated, not one card per chart'
assert all(r.get('evidence_ids') for r in test_recs), 'recommendations should retain traceable evidence'

findings_for_docs = ['Revenue is concentrated in a small number of regions.']
new_types = [
    'Root Cause Analysis (RCA)',
    'Product Requirements Document (PRD)',
    'KPI / Performance Review',
    'Data & Business Analysis Report',
    'Implementation Roadmap',
]
tmp = Path(tempfile.mkdtemp())
for kind in new_types:
    sections = studio_sections(kind, objective, findings_for_docs, sig, df, [], recs, register)
    assert sections and all(isinstance(s, tuple) and len(s) == 2 for s in sections), f'{kind} produced malformed sections'
    joined = ' '.join(b for _, b in sections)
    assert '[image]' not in joined, f'{kind} contains a raw [image] placeholder'
    docx_path = tmp / f'{kind.replace("/", "-").replace(" ", "_")}.docx'
    pdf_path = tmp / f'{kind.replace("/", "-").replace(" ", "_")}.pdf'
    make_docx(docx_path, kind, sections)
    make_pdf(pdf_path, kind, sections)
    assert docx_path.exists() and docx_path.stat().st_size > 0
    assert pdf_path.exists() and pdf_path.stat().st_size > 0
    print(f'{kind}: {len(sections)} sections, docx {docx_path.stat().st_size}B, pdf {pdf_path.stat().st_size}B')

print('\nALL NEW-FEATURE TESTS PASSED')
