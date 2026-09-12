import streamlit as st
import pandas as pd
import plotly.express as px
from src.styles import hero, section_head
from src.intelligence import investigation_brief
from src.evidence import find_evidence_for_text

hero('INVESTIGATE','Find the driver, not just the chart.','Turn the observed business problem into a focused investigation: where is the change, what business signal moves with it, and what evidence is still needed before acting.')
if st.session_state.df is None and not st.session_state.doc_signals:
    st.info('Upload business evidence first.'); st.stop()

brief=investigation_brief(st.session_state.df,st.session_state.doc_signals,st.session_state.get('business_objective',''))
st.session_state.analysis['current_investigation']=brief

section_head('Problem to investigate')
st.markdown(f'<div class="finding big-answer"><b>{brief["problem"]}</b></div>',unsafe_allow_html=True)

section_head('Executive investigation finding')
st.markdown(f'<div class="answer-card"><div class="answer-head">{brief.get("executive_finding", "No executive finding is available yet.")}</div><div class="solution-strip"><b>What this means:</b> The evidence identifies the strongest area to investigate, but the underlying cause still needs validation.</div></div>',unsafe_allow_html=True)

section_head('What the evidence says')
for e in brief.get('evidence',[]) or ['No quantitative observation is available yet.']:
    st.markdown(f'<div class="finding">✓ {e}</div>',unsafe_allow_html=True)

# Executive signal card: make the business implication obvious before the details.
if brief.get('hypotheses'):
    lead=brief['hypotheses'][0]
    st.markdown(f'<div class="insight-card"><div class="eyebrow">Leading signal</div><b>{lead["hypothesis"]}</b><div class="muted" style="margin-top:.35rem">{lead.get("confidence","")}</div></div>',unsafe_allow_html=True)

if brief.get('contributors'):
    section_head('Where the change is concentrated','This ranks groups by period change, so the investigation starts with deterioration rather than simply the largest business unit.')
    g=pd.DataFrame(brief['contributors'])
    if 'change_pct' in g.columns:
        plot=g.dropna(subset=['change_pct']).copy()
        if not plot.empty:
            fig=px.bar(plot.sort_values('change_pct'),x='change_pct',y='group',orientation='h',title=f'{brief["metric"]}: change by {brief["dimension"]}')
            fig.update_layout(template='plotly_white',height=330,margin=dict(l=20,r=20,t=55,b=20),xaxis_title='Change (%)',yaxis_title='')
            st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})

section_head('Operational signals to validate')
operational=[h for h in brief.get('hypotheses',[]) if h.get('kind') in ('sla','tickets')]
if operational:
    for h in operational:
        label='Service performance' if h.get('kind')=='sla' else 'Customer/service pressure'
        st.markdown(f'<div class="finding"><b>{label}</b><br>{h["hypothesis"]}<br><span class="muted">{h.get("confidence","")}</span></div>',unsafe_allow_html=True)
else:
    st.caption('No additional operational signal could be calculated from the connected fields.')

section_head('What may be contributing','These are evidence-backed hypotheses or contribution signals, not confirmed causes. Each validation plan states the next evidence needed to support or reject the hypothesis.')
hyps=brief.get('hypotheses',[])
if not hyps:
    st.markdown('<div class="finding">No defensible hypothesis has been formed from the current evidence. Add a more detailed operational or customer dataset.</div>',unsafe_allow_html=True)
for h in hyps:
    matched=find_evidence_for_text(st.session_state.get('evidence_register',[]), h.get('hypothesis',''), limit=3)
    evidence_ids=', '.join(e.get('evidence_id','') for e in matched if e.get('evidence_id'))
    evidence_caption=('Traceable evidence: ' + evidence_ids) if evidence_ids else 'Evidence link: additional source evidence required'
    st.markdown(f'<div class="finding"><b>{h.get("id","")} — {h["hypothesis"]}</b><br><span class="muted">{h.get("status","")} · {h.get("confidence","")}</span><br><small>{evidence_caption}</small></div>',unsafe_allow_html=True)
    steps=h.get('validation') or []
    if steps:
        with st.expander(f'Validation plan — {h.get("id","this hypothesis")}'):
            for i,step in enumerate(steps,1):
                if str(step).strip(): st.markdown(f'{i}. {step}')

section_head('Candidate business signals','Only signals supported by the connected data are shown. A focus area or contribution signal is not presented as a root cause.')
drivers=brief.get('drivers',[])
if drivers:
    ddf=pd.DataFrame(drivers)[['driver','category','relationship','confidence']].rename(columns={'driver':'Driver','category':'Signal type','relationship':'What the data shows','confidence':'Assessment'})
    st.dataframe(ddf,width='stretch',hide_index=True)
else:
    st.info('No candidate driver can be tested with the current schema.')

section_head('Root-cause status')
rc=brief.get('root_cause',{})
cols=st.columns(5)
for col,(label,count) in zip(cols,rc.items()):
    with col: col.metric(label,count)
if rc.get('Confirmed',0)==0 and rc.get('Strongly supported',0)==0:
    st.caption('No root cause is confirmed. The app is deliberately stopping short of calling an observed pattern a cause.')

section_head('Investigation conclusion')
conc=brief.get('conclusion',{})
if conc:
    st.markdown(f'<div class="finding"><b>Established</b><br>{conc["established"]}<br><br><b>Not established</b><br>{conc["not_established"]}<br><br><b>Strongest signal</b><br>{conc["most_credible"]}<br><br><b>Evidence still required</b><br>{conc["evidence_required"]}<br><br><b>Next investigation</b><br>{conc["next_investigation"]}</div>',unsafe_allow_html=True)

section_head('What to do next')
st.info(brief['next_step'])
if st.button('Save this investigation to the workspace',type='primary',width='stretch'):
    record={'focus':brief.get('problem'),'signal':' | '.join(brief.get('evidence',[])[:4]),'hypotheses':[h['hypothesis'] for h in brief.get('hypotheses',[])],'brief':brief}
    existing=st.session_state.get('investigations',[])
    if not any(x.get('focus')==record['focus'] for x in existing): existing.append(record)
    st.session_state.investigations=existing
    from src.workspace import refresh_workspace
    refresh_workspace()
    st.success('Investigation saved. Recommendations and BA Studio can reuse it.')
