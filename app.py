import streamlit as st
from src.styles import inject_css, brand
from src.state import init_state
from src.workspace_intelligence import build_workspace_context, choose_techniques
from src.workspace import init_workspace, refresh_workspace
from src.intelligence import build_evidence_graph
from src.ai import ai_status
from src.ui import process_uploaded_files, clear_workspace

st.set_page_config(page_title='BizLens', page_icon=None, layout='wide', initial_sidebar_state='expanded')
init_state()
init_workspace()
inject_css()

# Keep the navigation deliberately small and grouped around the BA workflow.
pages = {
    'WORKSPACE': [
        st.Page('pages/home.py', title='Home', icon=':material/home:', default=True),
        st.Page('pages/1_Ask.py', title='Ask BizLens', icon=':material/chat:'),
    ],
    'UNDERSTAND': [
        st.Page('pages/2_Data.py', title='Data & Insights', icon=':material/analytics:'),
        st.Page('pages/5_Documents.py', title='Business Context', icon=':material/description:'),
    ],
    'INVESTIGATE': [
        st.Page('pages/3_Investigation.py', title='Investigation', icon=':material/search:'),
    ],
    'DECIDE': [
        st.Page('pages/6_Recommendations.py', title='Recommendations', icon=':material/lightbulb:'),
    ],
    'DELIVER': [
        st.Page('pages/7_Deliverables.py', title='Studio', icon=':material/task_alt:'),
    ],
}

pg = st.navigation(pages, position='sidebar', expanded=True)

with st.sidebar:
    st.divider()
    brand()
    st.markdown('**Your business evidence**')
    st.caption('Upload the files you already use. BizLens keeps them connected across analysis and BA deliverables.')
    uploads = st.file_uploader(
        'Add business files', type=['csv','xlsx','xls','docx','pdf','pptx','txt'],
        accept_multiple_files=True, key='sidebar_uploader'
    )
    if process_uploaded_files(uploads):
        st.session_state.workspace_summary = build_workspace_context(
            st.session_state.artifacts, st.session_state.datasets, st.session_state.doc_signals
        )
        st.session_state.analysis['suggested_techniques'] = choose_techniques(st.session_state.workspace_summary)
        st.session_state.evidence_graph = build_evidence_graph(st.session_state.artifacts, st.session_state.df, st.session_state.doc_signals)
        refresh_workspace()
        st.rerun()

    if st.session_state.artifacts:
        st.caption(f'{len(st.session_state.artifacts)} source(s) connected')
        datasets = list(st.session_state.get('datasets', {}).keys())
        if len(datasets) > 1:
            current = st.session_state.get('dataset_name')
            selected = st.selectbox('Active dataset', datasets, index=datasets.index(current) if current in datasets else 0)
            if selected != current:
                st.session_state.dataset_name = selected
                st.session_state.df = st.session_state.datasets[selected]
                st.rerun()
        elif datasets:
            st.caption(f'Active dataset: {datasets[0]}')
        if st.button('Clear workspace', width='stretch'):
            clear_workspace()
            st.rerun()

    st.divider()
    st.markdown('**AI Connection (optional)**')
    status = ai_status()
    if status.get('configured') and not st.session_state.get('ai_api_key'):
        st.caption(f"AI synthesis ready: {status['provider']} (from .env). Calculations still use local Python.")
        with st.expander('Use a different key for this session'):
            provider = st.selectbox('AI provider', ['Gemini','OpenAI'], key='ai_provider_choice')
            st.text_input('API key', type='password', key='ai_api_key', help='Optional override for this session only. Never written to project files.')
    else:
        provider = st.selectbox('AI provider', ['Gemini','OpenAI'], index=0 if status.get('provider') in (None,'Gemini') else 1, key='ai_provider_choice')
        st.text_input('API key', type='password', key='ai_api_key', help='Optional. Stored only for this Streamlit session and never written to the project files. For a permanent setup, add it to a .env file instead (see .env.example).')
        live = ai_status()
        if live['configured']:
            st.caption(f"AI synthesis ready: {live['provider']}. Calculations still use local Python.")
        else:
            st.caption('Optional AI is not configured. Safe local evidence mode remains fully available.')

    st.divider()
    st.caption('BIZLENS · evidence before assumptions')
    st.markdown('<div class="footer-note">Human review remains the final approval step.</div>', unsafe_allow_html=True)

pg.run()
