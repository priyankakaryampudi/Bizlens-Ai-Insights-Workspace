"""Evidence-first workspace intelligence for BizLens V2."""
import pandas as pd
from src.analytics import guess_metric, guess_dimension, guess_date, auto_insights, trend, investigation_metrics, quality_actions

def build_evidence_graph(artifacts, df, signals, objective=''):
    nodes=[]; links=[]
    for a in artifacts:
        nodes.append({'type':'source','name':a.get('name','source'),'kind':a.get('kind','document')})
    for kind in ['requirements','risks','decisions','questions','stakeholders']:
        for item in (signals.get(kind,[]) or [])[:12]:
            nodes.append({'type':kind[:-1] if kind.endswith('s') else kind,'name':str(item),'source':'documents'})
            links.append({'from':'documents','to':str(item),'relation':kind})
    findings=[]
    if df is not None and len(df):
        metric, dim, date=guess_metric(df,objective),guess_dimension(df,objective),guess_date(df)
        for f in auto_insights(df,metric,dim,date)[:6]:
            findings.append({'finding':f,'metric':metric,'dimension':dim,'date':date,'source':'active dataset','confidence':'Observed'})
        if metric and dim:
            g=investigation_metrics(df,metric,dim,20)
            if not g.empty:
                top=g.iloc[0]
                findings.append({'finding':f'{top[dim]} is the largest observed contributor for {metric} ({top.share_pct:.1f}% share).','metric':metric,'dimension':dim,'date':date,'source':'active dataset','confidence':'Observed'})
    return {'nodes':nodes,'links':links,'findings':findings}

def _preferred_group_from_context(df, dimension, context_text):
    """Prefer a group explicitly highlighted by the business documents when
    choosing the investigation focus. This prevents a raw rank from replacing
    the business question (for example, a document calling out South)."""
    if df is None or not dimension or dimension not in df.columns:
        return None
    import re
    text=str(context_text or '').lower()
    scores=[]
    for value in df[dimension].dropna().astype(str).unique():
        v=value.lower()
        if v not in text: continue
        score=text.count(v)
        for sentence in re.split(r'(?<=[.!?])\s+', text):
            if v in sentence and any(w in sentence for w in ['declin','weaken','priority','concern','issue','deteriorat','attention']):
                score += 5
        scores.append((score,value))
    return max(scores,key=lambda x:x[0])[1] if scores else None


