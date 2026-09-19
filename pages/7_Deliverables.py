import streamlit as st
from pathlib import Path
import zipfile
import tempfile
from src.styles import hero, section_head
from src.analytics import auto_insights, guess_metric, guess_dimension, guess_date
from src.reports import make_pdf, make_docx
from src.diagrams import parse_diagram_body
from src.studio import studio_sections
from src.intelligence import decision_recommendations
from src.workspace import refresh_workspace

hero('DELIVER','Studio','Choose one professional deliverable. BizLens reuses the connected workspace instead of restarting the analysis.')
if not st.session_state.artifacts:
    st.info('Upload evidence first.'); st.stop()

refresh_workspace()
objective=st.session_state.get('business_objective') or 'Define and improve the business outcome represented by the connected evidence.'
findings=auto_insights(st.session_state.df,guess_metric(st.session_state.df,objective),guess_dimension(st.session_state.df,objective),guess_date(st.session_state.df)) if st.session_state.df is not None else []
# Recommendations may not exist yet if the user hasn't visited Recommendations -
# compute them here too so RCA/PRD/KPI/Roadmap are grounded even on a first visit.
if not st.session_state.get('recommendations_v2'):
    st.session_state.recommendations_v2=decision_recommendations(st.session_state.df,st.session_state.doc_signals,st.session_state.get('investigations',[]),objective,st.session_state.get('evidence_register',[]))
choices=['Executive Brief','BRD','Product Requirements Document (PRD)','Functional Requirements Document (FRD)','Process Specification (AS-IS / TO-BE)','Root Cause Analysis (RCA)','Data & Business Analysis Report','KPI / Performance Review','Gap Analysis','Business Case / Improvement Proposal','Requirements Traceability Matrix (RTM)','Implementation Roadmap','User Stories & Acceptance Criteria','Use Case Catalogue','UAT & Test Scenarios','Stakeholder Analysis','RACI Matrix','Action Plan']

section_head('Choose a deliverable', 'Create one professional BA artifact from the same connected evidence and analysis.')
artifact=st.selectbox('Deliverable',choices,index=None,placeholder='Select what you want to create')
if not artifact:
    st.caption('Select one deliverable to preview it. BizLens deliberately does not dump every artifact at once.')
    st.stop()

# A generated file belongs to one exact deliverable + format. Clear stale output as soon as the selection changes.
fmt=st.radio('Download format',['DOCX','Markdown/Text','PDF'],horizontal=True)
selection_token=f'{artifact}|{fmt}'
if st.session_state.get('report_selection_token') != selection_token:
    st.session_state.report_path=None
    st.session_state.report_selection_token=selection_token

def _doc_title(deliverable, objective):
    """A generic 'BizLens - BRD' title reads like a tool export, not a real business
    document. Build a title that names the actual subject, the way a document
    you'd genuinely submit would."""
    subject = (objective or '').strip().rstrip('.')
    if subject and subject != 'Define and improve the business outcome represented by the connected evidence':
        subject = subject[0].upper() + subject[1:]
        if len(subject) > 90:
            subject = subject[:89].rsplit(' ', 1)[0] + '…'
        return f'{deliverable}: {subject}'
    return deliverable

doc_title = _doc_title(artifact, objective)
sections=studio_sections(artifact,objective,findings,st.session_state.doc_signals,st.session_state.df,st.session_state.get('investigations',[]),st.session_state.get('recommendations_v2',[]),st.session_state.get('evidence_register',[]))
st.markdown(f'<div class="doc-cover"><span class="eyebrow">Evidence-backed output</span><b>{doc_title}</b><div class="small-note">Generated from the active workspace. Human review remains the final approval step.</div></div>', unsafe_allow_html=True)
section_head('Preview', 'Review the structure before generating the final file.')
for h,b in sections:
    with st.expander(h,expanded=h.startswith('1.')):
        diagram=parse_diagram_body(b)
        if diagram:
            img_path,caption=diagram
            st.image(img_path,width='stretch')
            st.markdown(caption)
        else:
            st.markdown(b)

if st.button('Generate deliverable',type='primary',width='stretch'):
    root=Path(tempfile.mkdtemp(prefix='bizlens_deliverable_'))
    stem='BizLens_'+artifact.replace('/','_').replace(' ','_').replace('&','and')
    try:
        if fmt=='DOCX':
            path=root/(stem+'.docx'); make_docx(path,doc_title,sections)
        elif fmt=='PDF':
            path=root/(stem+'.pdf'); make_pdf(path,doc_title,sections)
        else:
            def _md_body(b):
                d=parse_diagram_body(b)
                if d:
                    _,caption=d
                    return '[Diagram available in the DOCX/PDF export - not renderable in plain text/Markdown]\n\n'+caption
                return b
            path=root/(stem+'.md'); path.write_text('\n\n'.join(f'# {h}\n\n{_md_body(b)}' for h,b in sections),encoding='utf-8')
        st.session_state.report_path=str(path)
        st.session_state.report_selection_token=selection_token
        st.success('Deliverable generated successfully.')
    except Exception as exc:
        st.error(f'Deliverable generation failed: {exc}')

if st.session_state.get('report_path') and st.session_state.get('report_selection_token') == selection_token:
    p=Path(st.session_state.report_path)
    if p.exists():
        with open(p,'rb') as f:
            st.download_button('Download deliverable',f,file_name=p.name,mime='application/octet-stream',width='stretch')
