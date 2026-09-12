import os
import re
import pandas as pd
from .analytics import (
    guess_metric, guess_dimension, guess_date, summary_stats, dimension_breakdown,
    trend, data_quality_findings, measure_options, categorical_columns, numeric_columns,
    match_field_from_text
)

try:
    from dotenv import load_dotenv
    import pathlib as _pathlib
    load_dotenv(_pathlib.Path(__file__).resolve().parent.parent / '.env')  # explicit: always find the project's own .env
    load_dotenv()  # fallback: also honor a .env in the current working directory
except Exception:
    pass


# --- Spec section 40: answer validation pass -------------------------------
# Applied as a post-processing step on every answer (AI or deterministic)
# before it reaches the user, not left to prompt instructions alone.

_CAUSAL_PATTERNS = [
    (re.compile(r'\bis causing\b', re.IGNORECASE), 'may be associated with'),
    (re.compile(r'\bcauses\b', re.IGNORECASE), 'is associated with'),
    (re.compile(r'\bcaused by\b', re.IGNORECASE), 'associated with'),
    (re.compile(r'\bdue to\b', re.IGNORECASE), 'potentially related to'),
]
_CAUSAL_HEDGES = ('may ', 'could ', 'hypothes', 'evidence does not', 'not establish',
                   'validated', 'confirmed', 'associat', 'correlat', 'potential',
                   'candidate', 'not yet', 'has not been')


def _soften_causal_language(text):
    """Reject unhedged 'X caused Y' phrasing per spec section 2/40 - replace
    it with association language unless the sentence already hedges."""
    if not text:
        return text
    sentences = re.split(r'(?<=[.!?])\s+', text)
    changed = False
    out = []
    for s in sentences:
        low = s.lower()
        if any(h in low for h in _CAUSAL_HEDGES):
            out.append(s)
            continue
        new_s = s
        for pat, repl in _CAUSAL_PATTERNS:
            if pat.search(new_s):
                new_s = pat.sub(repl, new_s)
                changed = True
        out.append(new_s)
    result = ' '.join(out)
    if changed:
        result += '\n\n_Causal language above was automatically softened to reflect an observed association rather than proven causation._'
    return result


def _flag_unsupported_numbers(text, context):
    """Claim validation: numeric values in the answer that do not appear
    anywhere in the retrieved evidence context are flagged for the reader
    rather than silently trusted."""
    if not text or not context:
        return text
    def _norm(n):
        # Compare by numeric value, not by exact string: "319,955.00" (as
        # typically shown in an answer) and "319955.0000" (as typically
        # shown in a raw evidence context) are the same number and must not
        # be treated as unsupported just because the formatting differs.
        try:
            return round(float(n.replace(',', '')), 2)
        except ValueError:
            return None
    ctx_nums = {v for v in (_norm(n) for n in re.findall(r'\d[\d,]*(?:\.\d+)?', context)) if v is not None}
    ans_raw = re.findall(r'\d[\d,]*(?:\.\d+)?', text)
    unsupported = sorted({n for n in ans_raw if len(n.replace(',', '')) > 2 and _norm(n) not in ctx_nums})
    if unsupported:
        return text + f"\n\n_Note: the following figures could not be matched against the retrieved evidence context and should be verified before use: {', '.join(unsupported[:5])}._"
    return text


def validate_answer(text, context=None):
    """Run the answer-validation pass: soften unhedged causal claims, then
    flag any number that isn't traceable to the evidence context."""
    text = _soften_causal_language(text)
    if context:
        text = _flag_unsupported_numbers(text, context)
    return text


_PLACEHOLDER_KEYS = {
    'your_gemini_api_key_here', 'paste_your_key_here', 'your_openai_api_key_here',
    'your_api_key_here', 'changeme', 'replace_me', '',
}


def _looks_like_real_key(value):
    """Guard against unedited .env placeholder text being treated as a real key."""
    if not value:
        return False
    v = value.strip()
    if not v or v.lower() in _PLACEHOLDER_KEYS:
        return False
    if v.lower().startswith('paste_') or v.lower().startswith('your_') or 'here' in v.lower():
        return False
    return len(v) >= 8


def _session_ai():
    try:
        import streamlit as st
        return st.session_state.get('ai_provider_choice'), st.session_state.get('ai_api_key')
    except Exception:
        return None, None

def get_api_key():
    # Session-only key takes precedence and is never written to disk.
    _, session_key = _session_ai()
    for candidate in (session_key, os.getenv('GEMINI_API_KEY'), os.getenv('BIZLENS_API_KEY'), os.getenv('OPENAI_API_KEY')):
        if _looks_like_real_key(candidate):
            return candidate
    return None

