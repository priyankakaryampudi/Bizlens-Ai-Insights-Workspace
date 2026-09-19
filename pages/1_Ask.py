import streamlit as st
from src.styles import hero, section_head
from src.ai import routed_answer, ai_provider, classify_question, classify_intent, ai_status
from src.intelligence import build_evidence_graph

hero('ASK','Ask BizLens','BizLens routes each question to the right evidence: Python for calculations, documents for business evidence, and synthesis only where interpretation is needed.')
if not st.session_state.artifacts: st.info('Upload business evidence on Home first.'); st.stop()
st.session_state.evidence_graph=build_evidence_graph(st.session_state.artifacts,st.session_state.df,st.session_state.doc_signals,st.session_state.get('business_objective',''))
section_head('Ask a business question', 'Get an evidence-grounded answer from the connected workspace.')

q=st.text_area('Your question',placeholder='Ask about performance, requirements, risks, stakeholders, investigations or recommendations.',height=105,key='ask_question')
status=ai_status()
st.caption(f"Answer engine: Python calculations + workspace evidence. AI synthesis: {status['provider']+' (falls back to local evidence automatically if unavailable)' if status['configured'] else 'not configured (safe local mode active)'}.")
if q.strip(): st.caption('Question type: '+classify_intent(q,st.session_state.df,st.session_state.doc_signals).replace('_',' ').title()+'  ·  Route: '+classify_question(q,st.session_state.df,st.session_state.doc_signals).replace('_',' ').title())
if st.button('Ask BizLens',type='primary',disabled=not q.strip(),width='stretch'):
    with st.spinner('Checking the connected evidence...'):
        ans=routed_answer(q.strip(),st.session_state.artifacts,st.session_state.df,st.session_state.doc_signals,st.session_state.get('business_objective',''),st.session_state.get('investigations',[]),st.session_state.get('recommendations_v2',[]))
    st.session_state.last_answer=ans; st.session_state.chat.append({'question':q.strip(),'answer':ans})
if st.session_state.get('last_answer'):
    section_head('Answer')
    st.markdown(st.session_state.last_answer)
    st.markdown('<div class="evidence-used"><b>Evidence boundary</b><br>Calculated facts and documented statements are separated from hypotheses. Association is not proof of causation.</div>', unsafe_allow_html=True)
    if st.session_state.get('evidence_register'):
        matched = []
        qtext = st.session_state.chat[-1]['question'] if st.session_state.chat else ''
        for item in st.session_state.evidence_register[:8]:
            if item.get('evidence_id') and item['evidence_id'] not in matched:
                matched.append(item['evidence_id'])
        if matched:
            st.markdown('<div class="evidence-used"><b>Workspace evidence available</b><br>' + ' '.join(f'<span class="pill">{x}</span>' for x in matched[:6]) + '</div>', unsafe_allow_html=True)
if st.session_state.chat:
    with st.expander('Recent workspace questions'):
        for x in reversed(st.session_state.chat[-5:]): st.markdown(f'**Q:** {x["question"]}\n\n{x["answer"]}')
