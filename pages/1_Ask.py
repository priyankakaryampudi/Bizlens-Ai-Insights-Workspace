import streamlit as st
from src.styles import hero, section_head
from src.ai import routed_answer, ai_provider, classify_question, classify_intent, ai_status
from src.intelligence import build_evidence_graph

hero('ASK','Ask BizLens','BizLens routes each question to the right evidence: Python for calculations, documents for business evidence, and synthesis only where interpretation is needed.')
if not st.session_state.artifacts: st.info('Upload business evidence on Home first.'); st.stop()
st.session_state.evidence_graph=build_evidence_graph(st.session_state.artifacts,st.session_state.df,st.session_state.doc_signals,st.session_state.get('business_objective',''))
section_head('Ask a business question')
q=st.text_area('Your question',placeholder='Ask about performance, requirements, risks, stakeholders, investigations or recommendations.',height=110,key='ask_question')
status=ai_status()
st.caption(f"Answer engine: Python calculations + workspace evidence. AI synthesis: {status['provider']+' (falls back to local evidence automatically if unavailable)' if status['configured'] else 'not configured (safe local mode active)'}.")
if q.strip(): st.caption('Question type: '+classify_intent(q,st.session_state.df,st.session_state.doc_signals).replace('_',' ').title()+'  ·  Route: '+classify_question(q,st.session_state.df,st.session_state.doc_signals).replace('_',' ').title())
if st.button('Ask BizLens',type='primary',disabled=not q.strip(),width='stretch'):
    with st.spinner('Checking the connected evidence...'):
        ans=routed_answer(q.strip(),st.session_state.artifacts,st.session_state.df,st.session_state.doc_signals,st.session_state.get('business_objective',''),st.session_state.get('investigations',[]),st.session_state.get('recommendations_v2',[]))
    st.session_state.last_answer=ans; st.session_state.chat.append({'question':q.strip(),'answer':ans})
if st.session_state.get('last_answer'):
    section_head('Answer'); st.markdown(st.session_state.last_answer)
    st.caption('Evidence boundary: calculated facts and documented statements are separated from hypotheses. Association is not proof of causation.')
if st.session_state.chat:
    with st.expander('Recent workspace questions'):
        for x in reversed(st.session_state.chat[-5:]): st.markdown(f'**Q:** {x["question"]}\n\n{x["answer"]}')
