import streamlit as st
from src.styles import hero, section_head
from src.ui import process_uploaded_files, load_demo_workspace
from src.doc_intel import build_context
from src.workspace_intelligence import build_workspace_context, choose_techniques
from src.intelligence import build_evidence_graph, workspace_journey, next_best_action, investigation_brief
from src.analytics import guess_metric, guess_dimension
from src.workspace import refresh_workspace

hero(
    'BIZLENS',
    'Business Intelligence Workspace',
    'Connect business evidence once. BizLens carries the evidence through analysis, investigation and decision-making without losing the thread.'
)

is_empty = not st.session_state.artifacts
if is_empty:
    section_head('Start your workspace', 'Upload the dataset and business documents you already use. BizLens keeps them connected across the workflow.')
else:
    section_head('Add evidence', 'New datasets and documents are automatically carried into the existing analysis.')

files = st.file_uploader(
    'Add business evidence (data or documents)',
    type=['csv', 'xlsx', 'xls', 'docx', 'pdf', 'pptx', 'txt'],
    accept_multiple_files=True,
    key='uploader_main'
)
if files:
    if process_uploaded_files(files):
        st.success(f'Connected {len(files)} file{"s" if len(files) != 1 else ""} to your workspace.')
        st.rerun()

if is_empty:
    if st.button('Try the complete demo workspace'):
        count = load_demo_workspace()
        st.success(f'Connected {count} demo sources: data + meeting notes + requirements + review evidence.')
        st.rerun()
    st.stop()

sig, flags, _ = build_context(st.session_state.artifacts)
st.session_state.doc_signals = sig
obj = st.session_state.get('business_objective', '')
ctx = build_workspace_context(
    st.session_state.artifacts,
    st.session_state.datasets,
    sig,
    obj,
    flags,
)
st.session_state.workspace_summary = ctx
st.session_state.analysis['suggested_techniques'] = choose_techniques(ctx)
st.session_state.evidence_graph = build_evidence_graph(
    st.session_state.artifacts,
    st.session_state.df,
    sig,
    obj,
)
refresh_workspace()

df = st.session_state.df
metric = guess_metric(df, obj) if df is not None else None
dimension = guess_dimension(df, obj) if df is not None else None

section_head('Workspace snapshot', 'A quick orientation, not another dashboard.')
source_count = len(st.session_state.artifacts)
dataset_count = len(st.session_state.datasets)
evidence_count = sum(len(v) for v in sig.values() if isinstance(v, list))
status = 'Ready to investigate' if df is not None else 'Evidence connected'
if st.session_state.get('recommendations_v2'):
    status = 'Decision-ready'
elif st.session_state.get('investigations'):
    status = 'Investigation in progress'

cards = [
    ('Sources connected', str(source_count), 'documents + datasets'),
    ('Structured datasets', str(dataset_count), 'available for analysis'),
    ('Evidence items', str(evidence_count), 'extracted from connected sources'),
    ('Workflow status', status, 'current workspace stage'),
]
cols = st.columns(4)
for col, (label, value, note) in zip(cols, cards):
    with col:
        st.markdown(f'<div class="mini-card"><div class="label">{label}</div><div class="value">{value}</div><div class="note">{note}</div></div>', unsafe_allow_html=True)

section_head('What are we trying to understand?')
if obj:
    st.markdown(f'<div class="finding"><b>{obj}</b></div>', unsafe_allow_html=True)
    st.caption('Objective status: User-defined')
elif metric and dimension:
    st.markdown(
        f'<div class="finding"><b>Explain the {metric} change, identify where it is concentrated, and determine what business driver needs validation.</b></div>',
        unsafe_allow_html=True,
    )
    st.caption('Objective status: Evidence-derived starting point')
else:
    st.markdown(f'<div class="finding"><b>{(ctx.get("objectives") or ["Clarify the business objective."])[0]}</b></div>', unsafe_allow_html=True)
    st.caption('Objective status: Evidence-derived')

objective = st.text_area(
    'Set or refine the objective',
    value=obj,
    placeholder='Example: Why did revenue weaken in Q4 and what should management validate next?',
    height=80,
    label_visibility='collapsed',
)
if objective != obj:
    st.session_state.business_objective = objective.strip()
    refresh_workspace()
    st.rerun()

section_head('Current workspace status', 'BizLens keeps the home view focused on orientation. Detailed numbers belong in Data & Insights; causal reasoning belongs in Investigation.')
if df is not None:
    brief = investigation_brief(df, sig, obj)
    finding = brief.get('executive_finding', '')
    st.markdown(f'<div class="answer-card"><div class="answer-head">Current business signal</div><div class="answer-body">{finding}</div></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="finding">The evidence is connected, but a structured dataset is needed for quantified analysis.</div>', unsafe_allow_html=True)

if ctx.get('contradiction'):
    st.markdown(f'<div class="validation-card"><b>Validation needed</b><br>{ctx["contradiction"]}</div>', unsafe_allow_html=True)

section_head('Recommended next action', 'One concrete move based on the current workspace state.')
action = next_best_action(
    st.session_state.artifacts,
    ctx,
    st.session_state.get('investigations', []),
    st.session_state.get('recommendations_v2', []),
    df,
)
st.markdown(
    f'<div class="action-card"><b>{action["title"]}</b><br><span class="muted">Why:</span> {action["why"]}<br><span class="muted">This will answer:</span> {action["answers"]}</div>',
    unsafe_allow_html=True,
)
if action.get('page'):
    st.page_link(action['page'], label=action['button'], width='stretch')

section_head('Analysis progress')
cols = st.columns(5)
for col, (stage, label, status_text, done) in zip(
    cols,
    workspace_journey(
        st.session_state.artifacts,
        ctx,
        st.session_state.get('investigations', []),
        st.session_state.get('recommendations_v2', []),
    ),
):
    with col:
        st.markdown(f"{'✓' if done else '○'} **{stage}**")
        st.caption(f'{label} — {status_text}')