def driver_candidates(df, metric, dim, objective='', signals=None):
    """Business-driver analysis.

    The previous implementation ranked every numeric column by a statistical
    coefficient. That made Orders/Customers look like 'root causes' even though
    they are usually volume companions of Revenue. This version prioritizes:
    1) period-over-period deterioration, 2) operational signals such as SLA,
    3) product/segment/channel contribution shifts, and 4) explicit evidence gaps.
    """
    if df is None or not metric or not dim:
        return []
    from .analytics import guess_date, aligned_period_change, group_period_change, service_signal
    date=guess_date(df)
    text=' '.join([str((signals or {}).get('_context_text',''))] + [str(x) for v in (signals or {}).values() for x in (v if isinstance(v,list) else [])]).lower()
    out=[]
    try:
        shifts=group_period_change(df,date,metric,dim,context_text=text)
        if not shifts.empty:
            preferred=_preferred_group_from_context(df,dim,text)
            lead=preferred or str(shifts.iloc[0][dim])
            focus_rows=shifts[shifts[dim].astype(str)==str(lead)] if preferred else shifts.head(1)
            for _,r in focus_rows.iterrows():
                if float(r['delta']) < 0:
                    pct=r['change_pct']
                    detail=f'{r[dim]} declined {abs(pct):.1f}% from {shifts.attrs.get("previous_period")} to {shifts.attrs.get("current_period")}' if pd.notna(pct) else f'{r[dim]} declined in the latest comparison period'
                    out.append({'driver':str(r[dim]),'category':'Business focus','relationship':detail,
                                'confidence':'Strong signal for investigation focus','validation_required':True})
        # Operational metrics inside the selected business-focus group.
        if not shifts.empty:
            lead=_preferred_group_from_context(df,dim,text) or str(shifts.iloc[0][dim])
            for sig in service_signal(df,date,metric,dim,lead,text):
                if sig['kind']=='sla' and sig['delta'] < -0.02:
                    out.append({'driver':f'SLA performance in {lead}','category':'Operational signal',
                                'relationship':sig['detail'],'confidence':'Strong signal','validation_required':True})
                elif sig['kind']=='tickets' and sig['delta'] > 0:
                    prev=sig['previous']; curr=sig['current']; pct=((curr/prev)-1)*100 if prev else None
                    detail=f'{curr:.3f} per order vs {prev:.3f} per order' + (f' ({pct:+.1f}%)' if pct is not None else '')
                    out.append({'driver':f'Support-ticket pressure in {lead}','category':'Operational signal',
                                'relationship':detail,'confidence':'Moderate signal','validation_required':True})
            # Secondary business dimensions: identify where the revenue loss is concentrated.
            for sd in ['Product','Customer_Segment','Channel']:
                if sd in df.columns and sd != dim:
                    sub=group_period_change(df[df[dim]==lead],date,metric,sd,context_text=text)
                    if not sub.empty:
                        for _,r in sub.head(2).iterrows():
                            if float(r['delta']) < 0:
                                pct=r['change_pct']
                                detail=f'{r[sd]} declined {abs(pct):.1f}% within {lead}' if pd.notna(pct) else f'{r[sd]} declined within {lead}'
                                out.append({'driver':f'{r[sd]} ({sd})','category':'Contribution shift',
                                            'relationship':detail,'confidence':'Moderate signal','validation_required':True})
    except Exception:
        pass
    # Keep a useful fallback for datasets without time fields/dimensions.
    if not out:
        try:
            g=investigation_metrics(df,metric,dim,8)
            for _,r in g.head(3).iterrows():
                out.append({'driver':str(r[dim]),'category':'Observed concentration',
                            'relationship':f'{r.share_pct:.1f}% of observed {metric}','confidence':'Moderate signal',
                            'validation_required':True})
        except Exception:
            pass
    preferred=_preferred_group_from_context(df,dim,text)
    if preferred:
        out.sort(key=lambda x: 0 if str(preferred).lower() in str(x.get('driver','')).lower() else 1)
    return out[:8]


def root_cause_status(hypotheses):
    counts={'Confirmed':0,'Strongly supported':0,'Partially supported':0,'Unvalidated':0,'Rejected':0}
    for h in hypotheses or []:
        status=h.get('status','')
        if status=='Strong operational signal': counts['Partially supported']+=1
        elif status=='Observed concentration': counts['Partially supported']+=1
        elif status=='Document-supported lead': counts['Unvalidated']+=1
        else: counts['Unvalidated']+=1
    return counts


def validation_steps(hypothesis, metric, dim):
    kind=hypothesis.get('kind')
    if kind=='sla':
        return ['Obtain delivery-level SLA breach data for the affected region and period.',
                'Compare breach frequency with revenue/order changes by product, segment and channel.',
                'Confirm the operational cause with the Operations owner before implementing a fix.']
    if kind=='tickets':
        return ['Break support tickets down by reason, product and region.',
                'Check whether ticket spikes occur before the performance deterioration.',
                'Confirm the process owner and whether the ticket pattern represents a service bottleneck.']
    if kind=='contribution':
        return [f'Compare {hypothesis.get("driver","this group")} across the same periods and against the remaining groups.',
                f'Check whether the change persists across the same focus area and period, and whether order volume or mix explains part of the movement.',
                'Confirm the business explanation with the accountable owner.']
    if kind=='cancellation':
        return ['Obtain customer/order-level cancellation records with cancellation reason and the same period definition used for the performance analysis.',
                'Link SLA breaches and support events to the same customer or order where a common key exists, then compare cancellation rates for affected versus unaffected cases.',
                'Check whether the service event occurs before cancellation and segment the result by product, customer segment and region before confirming or rejecting the relationship.']
    return [f'Compare the affected group against the remaining {dim or "business groups"} across the same periods.',
            f'Break {metric} down by product, segment and channel where those fields exist.',
            'Confirm whether the observed pattern has a documented operational explanation.']


