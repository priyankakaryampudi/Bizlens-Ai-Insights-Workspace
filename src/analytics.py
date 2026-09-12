import re
import numpy as np
import pandas as pd


def numeric_columns(df):
    return list(df.select_dtypes(include=np.number).columns)


def is_year_like(df, col):
    if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
        return False
    x = pd.to_numeric(df[col], errors='coerce').dropna()
    return len(x) > 0 and x.between(1900, 2100).mean() > .8 and x.nunique() > 2


def categorical_columns(df, max_unique=60):
    out = []
    for c in df.columns:
        n = df[c].nunique(dropna=True)
        if 1 < n <= max_unique and (
            pd.api.types.is_object_dtype(df[c])
            or pd.api.types.is_string_dtype(df[c])
            or isinstance(df[c].dtype, pd.CategoricalDtype)
            or pd.api.types.is_bool_dtype(df[c])
        ):
            out.append(c)
    return out


def date_columns(df):
    out = []
    for c in df.columns:
        name = str(c).lower()
        if any(k in name for k in ['date', 'month', 'time', 'period', 'year']):
            p = pd.to_datetime(df[c], errors='coerce', format='mixed')
            if p.notna().mean() > .6:
                out.append(c)
    return out


def measure_options(df):
    return ['Record count'] + [c for c in numeric_columns(df) if not is_year_like(df, c)]


def metric_is_count(metric):
    return metric == 'Record count'


def _name_score(name, words):
    n = str(name).lower().replace('_', ' ')
    score = 0
    for i, w in enumerate(words):
        if w in n:
            score = max(score, 1000 - i * 20 + min(len(w), 12))
    return score


def _objective_field_match(objective, fields):
    """Match a stated business objective against column names, tolerating simple
    singular/plural differences (e.g. 'cancellations rising' -> 'Cancellations').
    Returns the best-matching field name, or None if the objective names nothing
    in `fields`."""
    if not objective or not fields:
        return None
    obj = str(objective).lower()
    obj_words = set(re.findall(r'[a-z]{3,}', obj))
    if not obj_words:
        return None

    def variants(word):
        v = {word}
        if word.endswith('ies'):
            v.add(word[:-3] + 'y')
        if word.endswith('es'):
            v.add(word[:-2])
        if word.endswith('s') and not word.endswith('ss'):
            v.add(word[:-1])
        v.add(word + 's')
        return v

    best, best_len = None, 0
    for f in fields:
        name = str(f).lower().replace('_', ' ')
        name_words = re.findall(r'[a-z]{3,}', name)
        if not name_words:
            continue
        hit = 0
        for w in name_words:
            if variants(w) & obj_words or w in obj:
                hit += len(w)
        if hit and hit > best_len:
            best, best_len = f, hit
    return best


def guess_metric(df, objective=None):
    nums = [c for c in numeric_columns(df) if not is_year_like(df, c)]
    if not nums:
        return 'Record count' if len(df) else None

    # What the user actually asked about wins over any generic keyword heuristic.
    named = _objective_field_match(objective, nums)
    if named:
        return named

    # Business measures should win over operational rates/IDs.
    strong = ['revenue', 'sales', 'net sales', 'gross sales', 'profit', 'gross profit', 'amount', 'gmv', 'turnover']
    medium = ['orders', 'units', 'quantity', 'customers', 'transactions', 'cost', 'price', 'value', 'tickets', 'headcount']
    weak = ['score', 'rating', 'duration', 'count']
    excluded = ['rate', 'percent', 'pct', 'ratio', 'index', 'year', 'id', 'latitude', 'longitude']

    def score(c):
        n = str(c).lower().replace('_', ' ')
        s = _name_score(n, strong) * 5 + _name_score(n, medium) * 2 + _name_score(n, weak)
        if any(x in n for x in excluded):
            s -= 1500
        # Avoid choosing a nearly constant technical field as the primary measure.
        vals = pd.to_numeric(df[c], errors='coerce').dropna()
        if len(vals) and vals.nunique() <= 1:
            s -= 2000
        return s

    return max(nums, key=score)