def ai_provider():
    session_provider, session_key = _session_ai()
    if _looks_like_real_key(session_key) and session_provider:
        return session_provider
    if _looks_like_real_key(os.getenv('GEMINI_API_KEY')) or _looks_like_real_key(os.getenv('BIZLENS_API_KEY')):
        return 'Gemini'
    if _looks_like_real_key(os.getenv('OPENAI_API_KEY')):
        return 'OpenAI'
    return None


def ai_available():
    return bool(get_api_key())

def ai_status():
    provider = ai_provider()
    if provider:
        return {'configured': True, 'provider': provider, 'mode': 'AI synthesis + deterministic local evidence'}
    return {'configured': False, 'provider': None, 'mode': 'Deterministic local evidence only'}



def _field_from_question(question, fields):
    return match_field_from_text(question, fields)


def _evidence_context(artifacts, df, question, doc_signals=None, max_chars=12000):
    # Smaller than before on purpose: a 30k-char prompt was the main driver of
    # slow AI answers (more tokens in = more time before the first token out).
    # 12k is still generous for a targeted, question-relevant evidence pack.
    """Build a compact, question-relevant evidence pack rather than dumping the workspace."""
    chunks=[]; doc_signals=doc_signals or {}
    q_terms=set(re.findall(r'[a-zA-Z]{3,}', question.lower()))
    if df is not None:
        measures=measure_options(df)
        m=_field_from_question(question, measures) or guess_metric(df)
        dims=categorical_columns(df, 60)
        d=_field_from_question(question, dims) or guess_dimension(df)
        dt=guess_date(df)
        chunks.append(f'DATASET: {len(df):,} rows, {len(df.columns)} columns. FIELDS: '+', '.join(map(str,df.columns)))
        if m:
            stat=summary_stats(df,m)
            chunks.append(f'MEASURE {m}: total={stat["total"]:.4f}; mean={stat["mean"]:.4f}; median={stat["median"]:.4f}; usable={stat["usable"]}.')
        if m and d:
            g=dimension_breakdown(df,d,m,12)
            chunks.append(f'RELEVANT BREAKDOWN {m} BY {d}:\n{g.to_csv(index=False)}')
        if m and dt:
            t=trend(df,dt,m)
            chunks.append(f'RELEVANT TREND {m} BY {dt}:\n{t.tail(12).to_csv(index=False)}')
        if any(w in question.lower() for w in ['missing','quality','duplicate','outlier','suspicious']):
            chunks.append('DATA QUALITY:\n'+'\n'.join(data_quality_findings(df)))
    # Include only signal categories relevant to the question, otherwise a small balanced set.
    relevant=[]
    key_terms={'requirements':['requirement','shall','must','need'], 'decisions':['decision','agreed','approved'], 'risks':['risk','concern','blocker'], 'stakeholders':['stakeholder','owner','manager'], 'actions':['action','next step','follow up'], 'questions':['question','unclear','clarify']}
    for key, vals in doc_signals.items():
        if not vals: continue
        if any(t in question.lower() for t in key_terms.get(key,[key.rstrip('s')])) or key in ['requirements','risks']:
            relevant.extend((key,x) for x in vals[:8])
    for key,x in relevant[:30]: chunks.append(f'{key.upper()}: {x}')
    scored=[]
    for a in artifacts:
        for line in (a.get('text') or '').splitlines():
            score=sum(t in line.lower() for t in q_terms)
            if score: scored.append((score,a.get('name','source'),line.strip()))
    for _,name,line in sorted(scored,key=lambda x:(x[0],len(x[2])),reverse=True)[:20]:
        chunks.append(f'SOURCE {name}: {line}')
    return '\n\n'.join(chunks)[:max_chars]