def _business_signal_summary(df, brief):
    """Create a concise executive finding from measurable signals."""
    metric = brief.get('metric')
    dim = brief.get('dimension')
    lead = brief.get('lead_group')
    change = brief.get('period_change')
    if not metric or not change:
        return 'The available evidence is sufficient to frame the problem, but not yet to quantify the business change.'
    direction = 'increased' if change['change_pct'] >= 0 else 'declined'
    text = f'{metric} {direction} {abs(change["change_pct"]):.1f}% from {change["previous_label"]} to {change["current_label"]}.'
    if lead and brief.get('lead_change_pct') is not None and brief.get('lead_delta', 0) < 0:
        text += f' {lead} is the business focus because it is explicitly highlighted in the connected evidence and also deteriorated in the aligned comparison.'
    service = brief.get('service_signals') or []
    sla = next((x for x in service if x.get('kind') == 'sla' and x.get('delta', 0) < 0), None)
    tickets = next((x for x in service if x.get('kind') == 'tickets' and x.get('delta', 0) > 0), None)
    if sla and lead:
        text += f' In {lead}, SLA performance fell from {sla["previous"]*100:.1f}% to {sla["current"]*100:.1f}%.'
    if tickets and lead:
        text += f' Support-ticket pressure rose from {tickets["previous"]:.3f} to {tickets["current"]:.3f} per order.'
    product = next((x for x in brief.get('secondary_shifts', []) if x.get('dimension') == 'Product'), None)
    if product:
        declines = [r for r in product.get('rows', []) if float(r.get('delta', 0)) < 0]
        if declines:
            names = [str(r['Product']) for r in declines[:2]]
            text += ' The largest product declines in the focus area are ' + ' and '.join(names) + '.'
    return text


def investigation_conclusion(hypotheses, contributors, metric, dim, primary=None):
    established = f'A measurable change in {metric} is visible across the aligned comparison period.' if contributors else 'A measurable business pattern is visible, but its driver is not yet established.'
    not_established = 'The evidence identifies where to investigate and shows operational signals moving at the same time; it does not prove that one caused the other.'
    most_credible = f'{hypotheses[0].get("id", "H1")} — {hypotheses[0].get("hypothesis", "the leading business signal")}' if hypotheses else 'No hypothesis is strong enough yet.'
    evidence_required = 'Delivery/SLA breach detail, customer-level cancellation reasons and linkage, plus product, segment and channel breakdowns for the affected period.'
    next_investigation = 'Trace the focus area from the KPI change into service performance, product/segment/channel mix and customer outcomes; then confirm the explanation with the accountable owner.'
    return {'established': established, 'not_established': not_established, 'most_credible': most_credible,
            'evidence_required': evidence_required, 'next_investigation': next_investigation}