def guess_date(df):
    cols = date_columns(df)
    if cols:
        return cols[0]
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]):
            continue  # numeric fields (revenue, ratings, ids) must never be reinterpreted as epoch timestamps
        p = pd.to_datetime(df[c], errors='coerce', format='mixed')
        if p.notna().mean() > .85 and p.nunique(dropna=True) > 2:
            return c
    return None


def guess_dimension(df, objective=None):
    cats = categorical_columns(df)
    if not cats:
        return None
    named = _objective_field_match(objective, cats)
    if named:
        return named
    preferred = ['region', 'country', 'market', 'segment', 'customer', 'product', 'category', 'department', 'channel', 'platform', 'city', 'team', 'status', 'type', 'role']
    return max(cats, key=lambda c: _name_score(c, preferred))


def measure_series(df, metric):
    if metric_is_count(metric):
        return pd.Series(np.ones(len(df)), index=df.index, dtype=float)
    return pd.to_numeric(df[metric], errors='coerce')


def profile(df):
    numeric = df.select_dtypes(include=np.number)
    outliers = 0
    outlier_fields = []
    for c in numeric.columns:
        if is_year_like(df, c):
            continue
        x = pd.to_numeric(df[c], errors='coerce').dropna()
        if len(x) > 4:
            q1, q3 = x.quantile([.25, .75]); iqr = q3 - q1
            if iqr:
                n = int(((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)).sum())
                if n:
                    outliers += n
                    outlier_fields.append((c, n))
    return {
        'rows': len(df), 'columns': len(df.columns),
        'missing': int(df.isna().sum().sum()),
        'duplicates': int(df.duplicated().sum()),
        'outliers': outliers,
        'outlier_fields': sorted(outlier_fields, key=lambda x: x[1], reverse=True),
        'numeric': len(numeric_columns(df)),
        'categorical': len(categorical_columns(df, 10000)),
    }


def summary_stats(df, metric):
    s = measure_series(df, metric).dropna()
    if s.empty:
        return {'total': 0, 'mean': 0, 'median': 0, 'min': 0, 'max': 0, 'std': 0, 'usable': 0}
    return {
        'total': float(s.sum()), 'mean': float(s.mean()), 'median': float(s.median()),
        'min': float(s.min()), 'max': float(s.max()), 'std': float(s.std() if len(s) > 1 else 0),
        'usable': len(s)
    }


def _period_series(raw, df, date_col):
    if pd.api.types.is_numeric_dtype(raw) and is_year_like(df, date_col):
        return pd.to_numeric(raw, errors='coerce'), 'year'
    parsed = pd.to_datetime(raw, errors='coerce', format='mixed')
    if parsed.notna().mean() < .5:
        return pd.Series(index=raw.index, dtype=object), 'unknown'
    return parsed.dt.to_period('M').astype(str), 'month'


def trend(df, date_col, metric):
    x = df[[date_col] + ([] if metric_is_count(metric) else [metric])].copy()
    x['_value'] = measure_series(x, metric)
    x['_period'], granularity = _period_series(x[date_col], df, date_col)
    x = x.dropna(subset=['_period', '_value'])
    if x.empty:
        return pd.DataFrame()
    t = x.groupby('_period')['_value'].sum().reset_index().rename(columns={'_period': date_col, '_value': metric})
    t = t.sort_values(date_col).reset_index(drop=True)
    t['change_pct'] = t[metric].pct_change() * 100
    t.attrs['granularity'] = granularity
    return t


def dimension_breakdown(df, dimension, metric, n=25, aggregation='sum'):
    if not dimension or dimension not in df.columns:
        return pd.DataFrame()
    x = df[[dimension]].copy()
    x['_value'] = measure_series(df, metric)
    x = x.dropna(subset=[dimension, '_value'])
    if x.empty:
        return pd.DataFrame()
    grouped = x.groupby(dimension)['_value']
    out = grouped.agg(total='sum', average='mean', records='count', median='median')
    if aggregation == 'mean':
        out = out.sort_values('average', ascending=False)
    else:
        out = out.sort_values('total', ascending=False)
    return out.head(n).reset_index()