def _gemini(question, context):
    from google import genai
    from google.genai import types
    key = get_api_key()
    if not key:
        raise RuntimeError('GEMINI_API_KEY is not configured')
    # vertexai=False pins this to the Gemini Developer API (plain API-key auth).
    # Without it, the SDK can auto-detect a Vertex AI / ADC environment (e.g. from
    # GOOGLE_CLOUD_PROJECT or GOOGLE_GENAI_USE_VERTEXAI being set) and switch to an
    # endpoint that expects an OAuth2 access token instead of an API key - which is
    # exactly the "expected OAuth 2 access token" 401 this app was hitting even with
    # a valid key configured.
    # A shorter timeout that fails fast into local evidence mode beats a long
    # silent wait for a slow/stuck request - the person just sees an answer
    # either way, so 30s of dead air before falling back served no purpose.
    client = genai.Client(api_key=key, vertexai=False, http_options=types.HttpOptions(timeout=15000))
    model = os.getenv('BIZLENS_MODEL', 'gemini-3.7-flash')
    prompt = f'''You are BizLens, a senior Business Analyst copilot.
Answer the user's exact question from the workspace evidence. Do not turn every question into a generic business summary.

Rules:
- Match the question to the relevant metric, dimension, period and document evidence.
- Use calculated workspace evidence before making an interpretation.
- Never invent numbers, facts, requirements, stakeholders or causal explanations.
- Correlation/concentration is an observation, not proof of causation.
- If evidence is insufficient, say exactly what is missing.
- If the user asks for a simple fact, answer in 1-3 sentences - do not force four sections or a long writeup.
- If the user asks why/what should we do, give the strongest evidence, a clearly labelled hypothesis, and 1-3 concrete next checks - nothing more.
- Use exact values from the evidence and keep units/percentages clear.
- Be direct and brief. Default to a short paragraph. Only use a list when there are genuinely 3+ distinct items, and if you do, put each item on its own line starting with "- " - never number items inline inside a sentence (e.g. never "...issues. 2. Enterprise Impact:...").
- Cite sources only once, on their own final line starting with "Sources:" - never mid-sentence in parentheses.
- Keep the whole answer under 120 words unless the question explicitly asks for a full list/table of evidence.

WORKSPACE EVIDENCE:
{context}

USER QUESTION:
{question}'''
    response = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=500, temperature=0.2),
    )
    text = (response.text or '').strip()
    if not text:
        raise RuntimeError('Gemini returned an empty answer')
    return text


def _openai(question, context):
    from openai import OpenAI
    client = OpenAI(api_key=get_api_key(), timeout=30.0)
    model = os.getenv('BIZLENS_MODEL', 'gpt-5.4-mini')
    prompt = f'''Answer the exact business question using only the evidence below. Never invent facts. Distinguish observation from causation. Keep simple factual questions concise.

EVIDENCE:
{context}

QUESTION:
{question}'''
    r = client.responses.create(model=model, input=prompt)
    return r.output_text.strip()


def answer_with_ai(question, context):
    provider = ai_provider()
    if provider == 'Gemini':
        return _gemini(question, context)
    if provider == 'OpenAI':
        return _openai(question, context)
    raise RuntimeError('No AI API key configured')


def _source_matches(question, artifacts, limit=8):
    terms = set(re.findall(r'[a-zA-Z]{3,}', question.lower()))
    q_norm = re.sub(r'[^a-z0-9]+', '', question.lower())
    scored = []
    for a in artifacts:
        for s in (a.get('text') or '').splitlines():
            s_norm = re.sub(r'[^a-z0-9]+', '', s.lower())
            if not s_norm or q_norm == s_norm or (len(q_norm) > 12 and q_norm in s_norm):
                continue
            s_terms = set(re.findall(r'[a-zA-Z]{3,}', s.lower()))
            overlap = len(terms & s_terms) / max(1, len(terms))
            score = sum(t in s.lower() for t in terms)
            if score:
                # A line that's itself a question and closely restates the
                # question's own wording ("investigate first?" vs "investigate
                # next?") is not evidence for an answer - it's the same question
                # asked elsewhere. Deprioritize rather than drop, in case nothing
                # better exists.
                is_restated_question = s.strip().endswith('?') and overlap >= 0.6
                scored.append((score, not is_restated_question, a['name'], s.strip()))
    scored.sort(key=lambda x: (x[1], x[0], len(x[3])), reverse=True)
    return [(sc, name, txt) for sc, _, name, txt in scored[:limit]]


_METRIC_SYNONYMS = ['order','orders','cancellation','cancellations','discount','discounts','conversion','conversions','churn','margin','margins','cost','costs','price','pricing','session','sessions','visit','visits','click','clicks','impression','impressions','ticket','tickets','complaint','complaints','refund','refunds','return','returns']

_STEM_WORDS = {'concentrat','declin','decreas','contribut','perform'}  # deliberately truncated stems - must stay substring-matched

def _has_word(q, word):
    """Whole-word match - a plain substring check wrongly fires 'sum' inside
    'summarize', or 'most' inside 'almost'. Multi-word phrases and deliberately
    truncated stems (matching 'concentrated'/'declining'/etc.) stay substring-matched."""
    if ' ' in word or word in _STEM_WORDS:
        return word in q
    # Match the word plus a real inflectional ending only (decision->decisions,
    # affect->affected/affecting) - NOT an arbitrary continuation, or short words
    # like 'sum'/'top' would wrongly fire inside unrelated words like 'summarize'/'topic'.
    return re.search(r'\b'+re.escape(word)+r'(?:s|es|ed|ing)?\b', q) is not None

