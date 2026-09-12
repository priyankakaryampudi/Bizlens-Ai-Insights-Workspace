"""Central Evidence Object model - Master Refactor spec sections 3-4.

Every important claim across BizLens (Home, Business Context, Investigation,
Recommendations, Ask BizLens, Deliverables) should be traceable to one of
these evidence items instead of every page independently rewording the same
underlying fact. This module builds one evidence register per workspace
refresh and exposes small helpers so pages can cite it consistently.

Each evidence item carries, where available:
    evidence_id, source_file, source_type, location, claim, value,
    metric, dimension, period, confidence, classification, supporting_text
"""
import re
import pandas as pd
from .analytics import (
    guess_metric, guess_dimension, guess_date, dimension_breakdown, trend, aligned_period_change, group_period_change, service_signal,
)

# A document-derived claim's classification depends on which bucket the
# sentence was filed into by doc_intel.extract_signals - a stated requirement
# or decision is DOCUMENT-STATED, a risk is DOCUMENT-SUPPORTED (someone raised
# it, it hasn't been validated), and an open question is genuinely UNKNOWN.
_DOC_CLASSIFICATION = {
    'requirements': 'DOCUMENT-STATED',
    'decisions': 'DOCUMENT-STATED',
    'business_rules': 'DOCUMENT-STATED',
    'risks': 'DOCUMENT-SUPPORTED',
    'actions': 'DOCUMENT-SUPPORTED',
    'questions': 'UNKNOWN',
}

# Kept in sync with reports.py's list: a real requirement sentence in this
# corpus has a modal/action verb; a run of scraped UI labels concatenated by
# extraction ("Executive dashboard Investigation findings...") does not.
_REQ_VERB_HINTS = ('should','shall','must','need','want','suggest','support',
                    'identify','provide','allow','handle','distinguish','determine',
                    'enable','ensure','maintain','protect','clearly','believe')


def _find_source(artifacts, sentence):
    """Trace a claim sentence back to the artifact it was extracted from,
    instead of labelling every document claim as generic 'connected
    documents'. doc_intel combines all document text before classifying, so
    this does a direct substring lookup against each artifact's own text."""
    needle = str(sentence).strip()[:40]
    if not needle:
        return 'connected documents', None
    for a in artifacts or []:
        text = a.get('text') or ''
        if needle and needle in text:
            return a.get('name', 'connected documents'), a.get('kind')
    return 'connected documents', None


