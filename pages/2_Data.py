import streamlit as st
import pandas as pd
import plotly.express as px
from src.styles import hero, section_head
from src.analytics import *
from src.workspace import refresh_workspace
from src.ai import answer

hero('UNDERSTAND','Data & Insights','BizLens profiles the active dataset and builds the useful dashboard automatically. No chart configuration is required.')
df=st.session_state.df
if df is None: st.info('Upload a structured dataset first.'); st.stop()
obj=st.session_state.get('business_objective','')
metric,dim,date=guess_metric(df,obj) or 'Record count',guess_dimension(df,obj),guess_date(df)
section_head('Executive dashboard')
items=business_kpis(df,metric,dim,date); cols=st.columns(len(items))
for col,item in zip(cols,items): col.metric(item['label'],item['value'],item['detail'])
section_head('What matters most','The dashboard surfaces measurable movement; the Investigation page is where candidate drivers are tested.')
st.info('Comparison note: the executive business case follows the period defined by the connected business evidence (for this demo, Q3→Q4). The dashboard also shows the latest comparable dataset periods (for example, Nov→Dec). These are different analytical views, so they should not be read as contradictory.')
try:
    from src.analytics import aligned_period_change, group_period_change, service_signal
    aligned = aligned_period_change(df, date, metric, st.session_state.get('business_objective','')) if date else None
    context = ' '.join(str(v) for v in st.session_state.get('doc_signals',{}).values())
    shifts = group_period_change(df,date,metric,dim,context_text=context) if date and dim else pd.DataFrame()
    preferred = next((str(v) for v in df[dim].dropna().unique() if str(v).lower() in context.lower()), None) if dim else None
    focus = shifts[shifts[dim].astype(str)==preferred].iloc[0] if preferred and not shifts.empty and any(shifts[dim].astype(str)==preferred) else (shifts.iloc[0] if not shifts.empty else None)
    if aligned:
        st.markdown(f'<div class="finding"><b>Performance movement:</b> {metric} {"declined" if aligned["change_pct"]<0 else "increased"} {abs(aligned["change_pct"]):.1f}% from {aligned["previous_label"]} to {aligned["current_label"]}.</div>',unsafe_allow_html=True)
    if focus is not None and float(focus.get('delta',0)) < 0:
        st.markdown(f'<div class="finding"><b>Priority area:</b> {focus[dim]} declined {abs(float(focus["change_pct"])):.1f}% in the same comparison period.</div>',unsafe_allow_html=True)
    for ss in (service_signal(df,date,metric,dim,str(focus[dim]),context) if focus is not None else []):
        if ss.get('kind')=='sla' and ss.get('delta',0)<0:
            st.markdown(f'<div class="finding"><b>Operational signal:</b> SLA moved from {ss["previous"]*100:.1f}% to {ss["current"]*100:.1f}% in {focus[dim]}.</div>',unsafe_allow_html=True)
    if not aligned and focus is None:
        for f in auto_insights(df,metric,dim,date)[:4]: st.markdown(f'<div class="finding">{f}</div>',unsafe_allow_html=True)
except Exception:
    for f in auto_insights(df,metric,dim,date)[:4]: st.markdown(f'<div class="finding">{f}</div>',unsafe_allow_html=True)

def show(fig,collect_title=None):
 fig.update_layout(template='plotly_white',paper_bgcolor='#FFFDF8',plot_bgcolor='#FFFDF8',height=370,margin=dict(l=20,r=20,t=55,b=25)); st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})
 if collect_title: st.session_state.setdefault('_dashboard_figs',[]).append((collect_title,fig))

st.session_state['_dashboard_figs']=[]

section_head('Business dashboard')
if date:
 try:
  t=trend(df,date,metric)
  if len(t)>=2: show(px.line(t,x=date,y=metric,markers=True,title=f'{metric} trend'),f'{metric} trend')
 except Exception as e: st.caption('Trend unavailable for the current date field.')
if dim:
 g=dimension_breakdown(df,dim,metric,10)
 if not g.empty:
  a,b=st.columns(2)
  with a: show(px.bar(g.sort_values('total'),x='total',y=dim,orientation='h',title=f'{metric} by {dim}'),f'{metric} by {dim}')
  with b: show(px.pie(g.head(6),names=dim,values='total',hole=.58,title=f'{metric} contribution mix'),f'{metric} contribution mix')
a,b=st.columns(2)
with a:
 try: show(px.histogram(distribution(df,metric),x='value',nbins=30,title=f'{metric} distribution'),f'{metric} distribution')
 except Exception: st.empty()
with b:
 # Prefer a business-operational view over a generic statistical relationship.
 op=None
 for c in ['SLA_Achievement_Rate','Support_Tickets','Cancellations']:
  if c in df.columns: op=c; break
 if op and date:
  try:
   t=trend(df,date,op)
   if len(t)>=2:
    show(px.line(t,x=date,y=op,markers=True,title=f'{op.replace("_"," ")} trend'),f'{op} trend')
  except Exception: st.empty()

section_head('Download this dashboard')
st.caption('One file with the KPIs, findings and charts above - opens in any browser.')
if st.button('Prepare dashboard download'):
    from src.dashboard_export import build_dashboard_html
    html=build_dashboard_html('BizLens Dashboard',items,auto_insights(df,metric,dim,date)[:6],st.session_state.get('_dashboard_figs',[]))
    st.session_state['_dashboard_html']=html
if st.session_state.get('_dashboard_html'):
    st.download_button('Download dashboard (HTML)',data=st.session_state['_dashboard_html'],file_name='bizlens_dashboard.html',mime='text/html')

section_head('Data quality watch')
qa=quality_actions(df)
if qa:
 for q in qa[:6]: st.markdown(f'<div class="finding"><b>{q["issue"]}</b> · {q["count"]:,}<br><span class="muted">{q["treatment"]}</span></div>',unsafe_allow_html=True)
else: st.success('No major automated data-quality issue was detected.')

section_head('Build a specific analysis')
custom=st.text_input('Describe the comparison or analysis you want',placeholder='Compare revenue by region')
st.caption('Type your own request above (the grey text is just an example) — the button activates once you do.')
if st.button('Build analysis',disabled=not custom.strip()):
 result,msg=custom_analysis_request(df,custom)
 st.session_state.custom_result=(result,msg)
if st.session_state.get('custom_result'):
 result,msg=st.session_state.custom_result; st.info(msg)
 if result and result.get('type')=='bar': show(px.bar(result['data'],x=result['x'],y=result['y'],title=result['title']))
 elif result and result.get('type')=='kpi': st.metric(result['metric'],f"{result['total']:,.2f}")

refresh_workspace()
section_head('Ask about these insights')
q=st.text_area('Specific follow-up',placeholder='Example: Which segment should management investigate first and why?',height=90)
if st.button('Ask about the analysis',disabled=not q.strip(),type='primary'):
 with st.spinner('Checking the connected evidence...'):
  st.session_state.data_answer=answer(q.strip(),st.session_state.artifacts,df,st.session_state.doc_signals)
if st.session_state.get('data_answer'): st.markdown(f'<div class="panel big-answer">{st.session_state.data_answer}</div>',unsafe_allow_html=True)