def cross_breakdown(df, dim1, dim2, metric, n=60):
    if not dim1 or not dim2 or dim1 not in df.columns or dim2 not in df.columns:
        return pd.DataFrame()
    x = df[[dim1, dim2]].copy(); x['_value'] = measure_series(df, metric)
    x = x.dropna(subset=[dim1, dim2, '_value'])
    return x.groupby([dim1, dim2])['_value'].sum().reset_index().sort_values('_value', ascending=False).head(n)


def distribution(df, metric):
    return pd.DataFrame({'value': measure_series(df, metric).dropna()})


def missingness(df):
    out = df.isna().sum().sort_values(ascending=False).reset_index()
    out.columns = ['field', 'missing']
    out['missing_pct'] = (out.missing / max(len(df), 1) * 100).round(1)
    return out[out.missing > 0]


def correlation_table(df):
    nums = numeric_columns(df)
    return df[nums].corr(numeric_only=True).round(2) if len(nums) >= 2 else pd.DataFrame()


def top_numeric_correlations(df, limit=8):
    corr = correlation_table(df); pairs = []
    if corr.empty:
        return pairs
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            v = corr.loc[a, b]
            if pd.notna(v):
                pairs.append((a, b, float(v), abs(float(v))))
    return sorted(pairs, key=lambda x: x[3], reverse=True)[:limit]


def investigation_metrics(df, metric, dimension, n=50):
    g = dimension_breakdown(df, dimension, metric, n)
    if g.empty:
        return g
    total = float(g.total.sum())
    g['share_pct'] = g.total / total * 100 if total else 0
    g['rank'] = np.arange(1, len(g) + 1)
    g['vs_top_pct'] = (g.total / g.total.max() - 1) * 100 if g.total.max() else 0
    return g


def trend_contributors(df, date_col, metric, dimension):
    if not date_col or not dimension:
        return pd.DataFrame()
    x = df[[date_col, dimension]].copy(); x['_value'] = measure_series(df, metric)
    x['_period'], _ = _period_series(x[date_col], df, date_col)
    x = x.dropna(subset=['_period', dimension, '_value'])
    return x.groupby(['_period', dimension])['_value'].sum().reset_index()


def _fmt_metric(name, value):
    if abs(value) >= 1_000_000: return f'{value / 1_000_000:.2f}M'
    if abs(value) >= 1_000: return f'{value / 1_000:.1f}K'
    return f'{value:,.0f}'


def business_kpis(df, metric, dimension=None, date_col=None):
    s = summary_stats(df, metric)
    items = [{'label': f'Total {metric}', 'value': _fmt_metric(metric, s['total']), 'detail': f'{s["usable"]:,} usable records'}]
    if date_col:
        try:
            from .analytics import aligned_period_change
            aligned = aligned_period_change(df, date_col, metric, '')
        except Exception:
            aligned = None
        if aligned:
            items.append({'label': f'{aligned["previous_label"]} → {aligned["current_label"]}', 'value': f'{aligned["change_pct"]:+.1f}%', 'detail': f'{_fmt_metric(metric, aligned["previous"])} → {_fmt_metric(metric, aligned["current"])}'})
        else:
            t = trend(df, date_col, metric)
            if len(t) >= 2 and pd.notna(t.iloc[-1].change_pct):
                items.append({'label': 'Latest change', 'value': f'{t.iloc[-1].change_pct:+.1f}%', 'detail': f'{_fmt_metric(metric, t.iloc[-2][metric])} → {_fmt_metric(metric, t.iloc[-1][metric])}'})
    if dimension:
        g = dimension_breakdown(df, dimension, metric, 10)
        if not g.empty:
            items.append({'label': f'Top {dimension}', 'value': str(g.iloc[0][dimension])[:20], 'detail': _fmt_metric(metric, g.iloc[0].total)})
    items.append({'label': f'Average {metric}', 'value': _fmt_metric(metric, s['mean']), 'detail': f'Median {_fmt_metric(metric, s["median"])}'})
    if dimension:
        g = dimension_breakdown(df, dimension, metric, 10)
        if len(g) >= 2:
            items.append({'label': 'Leader vs lowest', 'value': _fmt_metric(metric, g.iloc[0].total - g.iloc[-1].total), 'detail': f'{g.iloc[0][dimension]} vs {g.iloc[-1][dimension]}'})
    return items[:5]


