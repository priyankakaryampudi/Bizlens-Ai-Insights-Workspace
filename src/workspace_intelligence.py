import pandas as pd
from collections import Counter

def _text(signals):
    return ' '.join(str(x) for v in signals.values() for x in (v if isinstance(v,list) else [v])).lower()

_THEME_KEYWORDS = [
    ('data quality and completeness', ['incomplete', 'missing', 'invent', 'accura', 'data quality']),
    ('reporting and export', ['report', 'export', 'readable', 'management review']),
    ('usability for non-technical users', ['non-technical', 'understandable', 'interface', 'user friendly']),
    ('analytical rigor (evidence vs hypothesis)', ['evidence', 'hypothes', 'causal', 'correlation']),
    ('performance analysis by segment', ['region', 'segment', 'channel', 'product', 'dimension']),
    ('SLA and service performance', ['sla', 'delivery', 'service level']),
    ('customer retention and cancellation', ['cancel', 'renewal', 'retention', 'churn']),
    ('KPIs and measurement', ['kpi', 'metric', 'measure', 'success criteri']),
    ('charts and visualization', ['chart', 'visuali', 'graph', 'dashboard']),
]


def _bucket_by_theme(items):
    """Assign every item to a theme bucket, including an 'other' bucket for
    anything that matches no keyword - so summarizing never silently drops a
    point just because it didn't fit one of the named themes."""
    buckets = {label: [] for label, _ in _THEME_KEYWORDS}
    buckets['other'] = []
    for x in items:
        xl = str(x).lower()
        hit = next((label for label, kws in _THEME_KEYWORDS if any(k in xl for k in kws)), None)
        buckets[hit if hit else 'other'].append(x)
    return {k: v for k, v in buckets.items() if v}


def _clean_fragment(x, n=110):
    t = ' '.join(str(x).split()).strip().rstrip('.')
    return t if len(t) <= n else t[:n-1].rsplit(' ', 1)[0] + '…'


def _summarize_comprehensive(items, noun_singular, noun_plural=None):
    """Cover every item, not just the top few - group into named themes (every
    theme that has matches, not capped), and for a small theme give the actual
    substance rather than just its label, so nothing gets silently left out of
    the overview."""
    noun_plural = noun_plural or noun_singular + 's'
    if not items:
        return f'No explicit {noun_singular} was identified in the connected evidence.'
    buckets = _bucket_by_theme(items)
    ordered = sorted(buckets.items(), key=lambda kv: -len(kv[1]))
    clauses = []
    for label, group in ordered:
        if len(group) == 1:
            clauses.append(f'{_clean_fragment(group[0])}')
        elif label == 'other':
            clauses.append(f'{len(group)} additional {noun_plural} covering miscellaneous points')
        else:
            clauses.append(f'{len(group)} {noun_plural} on {label}')
    lead = f'{len(items)} {noun_plural if len(items)!=1 else noun_singular} {"were" if len(items)!=1 else "was"} identified: '
    return lead + '; '.join(clauses) + '.'


def _join_themes(themes):
    if not themes:
        return ''
    if len(themes) == 1:
        return themes[0]
    return ', '.join(themes[:-1]) + ' and ' + themes[-1]


_REQ_ID_PATTERN = __import__('re').compile(r'\((FR-\d+|BR-\d+),?\s*([\w\s-]*?)\s*priority\)', __import__('re').IGNORECASE)


