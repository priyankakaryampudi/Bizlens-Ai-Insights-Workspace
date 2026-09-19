import streamlit as st
import pandas as pd
import plotly.express as px
from src.styles import hero, section_head
from src.intelligence import investigation_brief
from src.evidence import find_evidence_for_text

hero(
    'INVESTIGATE',
    'Find the driver, not just the chart.',
    'Turn the observed business pattern into a focused investigation: where the change is concentrated, which signals move with it, which explanations are plausible, and what evidence is still needed.'
)
if st.session_state.df is None and not st.session_state.doc_signals:
    st.info('Upload business evidence first.')
    st.stop()

brief = investigation_brief(
    st.session_state.df,
    st.session_state.doc_signals,
    st.session_state.get('business_objective', ''),
)
st.session_state.analysis['current_investigation'] = brief

section_head('Problem to investigate')
st.markdown(f'<div class="finding big-answer"><b>{brief["problem"]}</b></div>', unsafe_allow_html=True)

section_head('Investigation finding', 'This is the strongest evidence-backed interpretation currently available. It is not a causal conclusion.')
st.markdown(
    f'<div class="answer-card"><div class="answer-head">{brief.get("executive_finding", "No executive finding is available yet.")}</div></div>',
    unsafe_allow_html=True,
)

section_head('What the evidence says', 'Quantitative observations and source-backed signals that support the investigation.')
for e in brief.get('evidence', []) or ['No quantitative observation is available yet.']:
    st.markdown(f'<div class="finding">✓ {e}</div>', unsafe_allow_html=True)

if brief.get('contributors'):
    section_head('Where the change is concentrated', 'This ranks groups by period change so the investigation starts with deterioration, not simply the largest business unit.')
    g = pd.DataFrame(brief['contributors'])
    if 'change_pct' in g.columns:
        plot = g.dropna(subset=['change_pct']).copy()
        if not plot.empty:
            fig = px.bar(
                plot.sort_values('change_pct'),
                x='change_pct',
                y='group',
                orientation='h',
                title=f'{brief["metric"]}: change by {brief["dimension"]}',
            )
            fig.update_layout(template='plotly_white', height=330, margin=dict(l=20, r=20, t=55, b=20), xaxis_title='Change (%)', yaxis_title='')
            st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})

section_head('Signals to validate', 'Signals that move alongside the business outcome. They are investigation leads, not confirmed causes.')
operational = [h for h in brief.get('hypotheses', []) if h.get('kind') in ('sla', 'tickets')]
if operational:
    for h in operational:
        label = 'Service performance' if h.get('kind') == 'sla' else 'Customer/service pressure'
        st.markdown(
            f'<div class="finding"><b>{label}</b><br>{h["hypothesis"]}<br><span class="muted">{h.get("confidence", "")}</span></div>',
            unsafe_allow_html=True,
        )
else:
    st.caption('No additional operational signal could be calculated from the connected fields.')

section_head('Hypotheses to test', 'Move from signal to explanation, then define the evidence needed to confirm or reject each hypothesis.')
hyps = brief.get('hypotheses', [])
if not hyps:
    st.markdown('<div class="finding">No defensible hypothesis has been formed from the current evidence. Add a more detailed operational or customer dataset.</div>', unsafe_allow_html=True)
if hyps:
    hdf = pd.DataFrame([{'ID': h.get('id',''), 'Hypothesis': h.get('hypothesis',''), 'Status': h.get('status',''), 'Assessment': h.get('confidence','')} for h in hyps])
    st.dataframe(hdf, width='stretch', hide_index=True)

for h in hyps:
    matched = find_evidence_for_text(st.session_state.get('evidence_register', []), h.get('hypothesis', ''), limit=3)
    evidence_ids = ', '.join(e.get('evidence_id', '') for e in matched if e.get('evidence_id'))
    evidence_caption = ('Traceable evidence: ' + evidence_ids) if evidence_ids else 'Evidence link: additional source evidence required'
    st.markdown(
        f'<div class="finding"><b>{h.get("id", "")} — {h["hypothesis"]}</b><br><span class="muted">{h.get("status", "")} · {h.get("confidence", "")}</span><br><small>{evidence_caption}</small></div>',
        unsafe_allow_html=True,
    )
    steps = h.get('validation') or []
    if steps:
        with st.expander(f'Validation plan — {h.get("id", "this hypothesis")}'):
            for i, step in enumerate(steps, 1):
                if str(step).strip():
                    st.markdown(f'{i}. {step}')

section_head('Candidate business signals', 'Signals supported by the connected data. None is labelled a root cause unless the evidence supports that conclusion.')
drivers = brief.get('drivers', [])
if drivers:
    ddf = pd.DataFrame(drivers)[['driver', 'category', 'relationship', 'confidence']].rename(
        columns={'driver': 'Driver', 'category': 'Signal type', 'relationship': 'What the data shows', 'confidence': 'Assessment'}
    )
    st.dataframe(ddf, width='stretch', hide_index=True)
else:
    st.info('No candidate driver can be tested with the current schema.')

section_head('Root-cause status', 'A deliberately conservative status: BizLens does not label a cause confirmed without supporting evidence.')
rc = brief.get('root_cause', {})
cols = st.columns(5)
for col, (label, count) in zip(cols, rc.items()):
    with col:
        col.metric(label, count)
if rc.get('Confirmed', 0) == 0 and rc.get('Strongly supported', 0) == 0:
    st.caption('No root cause is confirmed. BizLens deliberately stops at an evidence-backed signal until the missing validation is completed.')

section_head('Investigation conclusion', 'Separate what is established, what is still unproven, and what evidence would close the gap.')
conc = brief.get('conclusion', {})
if conc:
    st.markdown(
        f'<div class="finding"><b>Established</b><br>{conc["established"]}<br><br><b>Not established</b><br>{conc["not_established"]}<br><br><b>Strongest signal</b><br>{conc["most_credible"]}<br><br><b>Evidence still required</b><br>{conc["evidence_required"]}<br><br><b>Next investigation</b><br>{conc["next_investigation"]}</div>',
        unsafe_allow_html=True,
    )

section_head('Next investigation step')
st.info(brief['next_step'])
if st.button('Save this investigation to the workspace', type='primary', width='stretch'):
    record = {
        'focus': brief.get('problem'),
        'signal': ' | '.join(brief.get('evidence', [])[:4]),
        'hypotheses': [h['hypothesis'] for h in brief.get('hypotheses', [])],
        'brief': brief,
    }
    existing = st.session_state.get('investigations', [])
    if not any(x.get('focus') == record['focus'] for x in existing):
        existing.append(record)
    st.session_state.investigations = existing
    from src.workspace import refresh_workspace
    refresh_workspace()
    st.success('Investigation saved. Recommendations and Studio can reuse it.')