def _any_word(q, words):
    return any(_has_word(q, w) for w in words)

def _unmatched_metric_word(question, df):
    """If the question names a common business metric that has no matching column,
    say so instead of silently substituting a different metric and answering as if
    that's what was asked - a swap the person never sees is worse than no answer."""
    if df is None: return None
    q = question.lower()
    cols_blob = ' '.join(str(c).lower().replace('_',' ') for c in df.columns)
    for w in _METRIC_SYNONYMS:
        if w in q and w.rstrip('s') not in cols_blob:
            return w
    return None


def _find_named_entity(q, g, dim_col):
    """If the question names a specific category value that actually exists in
    this dimension (e.g. 'East' when Region has an East row), report on that
    exact row - asking about a named entity must never get answered about a
    different one just because it happens to rank highest."""
    for val in g[dim_col].astype(str):
        if val.strip() and _has_word(q, val.lower()):
            return g[g[dim_col].astype(str) == val].iloc[0]
    return None


_LOW_PERFORMANCE_WORDS = ['least', 'lowest', 'smallest', 'minimal', 'worse', 'worst',
    'underperform', 'poor', 'poorly', 'weak', 'weaker', 'lower', 'lagging', 'struggl', 'declin']


def local_answer(question, df=None, artifacts=None, doc_signals=None):
    q = question.lower().strip(); artifacts = artifacts or []; doc_signals = doc_signals or {}
    if df is None and not artifacts:
        return 'Upload at least one business source so I can answer from evidence.'

    m_named = _field_from_question(question, measure_options(df)) if df is not None else None
    d = _field_from_question(question, categorical_columns(df, 60)) if df is not None else None
    m = m_named or (guess_metric(df) if df is not None else None)
    d = d or (guess_dimension(df) if df is not None else None)
    dt = guess_date(df) if df is not None else None
    missing_word = _unmatched_metric_word(question, df) if not m_named else None
    lines = []

    if _any_word(q, ["what don't we know", 'what dont we know', 'known unknowns', "what do we not know", 'unknowns']):
        # Spec section 27: retrieve from the gaps/questions model directly,
        # prioritized - not a generic "further analysis is needed" line.
        items = []
        for x in (doc_signals or {}).get('questions', [])[:6]:
            xl = str(x).lower()
            priority = 'Critical' if any(w in xl for w in ['revenue', 'cancel', 'risk', 'loss']) else 'High' if any(w in xl for w in ['sla', 'complaint', 'delay']) else 'Medium'
            items.append((priority, x))
        order = {'Critical': 0, 'High': 1, 'Medium': 2}
        items.sort(key=lambda t: order.get(t[0], 3))
        if items:
            lines = ['**Direct answer: known unknowns**'] + [f'{i+1}. ({p}) {x}' for i, (p, x) in enumerate(items)]
        else:
            lines = ['**Direct answer:** No open question has been recorded in the connected evidence yet - that itself may be a gap worth confirming with the business owner.']
    elif _any_word(q, ['show me evidence', 'show evidence', 'what evidence', 'source for that', 'where does that come from', 'cite your source']):
        # Spec section 26: return the actual evidence references, not "the
        # documents suggest..." - name the source file for each item shown.
        parts = []
        for a in (artifacts or [])[:6]:
            name = a.get('name', 'document')
            snippet = str(a.get('text', ''))[:160].strip()
            if snippet: parts.append(f'- **{name}**: {snippet}{"…" if len(str(a.get("text",""))) > 160 else ""}')
        if df is not None:
            parts.append(f'- **Connected dataset**: {len(df):,} rows available for calculation - ask a specific data question to see the exact computed value.')
        lines = ['**Direct answer: evidence sources connected to this workspace**'] + (parts or ['No source evidence is connected yet.'])
    elif _any_word(q, ['summarize', 'summary', 'overview', 'recap']):
        parts = []
        if df is not None and m:
            s = summary_stats(df, m)
            parts.append(f'**Data:** {len(df):,} records connected. Total {m} is {s["total"]:,.2f}; average is {s["mean"]:,.2f}.')
        cat_labels = {'requirements': 'requirement(s)', 'risks': 'risk(s)', 'decisions': 'decision(s)', 'questions': 'open question(s)', 'stakeholders': 'stakeholder(s)'}
        cat_counts = [f'{len(doc_signals.get(k, []))} {label}' for k, label in cat_labels.items() if doc_signals.get(k)]
        if cat_counts:
            parts.append('**Documents:** ' + ', '.join(cat_counts) + ' found in the connected evidence.')
        if not parts:
            parts = ['Not enough connected evidence yet to summarize - upload a dataset or business document first.']
        lines = ['**Direct answer: workspace summary**'] + parts
    elif _has_word(q, 'caus'):
        # A yes/no causal question ("is X causing Y?") is a different, stronger
        # claim than association - the app's evidence-before-assumptions rule
        # means this is almost never a "yes" from correlation/document mentions
        # alone. Say so explicitly instead of drifting into a generic search.
        q_words = set(re.findall(r'[a-z]{4,}', q))
        related = None
        for key in ('risks', 'questions', 'decisions'):
            for x in (doc_signals or {}).get(key, []):
                if len(q_words & set(re.findall(r'[a-z]{4,}', str(x).lower()))) >= 2:
                    related = (key, x); break
            if related: break
        lines = ['**Direct answer:** The current evidence does not establish causation here - at most it shows association or a documented concern, which is a materially weaker claim than "causes."']
        if related:
            lines.append(f'**Document-supported context ({related[0]}):** {related[1]}')
        if df is not None and m:
            lines.append(f'**Data check:** No statistical test of this specific relationship has been run against {m} in this workspace yet.')
        lines.append('**Next step:** Validate directly - compare both quantities across the same segments and time periods, and check whether the pattern holds consistently, before treating this as a confirmed cause.')
    elif re.search(r'what should (we|i|management|the business|they)\b', q) or _any_word(q, ['recommend', 'next steps', 'what to do', 'what now']):
        parts = []
        if df is not None and m and d:
            g = dimension_breakdown(df, d, m, 10)
            if not g.empty:
                top = g.iloc[0]
                parts.append(f'1. **Investigate {d} drivers for {m}.** {top[d]} is the largest observed contributor ({top.total:,.2f}); the underlying cause is not yet established. Evidence: dataset. Confidence: Medium.')
        doc_hyps = ((doc_signals or {}).get('risks', [])[:1] + (doc_signals or {}).get('questions', [])[:1])
        for x in doc_hyps:
            frag = str(x).strip(); frag = frag if len(frag) <= 140 else frag[:139].rsplit(' ', 1)[0] + '…'
            parts.append(f'{len(parts)+1}. **Validate a documented concern.** "{frag}" is referenced in the connected documents but not yet checked against data. Evidence: document-supported. Confidence: Low.')
        if not parts:
            parts = ['Not enough connected evidence yet to recommend a specific action - upload a dataset or business document first.']
        lines = ['**Direct answer: recommended next steps**'] + parts + ['**Decision required:** Confirm which investigation to prioritize before committing to a corrective action.']
    elif df is not None and _any_word(q, ['duplicate', 'missing', 'quality', 'outlier', 'suspicious']):
        lines = ['**Direct answer**'] + [f'- {x}' for x in data_quality_findings(df)[:10]]
    elif df is not None and _any_word(q, ['why', 'reason', 'driver', 'contributor', 'affect', 'impact', 'concentrat']):
        # "most/least affected/impacted" is a causal/contribution question, not a plain
        # ranking request - it must not fall into the plain superlative branch below,
        # which would silently answer a different question (e.g. "highest revenue").
        # Verify that the claimed change/problem exists before searching for contributors.
        decline_claim=_any_word(q, ['declin','decreas','fall','drop'])
        if decline_claim and dt and m:
            t=trend(df,dt,m)
            if len(t)>=2:
                last,prev=t.iloc[-1],t.iloc[-2]
                if float(last.change_pct) >= 0:
                    lines=[f'**Evidence check:** I cannot confirm a latest-period decline in {m}. The latest period changed by {last.change_pct:+.1f}% ({prev[m]:,.2f} → {last[m]:,.2f}).', '**Next step:** Specify the period you mean or investigate a different measure.']
                else:
                    lines=[f'**Evidence check:** {m} declined {abs(last.change_pct):.1f}% in the latest period ({prev[m]:,.2f} → {last[m]:,.2f}).']
        if not lines and d and m:
            g = dimension_breakdown(df, d, m, 10)
            if not g.empty:
                named_row = _find_named_entity(q, g, d)
                leader = g.iloc[0]
                if named_row is not None:
                    row = named_row
                    if str(row[d]) == str(leader[d]):
                        lines = [f'**Direct answer:** {row[d]} is the largest observed contributor to {m} at {row.total:,.2f}.', '**Evidence boundary:** this shows concentration, not causation.', f'**Next check:** Compare {row[d]} against the remaining groups across time and another available dimension, and validate against the actual business event (e.g. cancellations, complaints) rather than {m} alone.']
                    else:
                        gap = leader.total - row.total
                        lines = [f'**Direct answer:** {row[d]} has {m} of {row.total:,.2f}, compared with {leader[d]} (the highest) at {leader.total:,.2f} - a gap of {gap:,.2f}.', '**Evidence boundary:** this establishes a performance difference, not its cause.', f'**Next check:** Compare {row[d]} against {leader[d]} across time and another available dimension, and validate against the actual business event (e.g. cancellations, complaints) rather than {m} alone.']
                else:
                    low = _any_word(q, _LOW_PERFORMANCE_WORDS)
                    row = g.iloc[-1] if low else g.iloc[0]
                    lines = [f'**Direct answer:** {row[d]} is the {"smallest" if low else "largest"} observed contributor to {m} at {row.total:,.2f}.', '**Evidence boundary:** this shows concentration, not causation.', f'**Next check:** Compare {row[d]} against the remaining groups across time and another available dimension, and validate against the actual business event (e.g. cancellations, complaints) rather than {m} alone.']
        elif not lines:
            lines = ['**Direct answer:** I need a usable business measure and dimension to investigate contributors.']
    elif df is not None and _any_word(q, ['highest', 'top', 'best', 'largest', 'lowest', 'bottom', 'worst', 'smallest', 'most', 'least']) and d and m:
        g = dimension_breakdown(df, d, m, 50)
        if not g.empty:
            low = _any_word(q, _LOW_PERFORMANCE_WORDS)
            row = g.iloc[-1] if low else g.iloc[0]
            direction = 'lowest' if low else 'highest'
            lines = [f'**Direct answer:** {row[d]} has the {direction} {m} at {row.total:,.2f}.', f'**Evidence:** {g.iloc[0][d]} = {g.iloc[0].total:,.2f}; {g.iloc[-1][d]} = {g.iloc[-1].total:,.2f}.']
    elif df is not None and _any_word(q, ['average', 'mean', 'median', 'total', 'sum', 'how many', 'number of', 'count of']):
        target = 'median' if 'median' in q else 'mean' if ('mean' in q or 'average' in q) else 'total'
        s = summary_stats(df, m); val = s[target]
        label = target.title()
        lines = [f'**Direct answer:** {label} {m} is {val:,.2f}.']
    elif df is not None and _any_word(q, ['trend', 'change', 'growth', 'decline', 'increase', 'decrease']):
        if dt:
            t = trend(df, dt, m)
            if len(t) >= 2:
                last, prev = t.iloc[-1], t.iloc[-2]
                lines = [f'**Direct answer:** {m} {"increased" if last.change_pct >= 0 else "declined"} {abs(last.change_pct):.1f}% in the latest period ({prev[m]:,.2f} → {last[m]:,.2f}).']
            else:
                lines = ['**Direct answer:** There are not enough valid periods for a reliable trend.']
        else:
            lines = ['**Direct answer:** I could not identify a reliable date or period field.']
    elif _any_word(q, ['requirement', 'approval', 'stakeholder', 'decision', 'risk', 'meeting', 'document', 'policy', 'process', 'question', 'open item']):
        key_map = {'requirement': 'requirements', 'approval': 'business_rules', 'stakeholder': 'stakeholders', 'decision': 'decisions', 'risk': 'risks', 'meeting': 'actions', 'policy': 'business_rules', 'process': 'requirements', 'question': 'questions', 'open item': 'questions'}
        singular = {'requirements': 'requirement', 'business_rules': 'business rule', 'stakeholders': 'stakeholder', 'decisions': 'decision', 'risks': 'risk', 'actions': 'action item', 'questions': 'open question'}
        matched_term = next((term for term in key_map if term in q), None)
        found = []
        for term, key in key_map.items():
            if term in q:
                found.extend(doc_signals.get(key, [])[:8])
        found = list(dict.fromkeys(found))
        if found:
            key = next((key for term, key in key_map.items() if term in q), None)
            noun = singular.get(key, 'item')
            lines = [f'**Direct answer:** {len(found)} {noun}{"s" if len(found)!=1 else ""} {"were" if len(found)!=1 else "was"} found in the connected evidence.'] + [f'- {x}' for x in found[:5]]
        elif matched_term:
            # The category was explicitly asked about but is genuinely empty - say so
            # plainly instead of silently falling through to an unrelated generic answer.
            key = key_map[matched_term]
            noun = singular.get(key, 'item')
            lines = [f'**Direct answer:** No explicit {noun} was found in the connected evidence.', 'Upload the relevant document, or confirm this directly with the accountable stakeholder.']

    if not lines:
        matches = _source_matches(question, artifacts)
        if matches:
            _, top_name, top_text = matches[0]
            lines = [f'**Most relevant evidence:** {top_text}', f'_Source: {top_name}_']
            extra = [f'- {name}: {t}' for _, name, t in matches[1:3]]
            if extra:
                lines.append('**Also relevant:**')
                lines.extend(extra)
        elif df is not None:
            s = summary_stats(df, m)
            lines = [f'**Current evidence:** {m} totals {s["total"]:,.2f}. Ask for a specific metric, segment, period, requirement or quality issue.']
        else:
            lines = ['I could not find enough evidence to answer that specifically. Try naming a specific metric, region, product or document term.']
    if missing_word and m and lines and any(m in l for l in lines):
        # The requested metric doesn't exist as a column - the answer above used a
        # different one instead. Say so up front rather than let a confident-looking
        # answer to a different question pass as if it addressed what was actually asked.
        lines = [f"**Note:** This dataset has no '{missing_word}' field. Available measures: {', '.join(measure_options(df))}. Showing **{m}** instead."] + lines
    return '\n\n'.join(lines[:15])