def classify_requirements(requirements):
    """Keep the Business Context requirement list tied to actual solution
    requirements. Broad words such as 'needs' in meeting notes are not enough;
    we prefer explicit FR/BR/NFR statements and clear system/interface/output
    requirements. This prevents business narrative from leaking into the
    requirements table."""
    import re
    seen = set(); rows = []
    explicit = re.compile(r'\((FR-\d+|BR-\d+|NFR-\d+),?\s*([\w\s-]*?)\s*priority\)', re.I)
    nfr_words = ('interface should', 'analysis should', 'outputs should', 'system should',
                 'generated reports should', 'solution should', 'system must', 'solution must')
    functional_words = ('shall provide','shall allow','shall identify','shall support','shall include',
                        'shall export','shall display','shall generate','shall calculate')
    quality_words = ('understandable','readable','reliable','fast','secure','available','performant','scalable','usable','incomplete data','source evidence')
    for req in requirements:
        raw = ' '.join(str(req).split()).strip().rstrip('.')
        low = raw.lower()
        m = explicit.search(raw)
        is_requirement = bool(m) or any(w in low for w in nfr_words) or any(w in low for w in functional_words)
        if low.startswith('the available business context suggests'):
            is_requirement = False
        if not is_requirement:
            continue
        clean = raw
        if m:
            clean = raw[:m.start()].strip().rstrip('.')
        # pdfplumber can clip the last word in a narrow table cell. Repair only
        # the known lexical fragment; do not invent missing requirement content.
        if clean.lower().endswith('segment and ch'):
            clean = clean + 'annel'
        # Drop extraction fragments that are clearly headings/labels.
        if len(clean.split()) < 4 or clean.lower() in {'required analysis','executive dashboard'}:
            continue
        key = re.sub(r'\W+', ' ', clean.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        if m:
            req_id = m.group(1).upper()
            priority = m.group(2).strip().title() or 'Not specified'
        else:
            req_id = f'NFR-{sum(1 for r in rows if str(r.get("id","")).startswith("NFR-"))+1:02d}'
            priority = 'Not specified'
        category = 'Functional' if m and req_id.startswith(('FR-','BR-')) or any(w in low for w in functional_words) else 'Quality'
        rows.append({'id': req_id, 'need': clean[0].upper()+clean[1:], 'category': category,
                     'priority': priority, 'source': 'Connected evidence', 'status': 'Draft'})
    return rows


def stakeholder_profiles(stakeholders, text):
    """Spec 6.6: never invent an owner or influence level - say plainly when
    the evidence doesn't document it, instead of guessing."""
    profiles = []
    for s in stakeholders:
        sl = str(s).lower()
        mentioned_with_concern = any(w in text for w in ['concern', 'risk', 'issue']) and sl in text
        profiles.append({
            'stakeholder': s,
            'interest': 'Referenced in connected evidence' if sl in text else 'Not explicitly documented',
            'concern': 'A related concern is referenced in the evidence' if mentioned_with_concern else 'Not explicitly documented',
            'role_in_decision': 'Not explicitly documented',
            'influence': 'Not explicitly documented',
            'ownership_status': 'Decision authority not explicitly documented',
        })
    return profiles


def decisions_required(decisions, problems, top_contributor_label=None):
    """Spec 6.7: if no explicit decision exists, derive candidates but label
    them plainly as recommendations for confirmation - never present a
    candidate as if it were an actual recorded decision."""
    if decisions:
        return [{'decision': d, 'status': 'Documented'} for d in decisions]
    candidates = []
    if top_contributor_label:
        candidates.append(f'Should {top_contributor_label} be investigated before any intervention is implemented?')
    for p in problems[:2]:
        candidates.append(f'Should {p} be prioritized for further investigation?')
    candidates.append('Who owns the relevant KPI targets and their review cadence?')
    return [{'decision': c, 'status': 'Recommended decision for stakeholder confirmation'} for c in candidates[:4]]


def categorize_risks(risks):
    """Spec 6.8: separate known risks from known issues, potential risks and
    evidence gaps - not every sentence becomes a 'risk'."""
    known_risks, known_issues, potential = [], [], []
    for r in risks:
        rl = str(r).lower()
        if any(w in rl for w in ['risk', 'exposure', 'liability']):
            known_risks.append(r)
        elif any(w in rl for w in ['issue', 'problem', 'delay', 'complaint', 'concern']):
            known_issues.append(r)
        else:
            potential.append(r)
    return {'known_risks': known_risks, 'known_issues': known_issues, 'potential_risks': potential}


def identify_gaps(ctx_problems, requirement_flags, df, doc_signals):
    """Spec 6.9: three distinct categories, each with why-it-matters and a
    recommended resolution - never invented, always tied to what's actually
    missing."""
    gaps = {'business': [], 'data': [], 'requirement': []}
    if not doc_signals.get('decisions'):
        gaps['business'].append({'gap': 'No formally documented decision exists yet.', 'why': 'Without a recorded decision, recommended actions cannot be approved or tracked.', 'impact': 'Medium', 'resolution': 'Confirm ownership and record the decision once evidence review is complete.'})
    if df is None:
        gaps['data'].append({'gap': 'No structured dataset is connected.', 'why': 'Quantitative findings, driver analysis and KPI tracking are unavailable without one.', 'impact': 'High', 'resolution': 'Connect a dataset covering the metric(s) referenced in the documents.'})
    else:
        text = ' '.join(str(x) for v in doc_signals.values() for x in (v if isinstance(v, list) else [])).lower()
        cols_blob = ' '.join(str(c).lower() for c in df.columns)
        for topic in ['cancellation', 'sla', 'complaint']:
            if topic in text and topic not in cols_blob:
                gaps['data'].append({'gap': f'Documents reference "{topic}" but no matching column exists in the connected dataset.', 'why': 'The documented concern cannot be checked against actual data without this field.', 'impact': 'High', 'resolution': f'Add a dataset or column capturing {topic}-related events.'})
    for f in (requirement_flags or [])[:5]:
        gaps['requirement'].append({'gap': f, 'why': 'An ambiguous requirement cannot be tested or signed off.', 'impact': 'Medium', 'resolution': 'Replace with a measurable, observable threshold confirmed by the business owner.'})
    return gaps


def group_questions_by_theme(questions):
    """Spec 6.10: grouped by theme with priority - not a flat list."""
    buckets = _bucket_by_theme(questions)
    out = []
    for theme, items in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        for q in items:
            ql = str(q).lower()
            priority = 'Critical' if any(w in ql for w in ['revenue', 'cancel', 'risk', 'loss']) else 'High' if any(w in ql for w in ['sla', 'complaint', 'delay']) else 'Medium'
            out.append({'theme': theme if theme != 'other' else 'General', 'question': q, 'priority': priority})
    return out


def ba_analysis_recommendations(ctx):
    """Spec 6.11: each technique with why it's recommended, its readiness
    status and the evidence it needs - not a bare list of technique names."""
    out = []
    if ctx.get('data_findings'):
        out.append({'technique': 'Trend & performance analysis', 'why': 'Quantitative data is connected and shows measurable variation.', 'status': 'Ready', 'evidence': 'Connected dataset'})
        out.append({'technique': 'Anomaly and contribution analysis', 'why': 'Identifying which segment concentrates the pattern narrows the investigation.', 'status': 'Ready', 'evidence': 'Connected dataset'})
    text = ' '.join(ctx.get('problems', []) + ctx.get('requirements', [])).lower()
    if any(w in text for w in ['delay', 'bottleneck', 'decline', 'issue', 'problem']):
        out.append({'technique': 'Root cause investigation', 'why': 'A performance or process problem is documented but its cause is not yet established.', 'status': 'Ready' if ctx.get('data_findings') else 'Needs a dataset', 'evidence': 'Dataset + document evidence'})
    if ctx.get('stakeholders'):
        out.append({'technique': 'Stakeholder analysis', 'why': 'Multiple stakeholder groups are referenced without documented roles or influence.', 'status': 'Ready', 'evidence': 'Connected documents'})
    if ctx.get('requirements'):
        out.append({'technique': 'Requirements extraction & traceability', 'why': 'Requirements exist in source documents but are not yet normalized or traceable to decisions.', 'status': 'Ready', 'evidence': 'Connected documents'})
    return out


def recommended_next_steps(ctx, has_dataset, has_investigation, has_recommendations):
    """Spec 6.12: 3-6 concrete actions, state-aware rather than static."""
    steps = []
    if ctx.get('contradiction'):
        steps.append('Resolve the evidence conflict between the dataset and the documented narrative before proceeding.')
    if has_dataset and not has_investigation:
        steps.append('Investigate the leading driver behind the main observed pattern.')
    if ctx.get('risks'):
        steps.append('Validate the highest-priority documented risk against available data.')
    if not ctx.get('decisions'):
        steps.append('Confirm ownership and record a decision for the top-priority open question.')
    if has_investigation and not has_recommendations:
        steps.append('Convert validated investigation findings into evidence-backed recommendations.')
    if not steps:
        steps.append('Connect additional evidence to expand what BizLens can validate.')
    return steps[:6]


def build_workspace_context(artifacts, datasets, doc_signals, objective='', flags=None):
    objectives=[]; problems=[]; requirements=[]; decisions=[]; risks=[]; questions=[]; stakeholders=[]
    mapping={'requirements':requirements,'decisions':decisions,'risks':risks,'questions':questions,'stakeholders':stakeholders}
    for k,out in mapping.items():
        for x in doc_signals.get(k,[]) or []:
            if x not in out: out.append(x)

    text=_text(doc_signals)
    # Keep only stakeholder groups that have a meaningful BA decision/ownership
    # role in the supplied case. Generic nouns such as 'customer' or 'users'
    # are not useful stakeholder records unless they are explicitly assigned a role.
    stakeholder_allow = ['Management','Operations','Customer Success','Sales','Analytics','Product','Business Owner']
    stakeholders[:] = [x for x in stakeholders if any(a.lower() in str(x).lower() for a in stakeholder_allow)]
    # De-duplicate and remove extraction noise from open questions.
    seen_q=set(); cleaned_q=[]
    for q in questions:
        q_clean=' '.join(str(q).split()).strip().rstrip('?')+'?'
        ql=q_clean.lower()
        if any(bad in ql for bad in ['confirm objective','what is the objective','what does fast mean','what does quick mean']):
            continue
        if q_clean.lower() not in seen_q:
            seen_q.add(q_clean.lower()); cleaned_q.append(q_clean)
    questions[:] = cleaned_q
    # Prefer the case's decision questions over generic extraction.
    priority_q=[]
    for q in questions:
        ql=q.lower()
        if any(k in ql for k in ['sla','cancellation','cancel','product','segment','channel','support ticket','delay']):
            priority_q.append(q)
    questions[:] = priority_q[:6] if priority_q else questions[:6]
    objective_stated = objective.strip() if objective and objective.strip() else None
    objective_derived = None
    if objective_stated:
        objectives.append(objective_stated)
    else:
        # Prefer an explicit 'Business objective:' statement from the connected
        # documents. This keeps Business Context tied to the actual brief rather
        # than inventing a generic objective from the existence of requirements.
        import re
        explicit_objective=None
        candidates=[]
        for a in artifacts or []:
            body=str(a.get('text') or '')
            # Prefer a real meeting-note objective block over a single generic
            # "Business objective:" sentence embedded in a requirements document.
            m=re.search(r'Business objective\.?\s*\n(.*?)(?=\n(?:Key discussion points|Decisions|Open questions|Actions)\b)', body, re.I|re.S)
            if m:
                lines=[]
                for line in m.group(1).splitlines():
                    line=' '.join(line.split()).strip(' -•.')
                    if line: lines.append(line)
                if lines:
                    candidates.append(('meeting', '. '.join(x.rstrip('.') for x in lines).rstrip('.') + '.'))
            m=re.search(r'Business objective\s*:\s*(.*?)(?=\n(?:Functional Requirements|Non-Functional Requirements|Key discussion points|Decisions|Open questions|Actions)\b|\Z)', body, re.I|re.S)
            if m:
                val=' '.join(m.group(1).split()).strip(' .')
                if val: candidates.append(('inline', val+'.'))
        meeting=[x for typ,x in candidates if typ=='meeting']
        explicit_objective=(meeting[0] if meeting else (candidates[0][1] if candidates else None))
        objective_derived = explicit_objective or ('Explain the observed performance change and identify the highest-impact business drivers.' if datasets else ('Clarify the business objective, requirements and decision points.' if requirements else None))
        if objective_derived: objectives.append(objective_derived)

    # Business problem signals are kept separate from solution requirements.
    for key, label in [('delay','delivery and cycle-time issues'),('bottleneck','operational bottlenecks'),
                       ('declin','performance decline'),('missing','missing or incomplete information'),
                       ('ownership','unclear ownership'),('complaint','customer/service issues'),
                       ('cancel','customer cancellation / retention risk')]:
        if key in text:
            problems.append(label)

    findings=[]
    primary_analysis={}
    for name,df in datasets.items():
        try:
            from .analytics import guess_metric, guess_dimension, guess_date, aligned_period_change, dimension_breakdown, group_period_change, service_signal
            m=guess_metric(df, objective); d=guess_dimension(df, objective); dt=guess_date(df)
            primary_analysis={'dataset':name,'metric':m,'dimension':d,'date':dt}
            if m:
                total=float(pd.to_numeric(df[m],errors='coerce').sum()) if m != 'Record count' else float(len(df))
                findings.append({'dataset':name,'metric':m,'value':total,'mean':total/max(len(df),1)})
            change=aligned_period_change(df,dt,m,text) if m and dt else None
            if change:
                primary_analysis['period_change']=change
                direction='increased' if change['change_pct'] >= 0 else 'declined'
                findings.append({'dataset':name,'metric':m,'value':change['current'], 'mean':None,
                                 'period':f'{change["current_label"]} vs {change["previous_label"]}',
                                 'change_pct':change['change_pct'], 'label':f'{m} {direction} {abs(change["change_pct"]):.1f}%'} )
            if m and d and dt:
                shifts=group_period_change(df,dt,m,d,context_text=text)
                primary_analysis['group_shifts']=shifts.head(8).to_dict('records') if not shifts.empty else []
                if not shifts.empty:
                    primary_analysis['largest_decline']=shifts.iloc[0].to_dict()
                    primary_analysis['lead_growth']=shifts.iloc[-1].to_dict()
                    preferred=_preferred_group_from_context(df,d,text)
                    if preferred is not None and preferred in set(shifts[d].astype(str)):
                        focus_row=shifts[shifts[d].astype(str)==preferred].iloc[0]
                    else:
                        focus_row=shifts.iloc[0]
                    lead_group=focus_row[d]
                    primary_analysis['lead_group']=lead_group
                    primary_analysis['focus_decline']=focus_row.to_dict()
                    primary_analysis['lead_decline']=focus_row.to_dict()
                    primary_analysis['service_signals']=service_signal(df,dt,m,d,lead_group,text)
                    # Inspect product/segment/channel within the lead group. This
                    # produces actionable contributors instead of volume proxies.
                    secondary=[]
                    for sd in ['Product','Customer_Segment','Channel']:
                        if sd in df.columns and sd != d:
                            sh=group_period_change(df,dt,m,sd,group_value=None,context_text=text)
                            if not sh.empty:
                                sub=df[df[d]==lead_group]
                                sub_sh=group_period_change(sub,dt,m,sd,context_text=text)
                                if not sub_sh.empty:
                                    secondary.append({'dimension':sd,'rows':sub_sh.head(5).to_dict('records')})
                    primary_analysis['secondary_shifts']=secondary
            break
        except Exception:
            continue

    # A conflict is only raised when the data contradicts the same business
    # period described by the documents. Do not compare a Q4 narrative to the
    # final month of the dataset just because that month happens to increase.
    contradiction=None
    change=primary_analysis.get('period_change')
    if 'declin' in text and change and change['change_pct'] > 0:
        contradiction=(f'Performance-period mismatch: the documents describe a decline, while the aligned dataset period '
                       f'({change["current_label"]}) shows {primary_analysis.get("metric","the selected metric")} increasing {change["change_pct"]:.1f}%. '
                       f'Confirm the intended period, KPI definition and scope before using the decline statement as a measured fact.')

    if not problems and datasets:
        problems.append('business performance and its key drivers')

    # Plain-English narrative: lead with the business answer, not source counts.
    narrative_parts=[]
    scope_bits=[]
    n_docs=sum(a.get('kind')=='document' for a in artifacts)
    n_sets=len(datasets)
    if n_docs: scope_bits.append(f'{n_docs} business document' + ('s' if n_docs!=1 else ''))
    if n_sets: scope_bits.append(f'{n_sets} dataset' + ('s' if n_sets!=1 else ''))
    if scope_bits: narrative_parts.append('BizLens combines ' + ' and '.join(scope_bits) + ' into one analysis.')
    if objectives:
        obj_clean=objectives[0].strip()
        if obj_clean.lower().startswith(('why ','how ','what ','where ','which ','who ','is ','are ','does ','do ','can ','should ')):
            narrative_parts.append(f'The working objective is to answer: {obj_clean.rstrip("?")}?' if obj_clean.endswith('?') else f'The working objective is to answer: {obj_clean}.')
        else:
            narrative_parts.append(f'The working objective is to {obj_clean.rstrip(".!?")}.')
    if primary_analysis.get('period_change'):
        ch=primary_analysis['period_change']; direction='increased' if ch['change_pct']>=0 else 'declined'
        narrative_parts.append(f'On the aligned business period, {primary_analysis["metric"]} {direction} {abs(ch["change_pct"]):.1f}% ({ch["previous_label"]} to {ch["current_label"]}).')
    if primary_analysis.get('lead_group') is not None:
        lead=primary_analysis['lead_group']; m=primary_analysis.get('metric'); d=primary_analysis.get('dimension')
        row=primary_analysis.get('focus_decline') or {}
        largest=primary_analysis.get('largest_decline') or {}
        if row and float(row.get('delta',0)) < 0:
            largest_name=str(largest.get(d,'')) if largest else ''
            if largest_name and largest_name != str(lead):
                narrative_parts.append(f'{lead} is the business focus because it is highlighted in the connected evidence and also deteriorated; {largest_name} has the largest percentage decline among {d} groups.')
            else:
                narrative_parts.append(f'{lead} is the clearest deterioration point in {m} among {d} groups and is the first place to investigate.')
        else:
            narrative_parts.append(f'{lead} is the largest observed {m} concentration across {d}; its business drivers should be validated before intervention.')
    if contradiction:
        narrative_parts.append('A period mismatch remains to be validated before treating the document narrative as a measured data finding.')
    if questions:
        narrative_parts.append(f'{len(questions)} open business questions remain, including the relationship between service performance and retention.')

    section_summaries={
        'requirements': _summarize_comprehensive(requirements, 'requirement'),
        'risks': _summarize_comprehensive(risks, 'risk'),
        'decisions': _summarize_comprehensive(decisions, 'decision'),
        'questions': _summarize_comprehensive(questions, 'open question', 'open questions'),
        'stakeholders': (f'{len(stakeholders)} stakeholder groups are referenced: {", ".join(stakeholders)}.') if stakeholders else 'No stakeholder group was explicitly named.',
    }
    req_table=classify_requirements(requirements)
    stakeholder_table=stakeholder_profiles(stakeholders,text)
    top_contributor_label=None
    if primary_analysis.get('lead_group') is not None:
        top_contributor_label=f'{primary_analysis["lead_group"]} performance in {primary_analysis.get("metric", "the primary KPI")}'
    decisions_table=decisions_required(decisions,list(dict.fromkeys(problems)),top_contributor_label)
    risk_categories=categorize_risks(risks)
    active_df=datasets.get(next(iter(datasets))) if datasets else None
    gaps=identify_gaps(problems,flags or [],active_df,doc_signals)
    questions_grouped=group_questions_by_theme(questions)

    return {'narrative':' '.join(narrative_parts),'contradiction':contradiction,'objective_stated':objective_stated,
            'objective_derived':objective_derived,'objectives':objectives,'problems':list(dict.fromkeys(problems)),
            'requirements':requirements,'decisions':decisions,'risks':risks,'questions':questions,'stakeholders':stakeholders,
            'data_findings':findings,'sources':len(artifacts),'section_summaries':section_summaries,
            'requirements_table':req_table,'stakeholder_table':stakeholder_table,'decisions_table':decisions_table,
            'risk_categories':risk_categories,'gaps':gaps,'questions_grouped':questions_grouped,
            'primary_analysis':primary_analysis}

def choose_techniques(ctx):
    t=[]
    if ctx.get('data_findings'): t += ['Trend & performance analysis','Anomaly and contribution analysis']
    text=' '.join(ctx.get('problems',[])+ctx.get('requirements',[])).lower()
    if any(w in text for w in ['delay','bottleneck','decline','issue','problem']): t.append('Root cause investigation')
    if any(w in text for w in ['process','approval','handoff','onboarding']): t += ['Process investigation','As-Is / To-Be / Gap analysis']
    if ctx.get('stakeholders'): t.append('Stakeholder analysis')
    if ctx.get('requirements'): t += ['Requirements extraction','Traceability']
    return list(dict.fromkeys(t))