def auto_insights(df, metric, dimension=None, date_col=None):
    findings = []
    if not metric:
        return findings
    s = summary_stats(df, metric)
    if dimension:
        g = dimension_breakdown(df, dimension, metric, 15)
        if len(g) >= 2:
            top, bottom = g.iloc[0], g.iloc[-1]; total = g.total.sum()
            findings.append(f'{top[dimension]} leads {metric} at {_fmt_metric(metric, top.total)}, representing {top.total / total * 100:.1f}% of observed {metric}.')
            findings.append(f'{bottom[dimension]} is lowest at {_fmt_metric(metric, bottom.total)}, a {_fmt_metric(metric, top.total - bottom.total)} gap to the leader.')
    if date_col:
        t = trend(df, date_col, metric)
        if len(t) >= 2 and pd.notna(t.iloc[-1].change_pct):
            last, prev = t.iloc[-1], t.iloc[-2]
            direction = 'increased' if last.change_pct >= 0 else 'declined'
            findings.append(f'{metric} {direction} {abs(last.change_pct):.1f}% in the latest period ({_fmt_metric(metric, prev[metric])} → {_fmt_metric(metric, last[metric])}).')
    if not findings:
        findings.append(f'{metric} totals {_fmt_metric(metric, s["total"])} across {s["usable"]:,} usable records.')
    return list(dict.fromkeys(findings))[:5]



def quarterly_trend(df, date_col, metric):
    """Quarterly performance view used for business-period comparisons."""
    if not date_col or date_col not in df.columns or not metric:
        return pd.DataFrame()
    x = df[[date_col] + ([] if metric_is_count(metric) else [metric])].copy()
    x['_value'] = measure_series(x, metric)
    parsed = pd.to_datetime(x[date_col], errors='coerce', format='mixed')
    x['_period'] = parsed.dt.to_period('Q')
    x = x.dropna(subset=['_period', '_value'])
    if x.empty:
        return pd.DataFrame()
    out = x.groupby('_period')['_value'].sum().reset_index()
    out['period'] = out['_period'].astype(str)
    out['change_pct'] = out['_value'].pct_change() * 100
    return out.rename(columns={'_value': metric})[['period', metric, 'change_pct']]


def aligned_period_change(df, date_col, metric, context_text=''):
    """Compare periods at a business-meaningful grain.

    If the evidence explicitly discusses a quarter/Q4, compare quarters rather
    than comparing the last two months. Otherwise use the latest two monthly
    periods. This avoids false 'conflicts' caused by mismatched time grains.
    """
    text = str(context_text or '').lower()
    if date_col and metric and any(k in text for k in ['q1', 'q2', 'q3', 'q4', 'quarter', 'quarterly']):
        t = quarterly_trend(df, date_col, metric)
        if len(t) >= 2:
            return {'grain': 'quarter', 'current_label': t.iloc[-1]['period'], 'previous_label': t.iloc[-2]['period'],
                    'current': float(t.iloc[-1][metric]), 'previous': float(t.iloc[-2][metric]),
                    'change_pct': float(t.iloc[-1]['change_pct'])}
    t = trend(df, date_col, metric) if date_col and metric else pd.DataFrame()
    if len(t) >= 2 and pd.notna(t.iloc[-1].change_pct):
        return {'grain': t.attrs.get('granularity', 'period'), 'current_label': str(t.iloc[-1][date_col]),
                'previous_label': str(t.iloc[-2][date_col]), 'current': float(t.iloc[-1][metric]),
                'previous': float(t.iloc[-2][metric]), 'change_pct': float(t.iloc[-1]['change_pct'])}
    return None


