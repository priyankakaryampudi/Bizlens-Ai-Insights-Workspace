import streamlit as st
from src.styles import hero, section_head
from src.ui import process_uploaded_files, load_demo_workspace
from src.doc_intel import build_context
from src.workspace_intelligence import build_workspace_context, choose_techniques
from src.intelligence import build_evidence_graph, workspace_journey, next_best_action, investigation_brief
from src.analytics import guess_metric, guess_dimension, guess_date, auto_insights
from src.workspace import refresh_workspace
from src.evidence import find_evidence_for_text, source_line

hero('BIZLENS','Business Intelligence Workspace','Connect business evidence once. BizLens turns it into a clear business story: what changed, where it changed, what is most likely driving it, and what management should do next.')

st.markdown('<div class="stepbar"><span class="active">1 Understand</span><span>2 Analyse</span><span>3 Investigate</span><span>4 Decide</span><span>5 Deliver</span></div>',unsafe_allow_html=True)

is_empty=not st.session_state.artifacts
if is_empty:
    section_head('Start your workspace','Upload the dataset and business documents you already use. BizLens keeps them connected.')
else:
    section_head('Add more evidence to this workspace','Add another dataset or document at any time. New evidence is carried through the analysis.')
files=st.file_uploader('Add business evidence (data or documents)',type=['csv','xlsx','xls','docx','pdf','pptx','txt'],accept_multiple_files=True,key='uploader_main')
if files:
    if process_uploaded_files(files):
        st.success(f'Connected {len(files)} file{"s" if len(files)!=1 else ""} to your workspace.'); st.rerun()
if is_empty:
    if st.button('Try the complete demo workspace'):
        count=load_demo_workspace(); st.success(f'Connected {count} demo sources: data + meeting notes + requirements + review evidence.'); st.rerun()
    st.stop()

sig,flags,_=build_context(st.session_state.artifacts); st.session_state.doc_signals=sig
obj=st.session_state.get('business_objective','')
ctx=build_workspace_context(st.session_state.artifacts,st.session_state.datasets,sig,obj,flags)
st.session_state.workspace_summary=ctx
st.session_state.analysis['suggested_techniques']=choose_techniques(ctx)
st.session_state.evidence_graph=build_evidence_graph(st.session_state.artifacts,st.session_state.df,sig,obj)
refresh_workspace()
df=st.session_state.df
m=guess_metric(df,obj) if df is not None else None
d=guess_dimension(df,obj) if df is not None else None
dt=guess_date(df) if df is not None else None

section_head('What are we trying to understand?')
if obj:
    st.markdown(f'<div class="finding"><b>{obj}</b></div>',unsafe_allow_html=True); st.caption('Objective status: User-defined')
elif m and d:
    st.markdown(f'<div class="finding"><b>Explain the {m} change, identify where it is concentrated, and determine what business driver should be addressed.</b></div>',unsafe_allow_html=True)
    st.caption('Objective status: Evidence-derived starting point — confirm or refine it below')
else:
    st.markdown((ctx.get('objectives') or ['Clarify the business objective.'])[0]); st.caption('Objective status: Evidence-derived')
objective=st.text_area('Set or refine the objective',value=obj,placeholder='Example: Why did revenue weaken in Q4 and what should management do next?',height=80,label_visibility='collapsed')
if objective!=obj:
    st.session_state.business_objective=objective.strip(); refresh_workspace(); st.rerun()

section_head('Executive answer','A concise decision view — facts first, hypotheses second, action last.')
pa=ctx.get('primary_analysis',{})
change=pa.get('period_change'); lead=pa.get('focus_decline') or pa.get('lead_decline') or {}
if change and m:
    brief=investigation_brief(df,sig,obj)
    finding=brief.get('executive_finding','')
    solution=brief.get('solution_direction','')
    st.markdown(f'<div class="answer-card"><div class="answer-head">What the evidence currently says</div><div class="answer-body">{finding}</div><div class="solution-strip"><b>Solution direction:</b> {solution}</div></div>',unsafe_allow_html=True)
else:
    st.markdown('<div class="finding">The workspace has enough evidence to frame the problem, but not enough structured data to produce a quantified solution yet.</div>',unsafe_allow_html=True)

