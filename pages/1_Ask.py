import streamlit as st
from src.styles import hero
from src.ai import routed_answer, display_answer
from src.intelligence import build_evidence_graph

hero('ASK','Ask BizLens','Ask a question about your business data and documents.')
if not st.session_state.artifacts: st.info('Upload business evidence on Home first.'); st.stop()
st.session_state.evidence_graph=build_evidence_graph(st.session_state.artifacts,st.session_state.df,st.session_state.doc_signals,st.session_state.get('business_objective',''))

q=st.text_area('Your question',placeholder='Ask about performance, requirements, risks, stakeholders, investigations or recommendations.',height=105,key='ask_question',label_visibility='collapsed')
if st.button('Ask BizLens',type='primary',disabled=not q.strip(),width='stretch'):
    with st.spinner('Thinking...'):
        ans=routed_answer(q.strip(),st.session_state.artifacts,st.session_state.df,st.session_state.doc_signals,st.session_state.get('business_objective',''),st.session_state.get('investigations',[]),st.session_state.get('recommendations_v2',[]))
    st.session_state.last_answer=ans; st.session_state.chat.append({'question':q.strip(),'answer':ans})
if st.session_state.get('last_answer'):
    st.markdown(display_answer(st.session_state.last_answer))