def group_period_change(df, date_col, metric, dimension, group_value=None, context_text='', periods=2):
    """Compare the latest business period with the preceding one by dimension.
    Returns readable contribution shifts rather than statistical coefficients."""
    if not date_col or not metric or not dimension or dimension not in df.columns:
        return pd.DataFrame()
    parsed = pd.to_datetime(df[date_col], errors='coerce', format='mixed')
    if any(k in str(context_text or '').lower() for k in ['q1','q2','q3','q4','quarter','quarterly']):
        period = parsed.dt.to_period('Q')
    else:
        period = parsed.dt.to_period('M')
    x = df[[dimension]].copy()
    x['_period'] = period
    x['_value'] = measure_series(df, metric)
    x = x.dropna(subset=[dimension, '_period', '_value'])
    if group_value is not None:
        x = x[x[dimension] == group_value]
    vals = sorted(x['_period'].unique())
    if len(vals) < 2:
        return pd.DataFrame()
    prev, curr = vals[-2], vals[-1]
    g = x.groupby([dimension, '_period'])['_value'].sum().unstack(fill_value=0)
    if prev not in g.columns or curr not in g.columns:
        return pd.DataFrame()
    out = pd.DataFrame({dimension: g.index.astype(str), 'previous': g[prev].values, 'current': g[curr].values})
    out['delta'] = out['current'] - out['previous']
    out['change_pct'] = np.where(out['previous'] != 0, (out['current'] / out['previous'] - 1) * 100, np.nan)
    out.attrs['previous_period'] = str(prev); out.attrs['current_period'] = str(curr)
    return out.sort_values('delta').reset_index(drop=True)


def _find_column(df, candidates):
    low = {str(c).lower().replace('_', ' '): c for c in df.columns}
    for cand in candidates:
        if cand in low:
            return low[cand]
    for c in df.columns:
        name = str(c).lower().replace('_', ' ')
        if any(cand in name for cand in candidates):
            return c
    return None


def service_signal(df, date_col, metric, group_dim=None, group_value=None, context_text=''):
    """Return operational signals that can explain a business performance change.
    Uses level changes and rates, not generic correlation rankings."""
    if df is None or not len(df) or not date_col:
        return []
    base = df.copy()
    if group_dim and group_dim in base.columns and group_value is not None:
        base = base[base[group_dim] == group_value]
    parsed = pd.to_datetime(base[date_col], errors='coerce', format='mixed')
    if any(k in str(context_text or '').lower() for k in ['q1','q2','q3','q4','quarter','quarterly']):
        periods = parsed.dt.to_period('Q')
    else:
        periods = parsed.dt.to_period('M')
    base = base.assign(_period=periods)
    vals = sorted(base['_period'].dropna().unique())
    if len(vals) < 2:
        return []
    prev, curr = vals[-2], vals[-1]
    p = base[base['_period'] == prev]; c = base[base['_period'] == curr]
    out=[]
    sla = _find_column(base, ['sla achievement rate', 'sla', 'service level'])
    orders = _find_column(base, ['orders', 'order count'])
    tickets = _find_column(base, ['support tickets', 'tickets', 'complaints'])
    canc = _find_column(base, ['cancellations', 'cancellation', 'cancelled', 'cancel'])
    if sla:
        if orders:
            pw = pd.to_numeric(p[sla], errors='coerce'); cw = pd.to_numeric(c[sla], errors='coerce')
            po = pd.to_numeric(p[orders], errors='coerce'); co = pd.to_numeric(c[orders], errors='coerce')
            pv = (pw*po).sum()/po.sum() if po.sum() else pw.mean()
            cv = (cw*co).sum()/co.sum() if co.sum() else cw.mean()
        else:
            pv = pd.to_numeric(p[sla], errors='coerce').mean(); cv = pd.to_numeric(c[sla], errors='coerce').mean()
        if pd.notna(pv) and pd.notna(cv):
            out.append({'kind':'sla','label':'Service-level performance','previous':float(pv),'current':float(cv),
                        'delta':float(cv-pv),'detail':f'{cv*100:.1f}% vs {pv*100:.1f}% ({(cv-pv)*100:+.1f} percentage points)'})
    if tickets:
        pt = pd.to_numeric(p[tickets], errors='coerce').sum(); ct = pd.to_numeric(c[tickets], errors='coerce').sum()
        if orders:
            po = pd.to_numeric(p[orders], errors='coerce').sum(); co = pd.to_numeric(c[orders], errors='coerce').sum()
            pv = pt/po if po else 0; cv = ct/co if co else 0
            detail = f'{cv:.3f} per order vs {pv:.3f} per order'
        else:
            pv, cv = pt, ct; detail = f'{cv:,.0f} vs {pv:,.0f}'
        out.append({'kind':'tickets','label':'Support-ticket pressure','previous':float(pv),'current':float(cv),
                    'delta':float(cv-pv),'detail':detail})
    if canc:
        pc = pd.to_numeric(p[canc], errors='coerce').sum(); cc = pd.to_numeric(c[canc], errors='coerce').sum()
        out.append({'kind':'cancellations','label':'Cancellation volume','previous':float(pc),'current':float(cc),
                    'delta':float(cc-pc),'detail':f'{cc:,.0f} in the latest period vs {pc:,.0f} in the prior period'})
    return out