def build_evidence_register(artifacts, df, sig, objective=''):
    """Build the shared Evidence Object register for the current workspace
    state. Deliberately capped per category so the register stays a curated
    evidence set, not a dump of every sentence in every file (spec section
    37 - do not over-generate)."""
    register = []
    counter = [0]

    def add(**kw):
        counter[0] += 1
        item = {
            'evidence_id': f'E-{counter[0]:03d}',
            'source_file': kw.get('source_file', 'connected documents'),
            'source_type': kw.get('source_type', 'document'),
            'location': kw.get('location', ''),
            'claim': kw.get('claim', ''),
            'value': kw.get('value', ''),
            'metric': kw.get('metric', ''),
            'dimension': kw.get('dimension', ''),
            'period': kw.get('period', ''),
            'confidence': kw.get('confidence', ''),
            'classification': kw.get('classification', 'OBSERVED'),
            'supporting_text': kw.get('supporting_text') or kw.get('claim', ''),
        }
        register.append(item)
        return item

    if df is not None and len(df):
        dataset_name = next((a.get('name') for a in (artifacts or []) if a.get('kind') in ('csv','xlsx','xls','dataset') and a.get('name')), 'connected dataset')
        metric = guess_metric(df, objective)
        dim = guess_dimension(df, objective)
        date_col = guess_date(df)

        if metric and dim:
            g = dimension_breakdown(df, dim, metric, 12)
            if len(g):
                for _, row in g.head(3).iterrows():
                    add(source_file=dataset_name, source_type='dataset',
                        claim=f'{row[dim]} records {metric} of {float(row.total):,.2f}.',
                        value=float(row.total), metric=metric, dimension=f'{dim}={row[dim]}',
                        period='Full connected dataset', confidence='High', classification='OBSERVED')
                total = float(g.total.sum()) or 1.0
                top = g.iloc[0]
                add(source_file=dataset_name, source_type='dataset',
                    claim=f'{top[dim]} accounts for {float(top.total) / total * 100:.1f}% of observed {metric}.',
                    value=f'{float(top.total) / total * 100:.1f}%', metric=metric, dimension=dim,
                    period='Full connected dataset', confidence='High', classification='DERIVED',
                    supporting_text='Calculated as this group\'s share of total observed value across the dataset.')

        if metric and date_col:
            t = trend(df, date_col, metric)
            if len(t) >= 2 and 'change_pct' in t.columns and pd.notna(t.iloc[-1]['change_pct']):
                pct = float(t.iloc[-1]['change_pct'])
                add(source_file=dataset_name, source_type='dataset',
                    claim=f'{metric} changed {pct:.1f}% in the latest available period.',
                    value=f'{pct:.1f}%', metric=metric, period=str(t.iloc[-1].get('period', 'Latest available period')),
                     confidence='High', classification='OBSERVED')
            # Add business-period evidence used by Investigation/Recommendations
            # so decision cards can point back to concrete dataset findings.
            context_text = ' '.join(str(v) for v in (sig or {}).values())
            aligned = aligned_period_change(df, date_col, metric, context_text)
            if aligned:
                add(source_file=dataset_name, source_type='dataset',
                    claim=f'{metric} changed {aligned["change_pct"]:+.1f}% from {aligned["previous_label"]} to {aligned["current_label"]}.',
                    value=f'{aligned["change_pct"]:+.1f}%', metric=metric, period=f'{aligned["previous_label"]} to {aligned["current_label"]}',
                    confidence='High', classification='DERIVED',
                    supporting_text='Calculated from the two latest aligned business periods.')
            if metric and dim and date_col:
                shifts = group_period_change(df, date_col, metric, dim, context_text=context_text)
                focus = None
                low_text = context_text.lower()
                for value in df[dim].dropna().astype(str).unique():
                    if value.lower() in low_text:
                        focus = value; break
                if focus and not shifts.empty:
                    row = shifts[shifts[dim].astype(str)==str(focus)]
                    if not row.empty:
                        rr=row.iloc[0]
                        add(source_file=dataset_name, source_type='dataset',
                            claim=f'{focus} changed {float(rr["change_pct"]):+.1f}% in {metric} from {shifts.attrs.get("previous_period")} to {shifts.attrs.get("current_period")}.',
                            value=f'{float(rr["change_pct"]):+.1f}%', metric=metric, dimension=f'{dim}={focus}',
                            period=f'{shifts.attrs.get("previous_period")} to {shifts.attrs.get("current_period")}',
                            confidence='High', classification='DERIVED',
                            supporting_text='Calculated as the focus group change across the aligned business periods.')
                    for ss in service_signal(df, date_col, metric, dim, focus, context_text):
                        if ss.get('kind') in ('sla','tickets') and ((ss.get('kind')=='sla' and ss.get('delta',0)<0) or (ss.get('kind')=='tickets' and ss.get('delta',0)>0)):
                            add(source_file=dataset_name, source_type='dataset',
                                claim=f'{ss["label"]} in {focus}: {ss["detail"]}.', value=ss['detail'],
                                metric=ss['label'], dimension=f'{dim}={focus}', period=f'{shifts.attrs.get("previous_period")} to {shifts.attrs.get("current_period")}',
                                confidence='High', classification='DERIVED',
                                supporting_text='Calculated from the operational field in the connected dataset.')


    # Quantify cancellation evidence explicitly when the dataset exposes a cancellation field.
    if df is not None and len(df):
        canc_col = next((c for c in df.columns if str(c).lower().replace('_',' ') in ('cancellations','cancellation','cancelled','cancel')), None)
        if canc_col:
            cancellation_total = int(pd.to_numeric(df[canc_col], errors='coerce').fillna(0).sum())
            add(source_file=dataset_name, source_type='dataset',
                claim=f'{cancellation_total:,} recorded cancellation' + ('s' if cancellation_total != 1 else '') + ' are present in the connected dataset.',
                value=cancellation_total, metric='Cancellations', period='Full connected dataset',
                confidence='High', classification='OBSERVED',
                supporting_text='Count derived from the cancellation field in the connected dataset.')

    for key, vals in (sig or {}).items():
        if key == 'stakeholders' or str(key).startswith('_'):
            continue
        cls = _DOC_CLASSIFICATION.get(key, 'DOCUMENT-SUPPORTED')
        for item in (vals or [])[:8]:
            text = str(item).strip()
            # Repair a known PDF table-extraction line break where the sentence
            # ends at 'opportunities to.' and the next source line contains the
            # continuation. Keep the correction limited to this exact fragment.
            if text.endswith('opportunities to.'):
                text = text[:-1] + ' reduce avoidable cancellations.'
            # A fragment like "Known business concerns." carries no real
            # information, and a run of scraped UI labels with no verb
            # ("Executive dashboard Investigation findings...") isn't a real
            # requirement either - both just put noise in front of every
            # document that cites the register.
            if len(text) < 30:
                continue
            if key == 'requirements' and not any(v in text.lower() for v in _REQ_VERB_HINTS):
                continue
            src, kind = _find_source(artifacts, item)
            add(source_file=src, source_type=kind or 'document',
                claim=text, classification=cls,
                confidence=('Document-stated' if cls == 'DOCUMENT-STATED'
                            else 'Unresolved' if cls == 'UNKNOWN'
                            else 'Requires validation'))

    return register


def evidence_by_id(register, evidence_id):
    for item in register or []:
        if item.get('evidence_id') == evidence_id:
            return item
    return None


def source_line(item):
    """Compact, one-line source caption - spec section 15 / 29."""
    if not item:
        return 'Source: connected evidence'
    parts = [item.get('source_file') or 'connected evidence']
    if item.get('metric'):
        parts.append(str(item['metric']))
    if item.get('dimension'):
        parts.append(str(item['dimension']))
    return 'Source: ' + ' · '.join(p for p in parts if p)


def find_evidence_for_text(register, text, limit=3):
    """Loose keyword match so a page can answer 'why do you say this' by
    pointing at the register entries that most overlap with a claim, without
    a full semantic-search stack."""
    terms = set(re.findall(r'[a-zA-Z]{4,}', str(text).lower()))
    if not terms:
        return []
    scored = []
    for item in register or []:
        claim_terms = set(re.findall(r'[a-zA-Z]{4,}', str(item.get('claim', '')).lower()))
        score = len(terms & claim_terms)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: -x[0])
    return [it for _, it in scored[:limit]]


def register_summary(register):
    """Small counts panel for workspace-health style displays."""
    out = {'total': len(register or [])}
    for item in register or []:
        c = item.get('classification', 'OBSERVED')
        out[c] = out.get(c, 0) + 1
    return out