def investigation_brief(df, signals, objective=''):
    if df is None or not len(df):
        return {'problem':'No structured metric is available yet.','evidence':[],'hypotheses':[],'next_step':'Validate the business problem using connected documents.'}
    from .analytics import guess_metric, guess_dimension, guess_date, aligned_period_change, group_period_change, service_signal
    metric, dim, date = guess_metric(df, objective), guess_dimension(df, objective), guess_date(df)
    text = ' '.join([str((signals or {}).get('_context_text', ''))] + [str(x) for v in (signals or {}).values() for x in (v if isinstance(v, list) else [])]).lower()
    evidence=[]; contributors=[]; hypotheses=[]; secondary_shifts=[]
    change = aligned_period_change(df, date, metric, text) if metric and date else None
    if change:
        direction = 'increased' if change['change_pct'] >= 0 else 'declined'
        evidence.append(f'{metric} {direction} {abs(change["change_pct"]):.1f}% from {change["previous_label"]} to {change["current_label"]}.')
    shifts = group_period_change(df, date, metric, dim, context_text=text) if metric and dim and date else pd.DataFrame()
    lead = None
    if not shifts.empty:
        neg = shifts[shifts['delta'] < 0]
        preferred = _preferred_group_from_context(df, dim, text)
        if preferred is not None and preferred in set(shifts[dim].astype(str)):
            lead = shifts[shifts[dim].astype(str) == preferred].iloc[0]
        else:
            lead = neg.iloc[0] if not neg.empty else shifts.iloc[0]
        # Show the full ranked regional picture, but only call the explicitly
        # selected business focus the focus area. This avoids false claims such
        # as calling South the "largest" decline when North declined more.
        contributors=[{'group':str(r[dim]),'share':0.0,'value':float(r['current']),'delta':float(r['delta']),
                       'change_pct':float(r['change_pct']) if pd.notna(r['change_pct']) else None}
                      for _,r in shifts.head(8).iterrows()]
        if lead is not None and float(lead['delta']) < 0:
            pct = lead['change_pct']
            qualifier = f' ({abs(pct):.1f}% lower)' if pd.notna(pct) else ''
            evidence.append(f'{lead[dim]} is the business focus and declined {metric} in the aligned comparison{qualifier}.')
            hypotheses.append({'hypothesis':f'{lead[dim]} is the primary focus area for the business investigation; its decline should be traced to operational and commercial contributors.',
                               'status':'Focus area','confidence':'Strong evidence for where to investigate, not proof of cause','kind':'contribution'})
        lead_group = str(lead[dim]) if lead is not None else None
        service = service_signal(df, date, metric, dim, lead_group, text) if lead_group else []
        for ss in service:
            if ss['kind']=='sla' and ss['delta'] < -0.02:
                hypotheses.insert(0, {'hypothesis':f'Service-level performance in {lead_group} deteriorated materially during the same period as the business performance change.',
                                      'status':'Strong operational signal','confidence':'Strong signal; operational cause still needs validation','kind':'sla'})
                evidence.append(f'SLA in {lead_group} moved from {ss["previous"]*100:.1f}% to {ss["current"]*100:.1f}% ({ss["delta"]*100:+.1f} percentage points).')
            elif ss['kind']=='tickets' and ss['delta'] > 0:
                pct = ((ss['current']/ss['previous'])-1)*100 if ss['previous'] else None
                hypotheses.append({'hypothesis':f'Support-ticket pressure increased in {lead_group}, which may indicate greater service friction.',
                                   'status':'Supporting operational signal','confidence':'Moderate signal; ticket reason and timing need validation','kind':'tickets'})
                detail=f'{ss["current"]:.3f} per order vs {ss["previous"]:.3f} per order' + (f' ({pct:+.1f}%)' if pct is not None else '')
                evidence.append(f'Support-ticket pressure in {lead_group} increased to {detail}.')
        # Secondary dimensions inside the focus area.
        for sd in ['Product','Customer_Segment','Channel']:
            if sd in df.columns and sd != dim:
                sub = group_period_change(df[df[dim] == lead_group], date, metric, sd, context_text=text)
                if not sub.empty:
                    secondary_shifts.append({'dimension':sd,'rows':sub.head(6).to_dict('records')})
                    declines = sub[sub['delta'] < 0].head(2)
                    if not declines.empty:
                        names = [str(r[sd]) for _,r in declines.iterrows()]
                        hypotheses.append({'hypothesis':f'{" and ".join(names)} show the main {metric} declines within {lead_group} for {sd.lower()}-level analysis.',
                                           'status':'Contribution signal','confidence':'Moderate signal; validate the business explanation','kind':'contribution'})
    # Cancellation is an evidence gap. Quantify the limitation when possible.
    canc_col = next((c for c in df.columns if str(c).lower().replace('_',' ') in ('cancellations','cancellation','cancelled','cancel')), None)
    cancellation_total = int(pd.to_numeric(df[canc_col], errors='coerce').fillna(0).sum()) if canc_col else None
    if any(w in text for w in ['cancel','retention']):
        if cancellation_total is None:
            limitation = 'The connected dataset does not provide sufficient customer-level cancellation detail.'
        elif cancellation_total == 1:
            limitation = 'Only 1 recorded cancellation is available in the connected dataset.'
        else:
            limitation = f'Only {cancellation_total} recorded cancellations are available in the connected dataset.'
        hypotheses.append({'hypothesis':f'Retention is an important business outcome, but the current evidence is insufficient to establish a service-to-cancellation relationship. {limitation}',
                           'status':'Evidence gap','confidence':'Not enough evidence for a causal conclusion','kind':'cancellation'})
    for i,h in enumerate(hypotheses,1):
        h['id']=f'H{i}'; h['validation']=validation_steps(h,metric,dim)
    drivers=driver_candidates(df,metric,dim,objective,signals)
    root_cause=root_cause_status(hypotheses)
    conclusion=investigation_conclusion(hypotheses,contributors,metric,dim)
    brief={'problem':(objective.strip() if objective and objective.strip() else (f'Explain the {metric} change, identify where the deterioration is concentrated, and determine what should be addressed.' if metric and dim else f'Understand what is driving {metric} and what management should do next.')),
            'metric':metric,'dimension':dim,'date':date,'period_change':change,'evidence':list(dict.fromkeys(evidence))[:8],
            'contributors':contributors,'lead_group':str(lead[dim]) if lead is not None else None,
            'lead_delta':float(lead['delta']) if lead is not None else None,
            'lead_change_pct':float(lead['change_pct']) if lead is not None and pd.notna(lead['change_pct']) else None,
            'service_signals':service_signal(df,date,metric,dim,str(lead[dim]),text) if lead is not None else [],
            'secondary_shifts':secondary_shifts,'hypotheses':hypotheses,'drivers':drivers,'root_cause':root_cause,'conclusion':conclusion}
    brief['executive_finding']=_business_signal_summary(df, brief)
    # Make the solution direction evidence-specific rather than a reusable generic sentence.
    lead_name = brief.get('lead_group')
    service = brief.get('service_signals') or []
    sla = next((x for x in service if x.get('kind') == 'sla' and x.get('delta', 0) < 0), None)
    tickets = next((x for x in service if x.get('kind') == 'tickets' and x.get('delta', 0) > 0), None)
    declining_pockets = []
    for block in brief.get('secondary_shifts', []) or []:
        for row in block.get('rows', [])[:6]:
            if float(row.get('delta', 0)) < 0:
                name = str(row.get(block.get('dimension','dimension'), ''))
                pct = row.get('change_pct')
                declining_pockets.append((name, block.get('dimension','dimension'), float(pct) if pd.notna(pct) else None))
    declining_pockets = sorted(declining_pockets, key=lambda x: x[2] if x[2] is not None else 0)
    pocket_text = ''
    if declining_pockets:
        names = [x[0] for x in declining_pockets[:2] if x[0]]
        if names:
            pocket_text = ' Prioritize ' + ' and '.join(names) + ' in the detailed drill-down.'
    if lead_name and sla:
        brief['solution_direction'] = (
            f'Prioritize service recovery in {lead_name}: identify what drove the SLA deterioration, then drill into product, customer segment and channel to target the corrective action.'
            + pocket_text
            + ' Validate the customer-level cancellation relationship before treating retention improvement as a proven outcome.'
        )
    elif lead_name:
        brief['solution_direction'] = (
            f'Focus the next intervention on {lead_name}: quantify the largest product, segment and channel contributors, validate the operational explanation, and pilot the corrective action before broad rollout.'
            + pocket_text
        )
    else:
        brief['solution_direction'] = 'Use the measured performance change to identify the highest-impact business area, validate its operational or commercial contributor, and pilot a targeted corrective action before broad rollout.'
    brief['next_step']='Trace the focus area into service performance, product/segment/channel mix and customer outcomes, then confirm the explanation with the accountable owner.'
    return brief