def _record_ai_failure(exc):
    """Keep the diagnostic available for the developer without ever surfacing
    it in the answer text the end user sees (they asked AI synthesis to fail
    silently into local evidence mode, not to announce that it failed)."""
    try:
        import streamlit as st
        st.session_state['_ai_last_error'] = _diagnose_ai_error(exc)
    except Exception:
        pass


def _diagnose_ai_error(exc):
    """Turn a raw SDK exception into a plain-language, actionable reason instead
    of a bare class name like 'ClientError' - that alone tells the person nothing
    they can act on."""
    msg = str(exc)
    low = msg.lower()
    if 'api key not valid' in low or 'api_key_invalid' in low or ('invalid' in low and 'key' in low):
        reason = 'The API key was rejected as invalid. Re-check it was copied in full with no extra spaces.'
    elif ('404' in msg and 'model' in low) or ('not found' in low and 'model' in low):
        configured = os.getenv('BIZLENS_MODEL', 'gemini-3.7-flash')
        reason = f"The model '{configured}' was not found for this account/API version - AI providers retire model names often, so this is usually just a stale default. Try setting BIZLENS_MODEL in .env to a current model name (check ai.google.dev/gemini-api/docs/models for Gemini)."
    elif '429' in msg or 'quota' in low or 'rate limit' in low or 'resource_exhausted' in low:
        reason = 'The account has hit its rate limit or quota for this key.'
    elif '403' in msg or 'permission' in low or 'forbidden' in low:
        reason = 'The key does not have permission to call this model (check it is enabled for the Gemini API in Google AI Studio).'
    elif 'timeout' in low or 'timed out' in low:
        reason = 'The request timed out - the network connection to the AI provider was too slow or unreachable.'
    elif 'connection' in low or 'network' in low or 'dns' in low:
        reason = 'Could not reach the AI provider - check the internet connection.'
    else:
        reason = 'Unrecognized error - see the detail below.'
    detail = msg[:220] + ('...' if len(msg) > 220 else '')
    return f'{reason} ({type(exc).__name__}: {detail})'


