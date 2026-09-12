import streamlit as st
DEFAULTS={'artifacts':[],'df':None,'datasets':{},'dataset_name':None,'analysis':{},'chat':[],'last_answer':None,'doc_signals':{},'report_path':None,'report_selection_token':None,'pack_path':None,'business_objective':'','investigations':[],'workspace_summary':{},'cleaned_df':None,'quality_actions':{},'custom_chart_prompt':'','evidence_graph':{},'evidence_register':[],'recommendations_v2':[],'journey':[],'context_version':0,'workspace':{}}
def init_state():
    for key,value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key]=value.copy() if isinstance(value,(dict,list)) else value
def reset_all():
    for key,value in DEFAULTS.items():
        st.session_state[key]=value.copy() if isinstance(value,(dict,list)) else value