def decision_recommendations(df, signals, investigations, objective='', evidence_register=None):
    """Produce a small set of decision-ready recommendations, grouped around a
    coherent solution rather than generating one recommendation per chart."""
    from .evidence import find_evidence_for_text
    brief=investigation_brief(df,signals,objective)
    recs=[]
    def add(rec_type,priority,title,why,action,owner,success,confidence,dependencies='',risks='',decision_required=None,evidence_text=None):
        recs.append({'id':f'REC-{len(recs)+1:03d}','type':rec_type,'priority':priority,'title':title,'why':why,
                     'action':action,'owner':'Not specified - confirmation required','suggested_owner':owner,'owner_status':'Requires stakeholder confirmation',
                     'success':success,'confidence':confidence,
                     'dependencies':dependencies or 'Confirm owner, source data and implementation constraints.',
                     'risks':risks or 'Do not implement a broad intervention until the leading driver is validated.',
                     'decision_required':decision_required or ('Approve the intervention.' if rec_type=='ACTION' else 'Approve the investigation scope and owner.'),
                     '_evidence_text': evidence_text or why})
    metric=brief.get('metric'); lead=brief.get('lead_group'); hyps=brief.get('hypotheses',[])
    sla=next((h for h in hyps if h.get('kind')=='sla'),None)
    if sla and lead:
        add('INVESTIGATION','High',f'Validate the South service-performance issue' if str(lead)=='South' else f'Validate service performance in {lead}',
            f'{brief.get("executive_finding", sla["hypothesis"])}',
            ['Review delivery/SLA breaches for the affected period and identify the operational step where performance deteriorated.',
             'Break the issue down by product, customer segment and channel to identify the highest-impact pockets.',
             'Assign an Operations owner, set a review date and agree the corrective action only after the breach pattern is explained.'],
            'Operations / regional performance owner',
            'The operational cause is validated, an owner is assigned, and a measurable service-recovery target is agreed.',
            sla['confidence'],
            dependencies='Period-aligned delivery/SLA detail, operational owner and consistent reporting definitions.',
            risks='SLA deterioration is a strong signal but does not by itself prove it caused the revenue or retention outcome.',
            decision_required='Approve the focused service-performance investigation and accountable owner.')
    # Consolidate product/segment/channel declines into one commercial focus recommendation.
    sec=brief.get('secondary_shifts',[])
    focus_items=[]
    for block in sec:
        for row in block.get('rows',[]):
            if float(row.get('delta',0)) < 0:
                focus_items.append((block['dimension'],str(row[block['dimension']]),float(row.get('change_pct',0))))
    if focus_items and len(recs)<3:
        focus_items=sorted(focus_items,key=lambda x:x[2])[:4]
        labels=[f'{n} ({d.lower()})' for d,n,_ in focus_items[:3]]
        add('INVESTIGATION','High','Prioritize the declining commercial pockets',
            'The focus area contains multiple product, segment or channel declines; these are contribution signals, not confirmed causes.',
            ['Quantify which declining pockets account for the largest revenue loss in the focus area.',
             'Check each pocket against SLA/service performance and customer outcomes to distinguish operational issues from demand or mix effects.',
             'Select targeted actions only after the leading explanation is validated.'],
            'Sales + Product + Customer Success',
            'The largest declining pockets have a validated explanation, owner and targeted response.',
            'Moderate signal',
            dependencies='Product/segment/channel detail and period-aligned operational evidence.',
            risks='A decline in a product or segment does not establish why it declined.',
            decision_required='Approve targeted analysis of the highest-impact declining pockets.')
    cancel_h=next((h for h in hyps if h.get('kind')=='cancellation'),None)
    if cancel_h:
        add('DATA VALIDATION','High','Close the customer-level retention evidence gap',
            cancel_h['hypothesis'],
            ['Obtain cancellation reason and customer-level cancellation data.',
             'Link SLA breaches and support events to the same customer and order where possible.',
             'Re-test the retention hypothesis before using cancellation reduction as a success target.'],
            'Customer Success + Analytics',
            'The service-to-cancellation relationship is validated or rejected with traceable customer evidence.',
            cancel_h['confidence'],
            dependencies='Customer-level cancellation reasons, SLA breach events and consistent customer/order keys.',
            risks='The current dataset contains too little cancellation evidence to support a causal conclusion.',
            decision_required='Approve the data request and owner for retention validation.')
    if not recs and metric:
        add('INVESTIGATION','High',f'Investigate the {lead or "primary performance area"}',
            'The dataset shows a measurable performance change, but the business driver is not established.',
            ['Compare the focus area with the prior period and other groups.', 'Break the change down by available commercial and operational dimensions.', 'Confirm the explanation with the accountable owner before intervention.'],
            'Business / performance owner','A validated driver, accountable owner and measurable action.','Moderate signal')
    # Keep recommendations tightly focused on distinct decision paths. Generic
    # risk-management advice is intentionally excluded from the final set.
    register=evidence_register or []
    for r in recs:
        text=r.pop('_evidence_text',r['why'])
        matches=find_evidence_for_text(register,text,limit=3) if register else []
        r['evidence_ids']=[m['evidence_id'] for m in matches]
    return recs[:4]


