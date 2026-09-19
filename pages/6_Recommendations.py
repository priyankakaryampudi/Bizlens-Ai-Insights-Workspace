import streamlit as st
from src.styles import hero, section_head
from src.intelligence import decision_recommendations
from src.workspace import refresh_workspace

hero(
    'DECIDE',
    'Recommendations that lead to action',
    'Convert the validated investigation into a small set of decision-ready actions, with owners, dependencies, success measures and explicit boundaries.'
)

recs = decision_recommendations(
    st.session_state.df,
    st.session_state.doc_signals,
    st.session_state.get('investigations', []),
    st.session_state.get('business_objective', ''),
    st.session_state.get('evidence_register', []),
)
st.session_state.recommendations_v2 = recs
refresh_workspace()
if not recs:
    st.info('Connect evidence first so BizLens can produce grounded recommendations.')
    st.stop()

section_head('Recommended direction', 'A concise action path derived from the investigation. The numbers stay in Data & Insights; this page focuses on what to do next.')
primary = recs[0]
all_actions = []
for r in recs:
    all_actions.extend(r.get('action', [])[:1])
solution_steps = ''.join(f'<li><b>{i:02d}</b> · {x}</li>' for i, x in enumerate(all_actions[:4], 1))
st.markdown(
    f'<div class="answer-card"><div class="answer-head">{primary["title"]}</div><div class="answer-body"><b>Why this path:</b> {primary["why"]}<br><br><b>Recommended path</b><ol>{solution_steps}</ol><b>Success looks like:</b> {primary["success"]}</div></div>',
    unsafe_allow_html=True,
)

section_head('Action plan', 'Each action has an owner, dependency, success measure and evidence boundary so the recommendation can move toward implementation.')
for r in recs:
    with st.container(border=True):
        st.markdown(f'### {r.get("id", "")} — {r["title"]}')
        st.caption(f'{r.get("type", "")} · {r["priority"]} priority · {r["confidence"]}')
        st.markdown(f'**What the investigation established**  \n{r["why"]}')
        st.markdown('**Recommended action**')
        for n, step in enumerate(r['action'], 1):
            st.markdown(f'{n}. {step}')
        a, b = st.columns(2)
        with a:
            st.markdown(
                f'**Owner**  \n{r["owner"]}<br><small>Suggested function: {r.get("suggested_owner", "Not specified")} · {r.get("owner_status", "Requires confirmation")}</small>',
                unsafe_allow_html=True,
            )
        with b:
            st.markdown(f'**Success measure**  \n{r["success"]}')
        c, d = st.columns(2)
        with c:
            st.markdown(f'**Dependencies**  \n{r.get("dependencies", "")}')
        with d:
            st.markdown(f'**Risk / boundary**  \n{r.get("risks", "")}')
        st.markdown(f'**Decision required**  \n{r.get("decision_required", "")}')
        if r.get('evidence_ids'):
            st.caption('Traceable evidence: ' + ', '.join(r['evidence_ids']))

section_head('Decision guardrails', 'Keep the intervention proportional to the evidence available today.')
st.markdown(
    '<div class="validation-card"><b>Validate before scaling.</b><br>'
    'Treat the leading signal as a reason to investigate and pilot, not as proof of causation. '
    'Use customer-level cancellation or outcome data before claiming a retention effect, and confirm accountable ownership before implementation.</div>',
    unsafe_allow_html=True,
)