def data_quality_findings(df):
    p = profile(df); out = []
    if p['duplicates']: out.append(f'{p["duplicates"]:,} duplicate rows detected. Review before using row-level totals.')
    if p['missing']: out.append(f'{p["missing"]:,} missing cells detected across {sum(missingness(df).missing > 0)} fields.')
    for field, n in p['outlier_fields'][:4]: out.append(f'{field}: {n:,} potential IQR outliers flagged. Validate before removing.')
    for _, r in missingness(df).head(5).iterrows(): out.append(f'{r.field}: {r.missing_pct:.1f}% missing values.')
    return out


def quality_actions(df):
    actions = []
    if df.duplicated().sum():
        actions.append({'issue': 'Duplicate rows', 'count': int(df.duplicated().sum()), 'treatment': 'Review exact duplicates; remove only confirmed duplicates.', 'method': 'Duplicate review'})
    for _, r in missingness(df).head(12).iterrows():
        if pd.api.types.is_numeric_dtype(df[r.field]):
            treatment = 'Consider median only if missingness is non-structural; compare with mean and business meaning.'
        elif pd.api.types.is_object_dtype(df[r.field]) or pd.api.types.is_string_dtype(df[r.field]):
            treatment = 'Consider an explicit Unknown category; use mode only when the business meaning supports it.'
        else:
            treatment = 'Investigate source; do not infer blindly.'
        actions.append({'issue': f'Missing values: {r.field}', 'count': int(r.missing), 'treatment': treatment, 'method': 'Conditional treatment'})
    p = profile(df)
    for field, n in p['outlier_fields'][:8]:
        actions.append({'issue': f'Potential outliers: {field}', 'count': n, 'treatment': 'Flag and investigate; do not auto-delete.', 'method': 'IQR screening'})
    return actions


def _future_dates(last_label, periods, granularity='month'):
    if granularity == 'year':
        last = int(float(last_label)); return np.arange(last + 1, last + 1 + periods)
    last = pd.to_datetime(str(last_label) + '-01' if re.fullmatch(r'\d{4}-\d{2}', str(last_label)) else str(last_label), errors='coerce')
    return pd.date_range(last + pd.offsets.MonthBegin(1), periods=periods, freq='MS').astype(str)


def forecast(df, date_col, metric, periods=6):
    """Robust planning baseline: damped trend blended with recent level.
    It intentionally avoids pretending that a straight line is a precise prediction.
    """
    t = trend(df, date_col, metric)
    if len(t) < 4:
        return None
    t = t.dropna(subset=[metric]).reset_index(drop=True)
    y = t[metric].astype(float).to_numpy()
    n = len(y); idx = np.arange(n)

    # Fit a linear trend, then damp it so noisy recent jumps do not compound forever.
    coef = np.polyfit(idx, y, 1)
    slope = float(coef[0])
    level = float(np.mean(y[-min(3, n):]))
    slope = float(np.clip(slope, -0.08 * max(abs(level), 1), 0.08 * max(abs(level), 1)))
    damp = 0.72
    pred = []
    current = level
    for h in range(1, periods + 1):
        current = current + slope * (damp ** (h - 1))
        pred.append(max(current, 0))
    pred = np.asarray(pred)

    fitted = np.polyval(coef, idx)
    residuals = y - fitted
    sd = float(np.std(residuals, ddof=1)) if n > 2 else 0.0
    # Wider uncertainty when the series is noisy.
    band = max(sd * 1.35, abs(level) * 0.03)
    lower = np.maximum(pred - band, 0)
    upper = pred + band
    granularity = t.attrs.get('granularity', 'month')
    dates = _future_dates(t[date_col].iloc[-1], periods, granularity)
    return t, pd.DataFrame({date_col: dates, metric: pred, 'lower': lower, 'upper': upper})