def workspace_journey(artifacts, ctx, investigations, recommendations):
    n_hyp = sum(len(i.get('hypotheses', [])) for i in (investigations or [])) if investigations else 0
    inv_status = f'{n_hyp} hypothesis{"es" if n_hyp!=1 else ""} awaiting validation' if investigations else ('Ready to investigate' if recommendations else 'Not started')
    rec_status = f'{len(recommendations)} available' if recommendations else 'Ready after investigation'
    return [
      ('Understand', 'Business Context', 'Built' if ctx else 'Not started', bool(ctx)),
      ('Analyse', 'Insights', 'Available' if any(a.get('kind')=='dataset' for a in artifacts) else 'No dataset connected', any(a.get('kind')=='dataset' for a in artifacts)),
      ('Investigate', 'Root Causes', inv_status, bool(investigations)),
      ('Decide', 'Recommendations', rec_status, bool(recommendations)),
      ('Deliver', 'BA Documents', 'Ready to download', True),
    ]


def next_best_action(artifacts, ctx, investigations, recommendations, df):
    """A single, concrete 'what should I do next' - not a status checklist.
    Chosen by where the workspace actually is, in the same UNDERSTAND ->
    INVESTIGATE -> DECIDE -> DELIVER order the rest of the app follows."""
    if not artifacts:
        return {'title': 'Connect business evidence to begin.', 'why': 'No dataset or document has been uploaded yet.', 'answers': 'What the workspace can tell you once evidence is connected.', 'button': 'Upload evidence', 'page': None}
    if df is None:
        return {'title': 'Add a structured dataset if one exists.', 'why': 'Only documents are connected so far - a dataset unlocks quantitative findings and driver analysis.', 'answers': 'Whether the documented concerns show up in the actual numbers.', 'button': 'Add a dataset', 'page': None}
    if not investigations:
        top = (ctx or {}).get('data_findings') or []
        subject = 'the highest-impact pattern in the connected data'
        return {'title': f'Investigate {subject}.', 'why': 'A measurable pattern is visible in the data, but its cause has not yet been established.', 'answers': 'Which candidate driver (volume, segment, time, or a document-supported hypothesis) actually explains the pattern.', 'button': 'Investigate now', 'page': 'pages/3_Investigation.py'}
    if not recommendations:
        return {'title': 'Review findings and generate recommendations.', 'why': 'An investigation has been saved but has not yet been turned into evidence-backed next steps.', 'answers': 'What the business should do, given the current evidence and confidence level.', 'button': 'Go to Recommendations', 'page': 'pages/6_Recommendations.py'}
    return {'title': 'Generate the relevant BA deliverable.', 'why': 'Investigation and recommendations are in place - the analysis is ready to be formalized.', 'answers': 'How to document and hand off the decision.', 'button': 'Go to Studio', 'page': 'pages/7_Deliverables.py'}