section_head('Current business situation')
if ctx.get('contradiction'):
    st.markdown(f'<div class="validation-card"><b>Validation needed</b><br>{ctx["contradiction"]}</div>',unsafe_allow_html=True)
st.markdown(f'<div class="finding">{ctx.get("narrative") or "The connected workspace combines structured data and business evidence."}</div>',unsafe_allow_html=True)

known=[]
if change and m:
    direction='increased' if change['change_pct']>=0 else 'declined'
    known.append(f'{m} {direction} {abs(change["change_pct"]):.1f}% from {change["previous_label"]} to {change["current_label"]}.')
if lead and float(lead.get('delta',0))<0:
    known.append(f'{lead.get(d,"The leading group")} is the priority business focus and deteriorated in the aligned comparison.')
for ss in (pa.get('service_signals') or []):
    if ss.get('kind')=='sla' and ss.get('delta',0)<0:
        known.append(f'Service-level performance in the affected area moved from {ss["previous"]*100:.1f}% to {ss["current"]*100:.1f}%.')
if not known:
    known=auto_insights(df,m,d,dt)[:3] if df is not None and m else []
uncertain=(sig.get('questions',[]) or [])[:4] or ['No open question has been recorded yet.']
register=st.session_state.get('evidence_register',[])
left,right=st.columns(2)
with left:
    section_head('What we know')
    for x in known[:5]:
        matches=find_evidence_for_text(register,x,limit=1)
        src=source_line(matches[0]) if matches else ('Source: connected dataset' if df is not None else 'Source: connected evidence')
        st.markdown(f'✓ {x}<br><span class="muted">{src}</span>',unsafe_allow_html=True)
with right:
    section_head('What remains uncertain')
    for x in uncertain: st.markdown(f'? {x}')

section_head('Needs attention','These are investigation triggers, not proof of cause.')
attention=[]
if ctx.get('contradiction'): attention.append(('🟠','Validate','Period or KPI mismatch',ctx['contradiction']))
if df is not None and m and d and not st.session_state.get('investigations'):
    attention.append(('🔴','High','Root cause not yet validated','The data identifies where the change is concentrated, but the operational or commercial cause still needs evidence.'))
if any('cancellation' in str(x).lower() for x in (sig.get('questions',[]) or [])):
    attention.append(('🟡','Medium','Retention evidence is incomplete','Cancellation questions are documented, but customer-level evidence is needed to test the service-to-cancellation link.'))
if flags:
    attention.append(('🟡','Medium','Requirement wording needs definition',flags[0]))
if not attention: st.markdown('Nothing urgent identified from the current evidence.')
else:
    for dot,level,title,why in attention[:3]: st.markdown(f'{dot} **{level} — {title}.** {why}')

section_head('Recommended next action','BizLens gives you one concrete next move instead of a checklist of generic tasks.')
action=next_best_action(st.session_state.artifacts,ctx,st.session_state.get('investigations',[]),st.session_state.get('recommendations_v2',[]),df)
st.markdown(f'<div class="action-card"><b>{action["title"]}</b><br><span class="muted">Why:</span> {action["why"]}<br><span class="muted">This will answer:</span> {action["answers"]}</div>',unsafe_allow_html=True)
if action.get('page'): st.page_link(action['page'],label=action['button'],width='stretch')

refresh_workspace()
section_head('Analysis progress')
cols=st.columns(5)
for col,(stage,label,status,done) in zip(cols,workspace_journey(st.session_state.artifacts,ctx,st.session_state.get('investigations',[]),st.session_state.get('recommendations_v2',[]))):
    with col:
        st.markdown(f"{'✓' if done else '○'} **{stage}**"); st.caption(f'{label} — {status}')

section_head('Quick actions')
x,y,z=st.columns(3)
with x: st.page_link('pages/1_Ask.py',label='Ask BizLens',width='stretch')
with y: st.page_link('pages/2_Data.py',label='Explore Data',width='stretch')
with z: st.page_link('pages/6_Recommendations.py',label='Review Recommendations',width='stretch')
with st.expander('Workspace health'):
    a,b,c,d2=st.columns(4)
    a.metric('Sources',len(st.session_state.artifacts)); b.metric('Datasets',len(st.session_state.datasets)); c.metric('Business documents',sum(x.get('kind')=='document' for x in st.session_state.artifacts)); d2.metric('Open questions',len(sig.get('questions',[])))
