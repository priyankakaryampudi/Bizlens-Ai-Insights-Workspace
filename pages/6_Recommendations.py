import streamlit as st
from src.styles import hero, section_head
from src.intelligence import decision_recommendations
from src.workspace import refresh_workspace

hero('DECIDE','Recommendations that lead to action','BizLens converts the investigation into a decision path: what management should validate now, what can be acted on, what evidence is missing, and how success will be measured.')
recs=decision_recommendations(st.session_state.df,st.session_state.doc_signals,st.session_state.get('investigations',[]),st.session_state.get('business_objective',''),st.session_state.get('evidence_register',[]))
st.session_state.recommendations_v2=recs; refresh_workspace()
if not recs: st.info('Connect evidence first so BizLens can produce grounded recommendations.'); st.stop()

section_head('Recommended solution direction')
primary=recs[0]
all_actions=[]
for r in recs:
    all_actions.extend(r.get('action',[])[:1])
solution_steps=''.join(f'<li>{x}</li>' for x in all_actions[:4])
st.markdown(f'<div class="answer-card"><div class="answer-head">{primary["title"]}</div><div class="answer-body"><b>Why:</b> {primary["why"]}<br><br><b>Recommended path</b><ol>{solution_steps}</ol><b>Success looks like:</b> {primary["success"]}</div></div>',unsafe_allow_html=True)

section_head('Decision priorities','A small set of actions and validations, ordered around one coherent solution path.')
st.markdown('<div class="validation-card"><b>How BizLens prioritizes</b><br>Priority is an analytical trigger based on magnitude, movement, concentration, data quality and evidence strength. These thresholds help surface what deserves attention; they are <b>not business-approved targets and do not prove causation</b>.</div>',unsafe_allow_html=True)
for r in recs:
    with st.container(border=True):
        st.markdown(f'### {r.get("id","")} — {r["title"]}')
        st.caption(f'{r.get("type","")} · {r["priority"]} priority · {r["confidence"]}')
        st.markdown(f'**What we observed**  \n{r["why"]}')
        st.markdown('**Recommended action**')
        for n,step in enumerate(r['action'],1): st.markdown(f'{n}. {step}')
        a,b=st.columns(2)
        with a: st.markdown(f'**Owner**  \n{r["owner"]}<br><small>Suggested function: {r.get("suggested_owner","Not specified")} · {r.get("owner_status","Requires confirmation")}</small>',unsafe_allow_html=True)
        with b: st.markdown(f'**Success measure**  \n{r["success"]}')
        c,d=st.columns(2)
        with c: st.markdown(f'**Dependencies**  \n{r.get("dependencies","")}')
        with d: st.markdown(f'**Risk / boundary**  \n{r.get("risks","")}')
        st.markdown(f'**Decision required**  \n{r.get("decision_required","")}')
        if r.get('evidence_ids'): st.caption('Traceable evidence: ' + ', '.join(r['evidence_ids']))

section_head('What management should NOT do yet')
st.markdown('<div class="validation-card"><b>Do not treat the leading signal as proven causation.</b><br>Do not make a broad pricing, retention or process change until the affected operational driver is validated and the customer-level cancellation evidence is available.</div>',unsafe_allow_html=True)

section_head('Decision boundary')
st.caption('Recommendations are evidence-based decision aids. Business owners still approve scope, ownership, intervention and success criteria.')
