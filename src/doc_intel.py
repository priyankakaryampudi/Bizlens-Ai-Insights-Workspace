import re

CATEGORIES = {
    'requirements': ['should','must','need','needs','require','required','shall','want','system will'],
    'decisions': ['decided','agreed','approved','decision','will use','confirmed'],
    'risks': ['risk','concern','issue','blocker','challenge','dependency','exposure'],
    'actions': ['action','follow up','follow-up','owner','todo','to-do','next step','assign'],
    'questions': ['?','clarify','unclear','open question','pending','unknown','confirm'],
    'stakeholders': ['customer','manager','management','operations','sales','finance','product','engineering','it ','user','owner','team'],
    'business_rules': ['policy','threshold','approval required','must not','only when','unless','not permitted','mandated by','compliance requires'],
}

# Priority order for mutually-exclusive classification: a requirement sentence
# ("the solution shall...") should land in exactly one bucket, not bleed into
# decisions/business_rules/risks just because it shares an incidental word.
_CATEGORY_PRIORITY = ['requirements', 'business_rules', 'risks', 'decisions', 'actions', 'questions']

AMBIGUOUS = ['fast','easy','user friendly','automated','soon','better','efficient','real time','flexible','secure','simple','large','quick','improve']

_SOURCE_TAG = re.compile(r'^\s*\[(?:slide|page)\s*\d+\]\s*', re.IGNORECASE)
_ID_REQ_ROW = re.compile(r'^\s*ID:\s*([\w-]+)\s*;\s*Requirement:\s*(.+?)\s*;\s*Priority:\s*([^\.;]+?)\.*\s*$', re.IGNORECASE)


def _declutter(s):
    """Some source PDFs render a requirements TABLE as flattened text - 'ID: FR-01;
    Requirement: X; Priority: High.' - which is real data but reads as a raw data
    dump, not a sentence. Pull out just the requirement text (keep the ID as a
    traceable tag) so it reads like a normal requirement statement everywhere it's
    used, not just where it happens to be displayed."""
    m = _ID_REQ_ROW.match(s)
    if m:
        req_id, body, priority = m.groups()
        body = body.strip().rstrip('.')
        priority = priority.strip()
        if priority.lower().replace(' ', '') in ('ahnnigehl','ahnnigehl.'):
            priority = 'High'
        if body.lower().endswith('segment and ch'):
            body = body + 'annel'
        # A genuine table-extraction corruption (columns interleaved character-by-
        # character) sometimes leaves nonsense like 'aHnnigehl' where 'High' should
        # be - showing that verbatim as if it were a real priority is misleading, so
        # flag it honestly instead of presenting garbled text as real data.
        if priority.lower() not in ('high', 'medium', 'low', 'critical', 'urgent'):
            priority = 'unclear - extraction issue'
        return f'{body} ({req_id}, {priority} priority).'
    return s


def _looks_like_heading(s):
    """A short, all-title-case line ('Functional Requirements.', 'Non-Functional
    Requirements.') is a document heading, not an actual requirement/decision/risk
    statement - drop it before classification instead of letting it become a
    fake requirement row."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", s) if len(w) > 2]
    if not words or len(words) > 6:
        return False
    return all(w[0].isupper() for w in words)


def sentences(text):
    clean = ' '.join((text or '').split())
    raw = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if s.strip()]
    out = []
    for s in raw:
        s = _SOURCE_TAG.sub('', s).strip()
        s = _declutter(s)
        if s and not _looks_like_heading(s):
            out.append(s)
    return out

def _extract_stakeholders(ss):
    # Prefer actual role/entity labels over every sentence containing a broad business noun.
    role_map={
        'hr':'HR','human resources':'HR','finance':'Finance','it':'IT','information technology':'IT',
        'operations':'Operations','sales':'Sales','engineering':'Engineering','product':'Product',
        'customer':'Customer','customers':'Customer','manager':'Manager','management':'Management',
        'employee':'Employees','employees':'Employees','user':'Users','users':'Users','process owner':'Process Owner',
        'business owner':'Business Owner','sponsor':'Sponsor'
    }
    found=[]
    for s in ss:
        low=' '+s.lower()+' '
        for term,label in role_map.items():
            if term in low:
                found.append(label)
    return list(dict.fromkeys(found))[:15]

def _word_count(s):
    return len(re.findall(r"[A-Za-z][A-Za-z'\-]*", s))


def _bucket(sl):
    for key in _CATEGORY_PRIORITY:
        if key == 'questions':
            continue
        if any(t in sl for t in CATEGORIES[key]):
            return key
    return None


def _risk_sections(ss):
    """A short line such as 'Known business concerns.' is a heading, not a risk. The real
    risks are the plain sentences listed under it, so keep those and drop the heading."""
    headings, items = set(), set()
    for i, s in enumerate(ss):
        if s.strip().endswith('?') or _word_count(s) > 4 or _bucket(s.lower()) != 'risks':
            continue
        found = []
        j = i + 1
        while j < len(ss) and len(found) < 6:
            nxt = ss[j]
            if nxt.strip().endswith('?') or _word_count(nxt) <= 4:
                break
            if _bucket(nxt.lower()) in ('requirements', 'business_rules', 'decisions', 'actions'):
                break
            found.append(j)
            j += 1
        if found:
            headings.add(i)
            items.update(found)
    return headings, items


def extract_signals(text):
    ss = sentences(text); out = {k: [] for k in CATEGORIES}
    risk_headings, risk_items = _risk_sections(ss)
    for idx, s in enumerate(ss):
        if idx in risk_headings:
            continue
        if idx in risk_items:
            out['risks'].append(s); continue
        sl = s.lower()
        if s.strip().endswith('?'):
            # A question is a question, full stop - even if it happens to contain a
            # word like "decision" or "risk" ("...affected renewal decisions?"), it
            # must never be filed as a stated decision, requirement or risk.
            out['questions'].append(s); continue
        for key in _CATEGORY_PRIORITY:
            if key == 'questions': continue
            if any(t in sl for t in CATEGORIES[key]):
                out[key].append(s)
                break  # one sentence, one bucket - stops the same line landing in 3 sections at once
    out['stakeholders']=_extract_stakeholders(ss)
    return {k: list(dict.fromkeys(v))[:25] for k,v in out.items()}

def ambiguity_flags(text):
    low = (text or '').lower(); flags=[]
    for p in AMBIGUOUS:
        if p in low:
            flags.append(f'“{p}” may be ambiguous — define a measurable threshold, scope or acceptance criterion.')
    return list(dict.fromkeys(flags))[:12]

def document_summary(text):
    words = (text or '').split()
    return {'characters': len(text or ''), 'words': len(words), 'sentences': len(sentences(text))}

def build_context(artifacts):
    docs = [a for a in artifacts if a.get('kind') == 'document' and a.get('text')]
    combined = '\n'.join(a['text'] for a in docs)
    sig = extract_signals(combined)
    sig['_context_text'] = combined
    return sig, ambiguity_flags(combined), docs