def answer(question, artifacts, df, doc_signals):
    context = _evidence_context(artifacts, df, question, doc_signals)
    if ai_available():
        try:
            return validate_answer(answer_with_ai(question, context), context)
        except Exception as exc:
            _record_ai_failure(exc)
            return local_answer(question, df, artifacts, doc_signals)
    return validate_answer(local_answer(question, df, artifacts, doc_signals), context)

# --- BizLens query router: deterministic facts first, synthesis second ---
_INTENT_TYPES = ['FACT_LOOKUP','COMPARISON','TREND','DIAGNOSTIC','ROOT_CAUSE','RECOMMENDATION','REQUIREMENT','RISK','STAKEHOLDER','KPI','DATA_QUALITY','DOCUMENT_QUERY','GENERAL_WORKSPACE']


def classify_intent(question, df=None, doc_signals=None):
    """Spec section 21: a named intent type for display/traceability, separate
    from (and layered on top of) the routing logic that actually picks which
    answer strategy to run - that routing is already tested against the
    acceptance tests, so this labels it rather than replaces it."""
    q = question.lower().strip()
    if _any_word(q, ['duplicate', 'missing', 'quality', 'outlier', 'suspicious']): return 'DATA_QUALITY'
    if _has_word(q, 'caus') or _any_word(q, ['root cause', 'underlying reason']): return 'ROOT_CAUSE'
    if _any_word(q, ['why', 'affect', 'impact', 'concentrat', 'contribut']): return 'DIAGNOSTIC'
    if re.search(r'what should (we|i|management|the business|they)\b', q) or _any_word(q, ['recommend', 'next steps', 'what to do']): return 'RECOMMENDATION'
    if _any_word(q, ['stakeholder', 'owner', 'ownership', 'owns', 'accountable', 'responsible for']): return 'STAKEHOLDER'
    if _has_word(q, 'requirement'): return 'REQUIREMENT'
    if _has_word(q, 'risk'): return 'RISK'
    if _has_word(q, 'kpi') or _any_word(q, ['target', 'success measure']): return 'KPI'
    if _any_word(q, ['trend', 'over time', 'growth', 'declin']): return 'TREND'
    if _any_word(q, ['highest', 'lowest', 'best', 'worst', 'top', 'bottom', 'most', 'least', 'compare', 'versus', 'vs']): return 'COMPARISON'
    if _any_word(q, ['decision', 'meeting', 'policy', 'process', 'document', 'notes', 'question', 'open item']): return 'DOCUMENT_QUERY'
    if _any_word(q, ['summarize', 'summary', 'overview']): return 'GENERAL_WORKSPACE'
    if df is not None:
        fields = [str(c).lower().replace('_', ' ') for c in getattr(df, 'columns', [])]
        if any(f and f in q for f in fields): return 'FACT_LOOKUP'
    return 'GENERAL_WORKSPACE'


