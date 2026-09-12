import streamlit as st
import pandas as pd
from src.styles import hero, section_head
from src.doc_intel import build_context
from src.workspace_intelligence import build_workspace_context, ba_analysis_recommendations, recommended_next_steps

hero('UNDERSTAND','Business Context','A clean BA view of the business problem, the evidence, the requirements that shape the solution, and the decisions still needed.')
if not st.session_state.artifacts: st.info('Upload business evidence first.'); st.stop()
sig,flags,_=build_context(st.session_state.artifacts); st.session_state.doc_signals=sig
ctx=build_workspace_context(st.session_state.artifacts,st.session_state.datasets,sig,st.session_state.get('business_objective',''),flags); st.session_state.workspace_summary=ctx

n_docs=sum(a.get('kind')=='document' for a in st.session_state.artifacts); n_sets=len(st.session_state.datasets)
n_evidence=sum(len(v) for v in sig.values() if isinstance(v,list))
status='Validation needed' if ctx.get('contradiction') else ('Investigation in progress' if st.session_state.get('investigations') else 'Evidence ready')
st.caption(f'{n_docs} business document{"s" if n_docs!=1 else ""} · {n_sets} dataset{"s" if n_sets!=1 else ""} · {n_evidence} extracted evidence items · Status: **{status}**')

section_head('Executive business situation')
pa=ctx.get('primary_analysis',{}); ch=pa.get('period_change'); lead=pa.get('lead_decline') or {}
if ch:
    direction='increased' if ch['change_pct']>=0 else 'declined'
    st.markdown(f'<div class="answer-card"><div class="answer-head">{pa.get("metric","The primary KPI")} {direction} {abs(ch["change_pct"]):.1f}% from {ch["previous_label"]} to {ch["current_label"]}.</div><div class="answer-body">{(str(lead.get(pa.get("dimension"),"The affected area")) + " is the clearest deterioration point. " if lead and float(lead.get("delta",0))<0 else "The data shows a measurable performance change. ")}The investigation should now trace that change into service performance and product, customer-segment and channel mix.</div></div>',unsafe_allow_html=True)
else:
    st.markdown('<div class="finding">The connected documents define the business problem, but the current data is not sufficient for a period-aligned performance conclusion.</div>',unsafe_allow_html=True)
if ctx.get('contradiction'):
    st.markdown(f'<div class="validation-card"><b>Validation note</b><br>{ctx["contradiction"]}</div>',unsafe_allow_html=True)

section_head('Business objective')
a,b=st.columns(2)
with a:
    st.markdown('**Working objective**'); st.markdown(ctx.get('objective_stated') or ctx.get('objective_derived') or 'Clarify the business objective from the connected evidence.')
with b:
    st.markdown('**Objective status**'); st.markdown('User-defined' if ctx.get('objective_stated') else 'Evidence-derived from the business case')

section_head('Business drivers & pain points')
# Use evidence-derived signals when a structured dataset is available; keep generic
# document themes only as a fallback.
brief = None
if st.session_state.df is not None:
    from src.intelligence import investigation_brief
    brief = investigation_brief(st.session_state.df, sig, st.session_state.get('business_objective',''))
if brief and brief.get('metric'):
    ch = brief.get('period_change') or {}
    if ch:
        direction = 'increased' if ch.get('change_pct', 0) >= 0 else 'declined'
        st.markdown(f'• **Primary performance movement:** {brief["metric"]} {direction} {abs(ch.get("change_pct", 0)):.1f}% from {ch.get("previous_label", "the prior period")} to {ch.get("current_label", "the latest period")}.')
    if brief.get('lead_group') and brief.get('lead_change_pct') is not None and brief.get('lead_delta', 0) < 0:
        st.markdown(f'• **Concentration:** {brief["lead_group"]} is the priority area and declined {abs(brief["lead_change_pct"]):.1f}% in the aligned comparison.')
    sla = next((x for x in brief.get('service_signals',[]) if x.get('kind')=='sla' and x.get('delta',0)<0), None)
    if sla and brief.get('lead_group'):
        st.markdown(f'• **Operational pressure:** SLA in {brief["lead_group"]} fell from {sla["previous"]*100:.1f}% to {sla["current"]*100:.1f}% ({abs(sla["delta"])*100:.1f} percentage-point deterioration).')
    tickets = next((x for x in brief.get('service_signals',[]) if x.get('kind')=='tickets' and x.get('delta',0)>0), None)
    if tickets and brief.get('lead_group'):
        pct = ((tickets['current']/tickets['previous'])-1)*100 if tickets.get('previous') else None
        st.markdown(f'• **Customer/service pressure:** Support-ticket pressure in {brief["lead_group"]} increased{f" {pct:.1f}%" if pct is not None else ""} to {tickets["current"]:.3f} per order.')
    declines=[]
    for block in brief.get('secondary_shifts',[]) or []:
        for row in block.get('rows',[])[:6]:
            if float(row.get('delta',0)) < 0:
                name=str(row.get(block.get('dimension','dimension'),'')); pct=row.get('change_pct')
                declines.append((name,block.get('dimension','dimension'),float(pct) if pd.notna(pct) else None))
    declines=sorted(declines,key=lambda x:x[2] if x[2] is not None else 0)
    if declines:
        labels=[]
        for name,dimension,pct in declines[:3]:
            labels.append(f'{name} ({abs(pct):.1f}% down)' if pct is not None else name)
        st.markdown('• **Commercial pockets requiring drill-down:** ' + ', '.join(labels) + '.')
