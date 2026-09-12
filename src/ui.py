from pathlib import Path
import streamlit as st
from src.ingest import read_tabular, extract_text, classify
from src.doc_intel import build_context

SUPPORTED=['csv','xlsx','xls','docx','pdf','pptx','txt']


def _rebuild_workspace_intelligence():
    """Rebuild every shared-workspace layer immediately after evidence changes."""
    from src.workspace_intelligence import build_workspace_context, choose_techniques
    from src.intelligence import build_evidence_graph
    from src.workspace import refresh_workspace

    sig, flags, _ = build_context(st.session_state.artifacts)
    st.session_state.doc_signals = sig
    st.session_state.analysis['ambiguity_flags'] = flags
    objective = st.session_state.get('business_objective', '')
    st.session_state.workspace_summary = build_workspace_context(
        st.session_state.artifacts,
        st.session_state.datasets,
        st.session_state.doc_signals,
        objective,
    )
    st.session_state.analysis['suggested_techniques'] = choose_techniques(
        st.session_state.workspace_summary
    )
    st.session_state.evidence_graph = build_evidence_graph(
        st.session_state.artifacts,
        st.session_state.df,
        st.session_state.doc_signals,
        objective,
    )
    refresh_workspace()


def process_uploaded_files(files):
    if not files:
        return False
    existing={a['name'] for a in st.session_state.artifacts}
    changed=False
    for f in files:
        if f.name in existing:
            continue
        data=f.getvalue()
        kind=classify(f.name)
        item={'name':f.name,'kind':kind,'size':len(data),'text':None,'bytes':data}
        try:
            if kind=='dataset':
                df=read_tabular(f.name,data)
                item.update(rows=len(df),columns=len(df.columns))
                st.session_state.datasets[f.name]=df
                st.session_state.df=df
                st.session_state.dataset_name=f.name
            else:
                item['text']=extract_text(f.name,data)
                item.update(words=len((item['text'] or '').split()))
            st.session_state.artifacts.append(item)
            existing.add(f.name)
            changed=True
        except Exception as exc:
            st.error(f'Could not process {f.name}: {exc}')
    if changed:
        _rebuild_workspace_intelligence()
    return changed


def load_demo_workspace():
    """Load a complete, connected demo: structured data plus business evidence."""
    data_dir = Path(__file__).resolve().parents[1] / 'data'
    demo_names = [
        'sales_demo.csv',
        'demo_meeting_notes.docx',
        'demo_requirements.pdf',
        'demo_business_review.pptx',
    ]
    from src.state import reset_all
    reset_all()
    for name in demo_names:
        path=data_dir/name
        if not path.exists():
            continue
        data=path.read_bytes()
        kind=classify(name)
        item={'name':name,'kind':kind,'size':len(data),'text':None,'bytes':data}
        if kind=='dataset':
            df=read_tabular(name,data)
            item.update(rows=len(df),columns=len(df.columns))
            st.session_state.datasets[name]=df
            st.session_state.df=df
            st.session_state.dataset_name=name
        else:
            item['text']=extract_text(name,data)
            item.update(words=len((item['text'] or '').split()))
        st.session_state.artifacts.append(item)
    _rebuild_workspace_intelligence()
    return len(st.session_state.artifacts)


def clear_workspace():
    from src.state import reset_all
    reset_all()


def artifact_icon(kind): return '▦' if kind=='dataset' else '▱'
def artifact_type_label(kind): return 'Dataset' if kind=='dataset' else 'Business document'
def format_bytes(size):
    if size<1024:return f'{size} B'
    if size<1024**2:return f'{size/1024:.0f} KB'
    return f'{size/1024**2:.1f} MB'

def download_figure(fig, filename, key):
    html=fig.to_html(include_plotlyjs='cdn',full_html=True)
    st.download_button('Download chart',html,file_name=filename,mime='text/html',key=key)