def classify_question(question, df=None, doc_signals=None):
    """Route by intent + actual workspace fields, not just a brittle keyword list."""
    q=question.lower().strip(); doc_signals=doc_signals or {}
    if df is not None:
        fields=[str(c).lower().replace('_',' ') for c in getattr(df,'columns',[])]
        field_hit=any(f and (f in q or any(tok in q for tok in f.split() if len(tok)>3)) for f in fields)
        data_intent=_any_word(q, ['total','sum','average','mean','median','highest','lowest','best','worst','top','bottom','most','least','perform','performance','trend','change','growth','decline','increase','decrease','correlation','compare','quality','missing','duplicate','outlier','show','calculate'])
        has_data=field_hit or data_intent
    else: has_data=False
    doc_intent=_any_word(q, ['requirement','stakeholder','decision','risk','meeting','policy','approval','process','document','ownership','notes','report','question','open item'])
    causal_or_decision=_any_word(q, ['why','cause','driver','recommend','what should','investigate','improve','affect','impact','concentrat','contribut'])
    if has_data and (doc_intent or causal_or_decision): return 'combined'
    if has_data: return 'data'
    if causal_or_decision and df is not None and any(doc_signals.values()): return 'combined'
    if doc_intent or causal_or_decision: return 'documents'
    return 'combined' if df is not None and any(doc_signals.values()) else ('data' if df is not None else 'documents')