def scenario(base, uplift=0, efficiency=0, risk=0):
    return base * (1 + uplift / 100) * (1 + efficiency / 100) * (1 - risk / 100)


def chart_candidates(df, metric, dimension=None, date_col=None):
    """Return only charts that are meaningful for the actual data shape."""
    charts = []
    if date_col:
        t = trend(df, date_col, metric)
        if len(t) >= 3: charts.append('trend')
    if dimension:
        g = dimension_breakdown(df, dimension, metric, 30)
        if not g.empty:
            charts.append('ranking')
            if 2 <= len(g) <= 8: charts.append('share')
            if len(g) >= 3: charts.append('box')
    dist = distribution(df, metric)
    if len(dist) >= 10: charts.append('distribution')
    nums = [c for c in numeric_columns(df) if c != metric and not is_year_like(df, c)]
    if nums:
        charts.append('relationship')
    dims = categorical_columns(df, 30)
    if len(dims) >= 2: charts.append('heatmap')
    return charts

def match_field_from_text(text, fields):
    """Find the field a user named in free text, preferring the longest/most
    specific match. Falls back to a fuzzy single-word match (e.g. a question
    saying just "segment" should still resolve to a column actually named
    "Customer_Segment") so a real, connected column doesn't get silently
    treated as unavailable just because the user didn't type its exact name."""
    q = str(text or '').lower().replace('_', ' ')
    matches = []
    for f in fields:
        name = str(f).lower().replace('_', ' ')
        if name in q:
            matches.append((len(name), f))
    if matches:
        return max(matches)[1]
    q_words = set(re.findall(r'[a-z]{3,}', q))
    fuzzy = []
    for f in fields:
        name_words = set(re.findall(r'[a-z]{3,}', str(f).lower().replace('_', ' ')))
        overlap = name_words & q_words
        if overlap:
            fuzzy.append((sum(len(w) for w in overlap), f))
    return max(fuzzy)[1] if fuzzy else None


_BREAKDOWN_WORDS = ['by ', 'across', 'per ', 'category', 'categories', 'segment', 'group', 'breakdown', 'break down', 'compare', 'split', 'each ', 'versus', ' vs ']


def custom_analysis_request(df, prompt):
    """Small deterministic NL analysis parser for common BA questions."""
    import pandas as pd
    p=(prompt or '').lower()
    metric=match_field_from_text(prompt, measure_options(df)) or guess_metric(df)
    dims=categorical_columns(df,60)
    dim=match_field_from_text(prompt, dims)
    wants_breakdown=any(w in p for w in _BREAKDOWN_WORDS)
    substituted=False
    if not dim and wants_breakdown and dims:
        # The user asked for a breakdown but didn't name a real column (e.g. "by
        # category" when the dataset's field is actually called "Product") - use
        # the closest available dimension instead of silently collapsing to a
        # bare total, and say so plainly rather than pretending it's what they asked.
        dim=guess_dimension(df, prompt)
        substituted=bool(dim)
    if metric is None: return None, 'I could not identify a usable numeric measure.'
    if dim:
        g=dimension_breakdown(df,dim,metric,20)
        prefix=f"No field matching that grouping was found - showing the closest available dimension, **{dim}**, instead. " if substituted else ''
        if any(w in p for w in ['average','mean']):
            tmp=df.groupby(dim,dropna=False)[metric].mean().reset_index(name='value').sort_values('value',ascending=False); return {'type':'bar','data':tmp,'x':dim,'y':'value','title':f'Average {metric} by {dim}'}, prefix+f'Calculated average {metric} by {dim}.'
        return {'type':'bar','data':g,'x':dim,'y':'total','title':f'{metric} by {dim}'}, prefix+f'Calculated {metric} by {dim}.'
    if wants_breakdown and dims:
        return {'type':'kpi','metric':metric,'total':float(pd.to_numeric(df[metric],errors='coerce').sum())}, f"Could not match that grouping to a field in this dataset. Available dimensions: {', '.join(dims)}. Showing the overall total instead."
    return {'type':'kpi','metric':metric,'total':float(pd.to_numeric(df[metric],errors='coerce').sum())}, f'Calculated total {metric}.'