else:
    for p in (ctx.get('problems') or ['No specific business driver has been established from the connected evidence.']):
        st.markdown(f'• {p.capitalize()}')

section_head('Business impact')
pa=ctx.get('primary_analysis',{})
impact=[]
if pa.get('period_change'):
    ch=pa['period_change']; direction='increased' if ch['change_pct'] >= 0 else 'declined'
    impact.append(f'{pa.get("metric","Primary KPI")} {direction} {abs(ch["change_pct"]):.1f}% from {ch["previous_label"]} to {ch["current_label"]}.')
focus=pa.get('focus_decline') or {}
if focus and float(focus.get('delta',0)) < 0:
    impact.append(f'{focus.get(pa.get("dimension"),"The focus area")} is the business focus and also deteriorated in the aligned period.')
for ss in pa.get('service_signals',[]) or []:
    if ss.get('kind')=='sla' and ss.get('delta',0)<0:
        impact.append(f'Service performance in the focus area fell by {abs(ss["delta"])*100:.1f} percentage points.')
    elif ss.get('kind')=='tickets' and ss.get('delta',0)>0:
        impact.append('Support-ticket pressure increased in the focus area.')
if impact:
    st.markdown('<div class="finding">' + '<br>'.join('• '+x for x in impact) + '</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="finding">Business impact cannot yet be quantified from the connected evidence.</div>', unsafe_allow_html=True)

section_head('Solution direction')
solution_text = brief.get('solution_direction') if brief else None
solution_text = solution_text or 'Use the observed performance change to focus the investigation, validate the strongest operational signal, then target the affected product, segment or channel before making a broad intervention.'
st.markdown(f'<div class="answer-card"><div class="answer-head">Recommended solution path</div><div class="answer-body">{solution_text}</div></div>', unsafe_allow_html=True)

section_head('Evidence & key findings')
k1,k2=st.columns(2)
with k1:
    st.markdown('**Observed in the connected data**')
    findings=ctx.get('data_findings') or []
    if findings:
        for f in findings[:5]:
            if f.get('change_pct') is not None:
                direction='up' if f['change_pct']>=0 else 'down'
                st.markdown(f'✓ {f["metric"]}: {direction} {abs(f["change_pct"]):.1f}% ({f.get("period", "aligned period")})')
            else:
                st.markdown(f'✓ {f["metric"]}: {f["value"]:,.0f} total')
    else: st.markdown('No quantitative observation is available yet.')
with k2:
    st.markdown('**Open business questions**')
    for x in (ctx.get('questions') or [])[:5] or ['No open question has been recorded yet.']:
        st.markdown(f'? {x}')

section_head('Requirements that shape the solution','Only explicit system, interface, analysis and output requirements are shown here. Business discussion points are kept out of this table.')
req_table=ctx.get('requirements_table',[])
if req_table:
    rdf=pd.DataFrame(req_table)[['id','need','category','priority']].rename(columns={'id':'ID','need':'Requirement','category':'Type','priority':'Priority'})
    st.dataframe(rdf,width='stretch',hide_index=True)
    st.caption('Source: connected requirements evidence · Status: Draft pending business confirmation')
else:
    st.info('No explicit solution requirement was extracted from the connected documents.')

left,right=st.columns(2)
with left:
    section_head('Stakeholders')
    st_table=ctx.get('stakeholder_table',[])
    if st_table:
        for s in st_table:
            st.markdown(f'• **{s["stakeholder"]}** — decision role and ownership still need confirmation.')
    else: st.markdown('No stakeholder group was explicitly named.')
    section_head('Decisions required')
    for d in ctx.get('decisions_table',[]) or []:
        st.markdown(f'• {d["decision"]}<br><span class="muted">{d["status"]}</span>',unsafe_allow_html=True)
with right:
    section_head('Risks & issues')
    rc=ctx.get('risk_categories',{})
    items=[]
    for key in ['known_risks','known_issues','potential_risks']: items += rc.get(key,[])
    for x in items[:6]: st.markdown(f'• {x}')
    if not items: st.markdown('No explicit risk or issue was confirmed in the connected evidence.')
    section_head('Open questions')
    for q in ctx.get('questions_grouped',[])[:6]:
        st.markdown(f'• **{q["priority"]}** — {q["question"]}')

section_head('Gaps that block a confident solution')
gaps=ctx.get('gaps',{})
for key,label in [('business','Business'),('data','Data'),('requirement','Requirement')]:
    items=gaps.get(key,[])
    if items:
        st.markdown(f'**{label} gaps**')
        for g in items:
            st.markdown(f'<div class="finding"><b>{g["gap"]}</b><br>{g["why"]}<br><span class="muted">Resolution: {g["resolution"]}</span></div>',unsafe_allow_html=True)

section_head('Recommended BA analysis')
for t in ba_analysis_recommendations(ctx):
    st.markdown(f'<div class="finding"><b>{t["technique"]}</b> · {t["status"]}<br><span class="muted">Why: {t["why"]} · Evidence: {t["evidence"]}</span></div>',unsafe_allow_html=True)

section_head('Recommended next steps')
for i,s in enumerate(recommended_next_steps(ctx,st.session_state.df is not None,bool(st.session_state.get('investigations')),bool(st.session_state.get('recommendations_v2'))),1):
    st.markdown(f'{i}. {s}')
