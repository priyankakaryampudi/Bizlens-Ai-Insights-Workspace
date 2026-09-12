"""Shared workspace backbone for BizLens.
All pages read/write the same evidence-first workspace state.
"""
import streamlit as st
from .evidence import build_evidence_register

def init_workspace():
    defaults={
        'workspace':{
            'objective':'', 'data_facts':[], 'document_evidence':[],
            'context':{}, 'investigations':[], 'recommendations':[],
            'decisions':[], 'deliverables':{}, 'evidence_index':[]
        }
    }
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v

def refresh_workspace():
    init_workspace()
    ws=st.session_state.workspace
    ws['objective']=st.session_state.get('business_objective','')
    ws['context']=st.session_state.get('workspace_summary',{})
    graph=st.session_state.get('evidence_graph',{}) or {}
    ws['data_facts']=graph.get('findings',[])
    ws['document_evidence']=[
        {'type':kind[:-1] if kind.endswith('s') else kind, 'statement':str(item), 'source':'connected documents'}
        for kind, values in (st.session_state.get('doc_signals',{}) or {}).items()
        for item in (values or [])
    ]
    ws['investigations']=st.session_state.get('investigations',[])
    ws['recommendations']=st.session_state.get('recommendations_v2',[])
    ws['decisions']=(st.session_state.get('doc_signals',{}) or {}).get('decisions',[])
    index=[]
    for a in st.session_state.get('artifacts',[]):
        index.append({'source':a.get('name'),'type':a.get('kind'),'rows':a.get('rows'),'words':a.get('words')})
    ws['evidence_index']=index
    register=build_evidence_register(
        st.session_state.get('artifacts',[]), st.session_state.get('df'),
        st.session_state.get('doc_signals',{}), st.session_state.get('business_objective','')
    )
    st.session_state.evidence_register=register
    ws['evidence_register']=register
    return ws
