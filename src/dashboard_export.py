"""Single-file, self-contained HTML dashboard export: KPIs + all charts in one
downloadable file that opens in any browser (no Chrome/kaleido dependency,
so it works on any machine without extra system installs).

Rendering notes (why it's built this way):
- plotly.js is embedded exactly ONCE via plotly.offline.get_plotlyjs() in its
  own <script> tag, before any chart markup. Every chart then uses
  include_plotlyjs=False and only emits its own `Plotly.newPlot(...)` call.
  Previously, the first chart embedded its own copy of the library
  (include_plotlyjs=True) while the rest assumed it was already loaded - two
  different code paths for the "same" library reference. Using one code path
  for every chart removes that asymmetry entirely, which is what was behind
  charts after the first rendering unstyled/black.
- Each chart gets an explicit, unique div_id instead of relying on an
  auto-generated one, so there is never any chance of two charts sharing a
  container.
- Layout uses a fixed-size CSS grid (explicit pixel width/height per card)
  instead of flexbox with '100%'/'responsive' sizing. Percentage-based
  responsive sizing inside a flex container can initialize against a
  not-yet-resolved (zero) width on first paint; fixed pixel dimensions avoid
  that race entirely and keep the exported file's layout predictable in any
  browser.
- A brand colorway is set explicitly on every figure before export, so bar/
  pie/histogram/scatter traces always carry an explicit color instead of
  depending on template inheritance resolving correctly at render time.
"""
import plotly.offline as pyo

BRAND_DARK = '#1F2A24'
BRAND_ACCENT = '#4B5D3A'
BRAND_LINE = '#C9C2AE'
CHART_COLORWAY = ['#4B5D3A', '#B4703B', '#6E8FA3', '#A63D40', '#8C6BAE', '#C9A227']

CHART_WIDTH = 560
CHART_HEIGHT = 380


def build_dashboard_html(title, kpi_items, findings, figures):
    """kpi_items: list of {'label','value','detail'}; findings: list of str;
    figures: list of (chart_title, plotly Figure)."""
    kpi_html = ''.join(
        f'<div class="kpi"><div class="kpi-label">{k["label"]}</div>'
        f'<div class="kpi-value">{k["value"]}</div>'
        f'<div class="kpi-detail">{k.get("detail","")}</div></div>'
        for k in kpi_items
    )
    findings_html = ''.join(f'<div class="finding">{f}</div>' for f in findings) or '<p class="muted">No findings available.</p>'

    chart_blocks = []
    for i, (chart_title, fig) in enumerate(figures):
        fig.update_layout(
            autosize=False, width=CHART_WIDTH, height=CHART_HEIGHT,
            margin=dict(t=40, l=10, r=10, b=10), colorway=CHART_COLORWAY,
        )
        chart_html = fig.to_html(
            full_html=False, include_plotlyjs=False,
            config={'displayModeBar': False, 'responsive': False},
            div_id=f'bizlens-chart-{i}',
        )
        chart_blocks.append(f'<div class="chart-card"><h3>{chart_title}</h3>{chart_html}</div>')
    charts_html = ''.join(chart_blocks)
    plotly_js = pyo.get_plotlyjs() if figures else ''

    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<script>{plotly_js}</script>
<style>
body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; background: #FFFDF8; color: {BRAND_DARK}; margin: 0; padding: 32px 40px; }}
h1 {{ font-family: Georgia, serif; color: {BRAND_DARK}; border-bottom: 2px solid {BRAND_ACCENT}; padding-bottom: 12px; }}
h2 {{ font-family: Georgia, serif; color: {BRAND_DARK}; border-bottom: 1px solid {BRAND_LINE}; padding-bottom: 6px; margin-top: 36px; }}
.kpi-row {{ display: flex; gap: 18px; flex-wrap: wrap; margin: 18px 0; }}
.kpi {{ background: white; border: 1px solid {BRAND_LINE}; border-radius: 10px; padding: 16px 20px; min-width: 160px; flex: 1; }}
.kpi-label {{ font-size: 12px; color: #716F67; text-transform: uppercase; letter-spacing: .04em; }}
.kpi-value {{ font-size: 26px; font-weight: 700; color: {BRAND_DARK}; margin: 4px 0; }}
.kpi-detail {{ font-size: 12px; color: {BRAND_ACCENT}; }}
.finding {{ background: white; border-left: 3px solid {BRAND_ACCENT}; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px; }}
.chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, {CHART_WIDTH}px); gap: 18px; justify-content: start; }}
.chart-card {{ background: white; border: 1px solid {BRAND_LINE}; border-radius: 10px; padding: 14px; width: {CHART_WIDTH}px; overflow: hidden; }}
.chart-card h3 {{ margin-top: 0; font-size: 14px; color: {BRAND_DARK}; }}
.muted {{ color: #716F67; }}
.footer {{ margin-top: 40px; font-size: 11px; color: #716F67; text-align: center; }}
</style></head>
<body>
<h1>{title}</h1>
<h2>Executive dashboard</h2>
<div class="kpi-row">{kpi_html}</div>
<h2>What matters most</h2>
{findings_html}
<h2>Charts</h2>
<div class="chart-grid">{charts_html}</div>
<div class="footer">Prepared with BizLens - evidence-based business analysis</div>
</body></html>'''
