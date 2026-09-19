import streamlit as st
import plotly.express as px
from src.styles import hero, section_head
from src.analytics import *
from src.workspace import refresh_workspace

hero(
    'UNDERSTAND',
    'Data & Insights',
    'Explore the structured data directly: trends, concentration, contribution, operational signals and data-quality issues. This page shows what the numbers say, not why they happened.'
)

df = st.session_state.df
if df is None:
    st.info('Upload a structured dataset first.')
    st.stop()

obj = st.session_state.get('business_objective', '')
metric = guess_metric(df, obj)
dim = guess_dimension(df, obj)
date = guess_date(df)

section_head('Executive dashboard', 'Core measures calculated from the active dataset.')
items = business_kpis(df, metric, dim, date)
cols = st.columns(len(items))
for col, item in zip(cols, items):
    col.metric(item['label'], item['value'], item['detail'])

section_head('What deserves investigation?', 'A short bridge from measurable movement to the Investigation page.')
try:
    lead = auto_insights(df, metric, dim, date)[:3]
except Exception:
    lead = []
if lead:
    text = '<div class="insight-card">' + '<br>'.join(f'• {x}' for x in lead) + '</div>'
    st.markdown(text, unsafe_allow_html=True)
else:
    st.markdown('<div class="insight-card">The dashboard establishes the pattern. Move to Investigation when a measurable change needs explanation.</div>', unsafe_allow_html=True)


def show(fig, collect_title=None):
    fig.update_layout(
        template='plotly_white',
        paper_bgcolor='#FFFDF8',
        plot_bgcolor='#FFFDF8',
        height=370,
        margin=dict(l=20, r=20, t=55, b=25),
    )
    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})
    if collect_title:
        st.session_state.setdefault('_dashboard_figs', []).append((collect_title, fig))


st.session_state['_dashboard_figs'] = []
section_head('Performance views', 'Use these views to establish the measurable pattern before moving to Investigation.')
if date:
    try:
        t = trend(df, date, metric)
        if len(t) >= 2:
            show(px.line(t, x=date, y=metric, markers=True, title=f'{metric} trend'), f'{metric} trend')
    except Exception:
        st.caption('Trend unavailable for the current date field.')

if dim:
    g = dimension_breakdown(df, dim, metric, 10)
    if not g.empty:
        a, b = st.columns(2)
        with a:
            show(px.bar(g.sort_values('total'), x='total', y=dim, orientation='h', title=f'{metric} by {dim}'), f'{metric} by {dim}')
        with b:
            show(px.pie(g.head(6), names=dim, values='total', hole=.58, title=f'{metric} contribution mix'), f'{metric} contribution mix')

a, b = st.columns(2)
with a:
    try:
        show(px.histogram(distribution(df, metric), x='value', nbins=30, title=f'{metric} distribution'), f'{metric} distribution')
    except Exception:
        st.empty()
with b:
    op = next((c for c in ['SLA_Achievement_Rate', 'Support_Tickets', 'Cancellations'] if c in df.columns), None)
    if op and date:
        try:
            t = trend(df, date, op)
            if len(t) >= 2:
                show(px.line(t, x=date, y=op, markers=True, title=f'{op.replace("_", " ")} trend'), f'{op} trend')
        except Exception:
            st.empty()

section_head('Data quality watch', 'Issues that could affect interpretation or downstream analysis.')
qa = quality_actions(df)
if qa:
    for q in qa[:6]:
        st.markdown(f'<div class="finding"><b>{q["issue"]}</b> · {q["count"]:,}<br><span class="muted">{q["treatment"]}</span></div>', unsafe_allow_html=True)
else:
    st.success('No major automated data-quality issue was detected.')

section_head('Focused analysis', 'Build a specific comparison when the standard dashboard is not enough.')
custom = st.text_input('Describe the comparison or analysis you want', placeholder='Compare revenue by region')
st.caption('Examples: compare revenue by region, show cancellations by product, inspect SLA by month.')
if st.button('Build analysis', disabled=not custom.strip()):
    result, msg = custom_analysis_request(df, custom)
    st.session_state.custom_result = (result, msg)
if st.session_state.get('custom_result'):
    result, msg = st.session_state.custom_result
    st.info(msg)
    if result and result.get('type') == 'bar':
        show(px.bar(result['data'], x=result['x'], y=result['y'], title=result['title']))
    elif result and result.get('type') == 'kpi':
        st.metric(result['metric'], f"{result['total']:,.2f}")

section_head('Download this dashboard')
st.caption('Export the current KPIs, selected findings and charts as a standalone HTML file.')
if st.button('Prepare dashboard download'):
    from src.dashboard_export import build_dashboard_html
    html = build_dashboard_html(
        'BizLens Dashboard',
        items,
        auto_insights(df, metric, dim, date)[:6],
        st.session_state.get('_dashboard_figs', []),
    )
    st.session_state['_dashboard_html'] = html
if st.session_state.get('_dashboard_html'):
    st.download_button(
        'Download dashboard (HTML)',
        data=st.session_state['_dashboard_html'],
        file_name='bizlens_dashboard.html',
        mime='text/html',
    )

refresh_workspace()