def routed_answer(question, artifacts, df, doc_signals, objective='', investigations=None, recommendations=None):
    route=classify_question(question,df,doc_signals)
    investigations=investigations or []; recommendations=recommendations or []
    if ai_available():
        context=_evidence_context(artifacts,df,question,doc_signals)
        if objective: context += '\n\nWORKSPACE OBJECTIVE:\n'+objective
        if investigations: context += '\n\nSAVED INVESTIGATIONS:\n'+str(investigations[:3])
        try:
            return validate_answer(answer_with_ai(question,context), context)
        except Exception as exc:
            _record_ai_failure(exc)
            deterministic=local_answer(question,df,artifacts,doc_signals)
            return validate_answer(deterministic, context)
    context=_evidence_context(artifacts,df,question,doc_signals)
    deterministic=local_answer(question,df,artifacts,doc_signals)
    if route=='data':
        return validate_answer(deterministic, context)
    # Only pad with a broader evidence dump when the deterministic answer genuinely
    # found nothing - not stacked on top of an answer that already worked, which
    # is what was drowning real answers in unrelated category dumps before.
    weak = deterministic.startswith('I could not find enough evidence')
    if not weak:
        return validate_answer(deterministic, context)
    extra=[]
    for key in ['requirements','decisions','risks','questions']:
        vals=(doc_signals or {}).get(key,[])[:3]
        if vals: extra.append(f'**{key.title()} evidence:**\n'+'\n'.join('- '+str(v) for v in vals))
    if investigations:
        inv=investigations[-1]
        extra.append(f'**Saved investigation:** {inv.get("focus","Investigation")}')
    if recommendations:
        titles=[x.get('title','Recommendation') for x in recommendations[:3]]
        extra.append('**Related recommendations:**\n'+'\n'.join('- '+x for x in titles))
    return validate_answer(deterministic + ('\n\n' + '\n\n'.join(extra) if extra else ''), context)
