import streamlit as st
import pandas as pd
from src.styles import hero, section_head
from src.doc_intel import build_context
from src.workspace_intelligence import build_workspace_context, ba_analysis_recommendations, recommended_next_steps

hero(
    'UNDERSTAND',
    'Business Context',
    'Capture the business meaning around the data: objective, requirements, stakeholders, decisions, risks and evidence gaps. Detailed KPI analysis stays in Data & Insights.'
)
if not st.session_state.artifacts:
    st.info('Upload business evidence first.')
    st.stop()

sig, flags, _ = build_context(st.session_state.artifacts)
st.session_state.doc_signals = sig
ctx = build_workspace_context(
    st.session_state.artifacts,
    st.session_state.datasets,
    sig,
    st.session_state.get('business_objective', ''),
    flags,
)
st.session_state.workspace_summary = ctx

n_docs = sum(a.get('kind') == 'document' for a in st.session_state.artifacts)
n_sets = len(st.session_state.datasets)
n_evidence = sum(len(v) for v in sig.values() if isinstance(v, list))
status = 'Validation needed' if ctx.get('contradiction') else ('Investigation in progress' if st.session_state.get('investigations') else 'Evidence ready')
st.caption(
    f'{n_docs} business document{"s" if n_docs != 1 else ""} · '
    f'{n_sets} dataset{"s" if n_sets != 1 else ""} · '
    f'{n_evidence} extracted evidence items · Status: **{status}**'
)

section_head('Business objective', 'The question BizLens is carrying through the workspace.')
a, b = st.columns(2)
with a:
    st.markdown('**Working objective**')
    st.markdown(ctx.get('objective_stated') or ctx.get('objective_derived') or 'Clarify the business objective from the connected evidence.')
with b:
    st.markdown('**Objective status**')
    st.markdown('User-defined' if ctx.get('objective_stated') else 'Evidence-derived from the business case')

if ctx.get('contradiction'):
    st.markdown(f'<div class="validation-card"><b>Validation note</b><br>{ctx["contradiction"]}</div>', unsafe_allow_html=True)

section_head('Business drivers & pain points', 'Themes extracted from the connected business evidence. Quantified performance movement is intentionally kept on Data & Insights.')
problems = ctx.get('problems') or []
if problems:
    for p in problems[:8]:
        st.markdown(f'<div class="finding">• {p.capitalize()}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="finding">No specific business driver has been established from the connected documents yet.</div>', unsafe_allow_html=True)

section_head('Evidence & key findings', 'Separate what the documents explicitly say from the questions that remain open.')
k1, k2 = st.columns(2)
with k1:
    st.markdown('**Observed or stated in the connected evidence**')
    findings = ctx.get('data_findings') or []
    if findings:
        for f in findings[:6]:
            if f.get('change_pct') is not None:
                direction = 'up' if f['change_pct'] >= 0 else 'down'
                st.markdown(f'✓ {f["metric"]}: {direction} {abs(f["change_pct"]):.1f}% ({f.get("period", "aligned period")})')
            elif f.get('value') is not None:
                st.markdown(f'✓ {f["metric"]}: {f["value"]:,.0f} total')
    else:
        st.markdown('No quantitative observation is available yet. Use Data & Insights for structured analysis.')
with k2:
    st.markdown('**Open business questions**')
    for x in (ctx.get('questions') or [])[:6] or ['No open question has been recorded yet.']:
        st.markdown(f'? {x}')

section_head('Requirements that shape the solution', 'Explicit system, interface, analysis and output requirements extracted from the connected documents.')
req_table = ctx.get('requirements_table', [])
if req_table:
    rdf = pd.DataFrame(req_table)[['id', 'need', 'category', 'priority']].rename(
        columns={'id': 'ID', 'need': 'Requirement', 'category': 'Type', 'priority': 'Priority'}
    )
    st.dataframe(rdf, width='stretch', hide_index=True)
    st.caption('Source: connected requirements evidence · Status: Draft pending business confirmation')
else:
    st.info('No explicit solution requirement was extracted from the connected documents.')

left, right = st.columns(2)
with left:
    section_head('Stakeholders')
    stakeholder_table = ctx.get('stakeholder_table', [])
    if stakeholder_table:
        for s in stakeholder_table:
            st.markdown(f'• **{s["stakeholder"]}** — decision role and ownership still need confirmation.')
    else:
        st.markdown('No stakeholder group was explicitly named.')

    section_head('Decisions required')
    decisions = ctx.get('decisions_table', []) or []
    if decisions:
        for d in decisions:
            st.markdown(f'• {d["decision"]}<br><span class="muted">{d["status"]}</span>', unsafe_allow_html=True)
    else:
        st.markdown('No explicit decision has been recorded yet.')

with right:
    section_head('Risks & issues')
    rc = ctx.get('risk_categories', {})
    risk_items = []
    for key in ['known_risks', 'known_issues', 'potential_risks']:
        risk_items += rc.get(key, [])
    if risk_items:
        for x in risk_items[:8]:
            st.markdown(f'• {x}')
    else:
        st.markdown('No explicit risk or issue was confirmed in the connected evidence.')

    section_head('Open questions')
    questions = ctx.get('questions_grouped', [])[:6]
    if questions:
        for q in questions:
            st.markdown(f'• **{q["priority"]}** — {q["question"]}')
    else:
        st.markdown('No additional open question was extracted.')

section_head('Gaps that block a confident solution', 'These gaps explain why a signal may be visible before a decision is ready.')
gaps = ctx.get('gaps', {})
for key, label in [('business', 'Business'), ('data', 'Data'), ('requirement', 'Requirement')]:
    items = gaps.get(key, [])
    if items:
        st.markdown(f'**{label} gaps**')
        for g in items:
            st.markdown(
                f'<div class="finding"><b>{g["gap"]}</b><br>{g["why"]}<br><span class="muted">Resolution: {g["resolution"]}</span></div>',
                unsafe_allow_html=True,
            )

section_head('Recommended BA analysis', 'The analysis techniques that fit the current evidence and business question.')
for t in ba_analysis_recommendations(ctx):
    st.markdown(
        f'<div class="finding"><b>{t["technique"]}</b> · {t["status"]}<br><span class="muted">Why: {t["why"]} · Evidence: {t["evidence"]}</span></div>',
        unsafe_allow_html=True,
    )

section_head('Recommended next steps', 'Move from context into the next stage of the BizLens workflow.')
for i, step in enumerate(
    recommended_next_steps(
        ctx,
        st.session_state.df is not None,
        bool(st.session_state.get('investigations')),
        bool(st.session_state.get('recommendations_v2')),
    ),
    1,
):
    st.markdown(f'{i}. {step}')
