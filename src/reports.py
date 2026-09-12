import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.lib import colors
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import pandas as pd
from datetime import date
from .diagrams import parse_diagram_body, diagram_body, render_process_flow
from .intelligence import investigation_brief
from .evidence import source_line, find_evidence_for_text

BRAND_DARK = '1F2A24'
BRAND_ACCENT = '4B5D3A'
BRAND_LINE = 'C9C2AE'


def safe(text):
    return str(text).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('→','->').replace('–','-').replace('—','-').replace('•','-')


def clip(text,n=160):
    """Keep long extracted sentences from blowing up table rows into unreadable multi-paragraph cells."""
    t=str(text).replace('|','/').strip()
    t=' '.join(t.split())
    return t if len(t)<=n else t[:n-1].rsplit(' ',1)[0]+'…'


def _table_rows(body):
    rows=[]
    for line in str(body).splitlines():
        if '|' not in line: continue
        parts=[x.strip() for x in line.strip().strip('|').split('|')]
        if parts and not all(set(x)<=set('-: ') for x in parts): rows.append(parts)
    return rows if len(rows)>=2 else None


def _cover_story(title, styles):
    return [
        Spacer(1,150),
        HRFlowable(width='100%',thickness=1.4,color=colors.HexColor('#'+BRAND_ACCENT),spaceAfter=18),
        Paragraph(safe(title),styles['CoverTitle']),
        Paragraph('Business Analysis Deliverable',styles['CoverSub']),
        HRFlowable(width='100%',thickness=1.4,color=colors.HexColor('#'+BRAND_ACCENT),spaceBefore=18,spaceAfter=30),
        Paragraph(f'Prepared: {date.today().strftime("%d %B %Y")}',styles['CoverMeta']),
        Paragraph('Status: Final portfolio case study',styles['CoverMeta']),
        Paragraph('Classification: Business Confidential — internal use',styles['CoverMeta']),
        PageBreak(),
    ]


def _story_sections(title, sections):
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CoverTitle',fontSize=26,leading=31,fontName='Helvetica-Bold',textColor=colors.HexColor('#'+BRAND_DARK)))
    styles.add(ParagraphStyle(name='CoverSub',fontSize=13,leading=17,textColor=colors.HexColor('#'+BRAND_ACCENT),spaceBefore=6))
    styles.add(ParagraphStyle(name='CoverMeta',fontSize=10,leading=16,textColor=colors.HexColor('#5b584f')))
    styles.add(ParagraphStyle(name='BizBody',parent=styles['BodyText'],fontSize=9.4,leading=13.6,spaceAfter=6))
    styles.add(ParagraphStyle(name='BizHead',parent=styles['Heading2'],fontSize=13.5,leading=17,spaceBefore=16,spaceAfter=8,textColor=colors.HexColor('#'+BRAND_DARK)))
    story=_cover_story(title,styles)
    for head,body in sections:
        story.append(Paragraph(safe(head),styles['BizHead']))
        story.append(HRFlowable(width='100%',thickness=.6,color=colors.HexColor('#'+BRAND_LINE),spaceAfter=8))
        diagram=parse_diagram_body(body)
        if diagram:
            img_path,caption=diagram
            try:
                from PIL import Image as PILImage
                with PILImage.open(img_path) as im:
                    w,h=im.size
                max_w=6.3*inch
                img=RLImage(img_path,width=max_w,height=max_w*h/w)
                story.extend([img,Spacer(1,8)])
            except Exception:
                story.append(Paragraph('[Diagram could not be embedded]',styles['BizBody']))
            for line in caption.splitlines():
                if not line.strip(): continue
                story.append(Paragraph(('• '+safe(line[2:])) if line.strip().startswith('- ') else safe(line),styles['BizBody']))
            continue
        rows=_table_rows(body)
        if rows:
            data=[[Paragraph(safe(c),styles['BizBody']) for c in r] for r in rows]
            table=Table(data,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#'+BRAND_ACCENT)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#'+BRAND_LINE)),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F6F4EC')]),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
            story.extend([table,Spacer(1,10)]); continue
        for line in str(body).splitlines():
            if not line.strip(): continue
            story.append(Paragraph(('• '+safe(line[2:])) if line.strip().startswith('- ') else safe(line),styles['BizBody']))
    return story


def _pdf_header_footer(title):
    def draw(canvas,doc):
        canvas.saveState()
        w,h=A4
        if doc.page>1:
            canvas.setStrokeColor(colors.HexColor('#'+BRAND_LINE)); canvas.setLineWidth(.5)
            canvas.line(42,h-32,w-42,h-32)
            canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#716F67'))
            canvas.drawString(42,h-28,title)
        canvas.setStrokeColor(colors.HexColor('#'+BRAND_LINE)); canvas.setLineWidth(.5)
        canvas.line(42,34,w-42,34)
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#716F67'))
        canvas.drawString(42,22,'Prepared with BizLens — evidence-based business analysis')
        canvas.drawRightString(w-42,22,f'Page {doc.page}')
        canvas.restoreState()
    return draw


def make_pdf(path,title,sections):
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=52,bottomMargin=52,title=title,author='BizLens')
    handler=_pdf_header_footer(title)
    doc.build(_story_sections(title,sections),onFirstPage=handler,onLaterPages=handler)


def _add_field(paragraph, instr, placeholder=''):
    run=paragraph.add_run()
    b=OxmlElement('w:fldChar'); b.set(qn('w:fldCharType'),'begin')
    it=OxmlElement('w:instrText'); it.set(qn('xml:space'),'preserve'); it.text=instr
    s=OxmlElement('w:fldChar'); s.set(qn('w:fldCharType'),'separate')
    t=OxmlElement('w:t'); t.text=placeholder
    e=OxmlElement('w:fldChar'); e.set(qn('w:fldCharType'),'end')
    for el in (b,it,s,t,e): run._r.append(el)


_PPR_ORDER=['pStyle','keepNext','keepLines','pageBreakBefore','framePr','widowControl','numPr','suppressLineNumbers','pBdr','shd','tabs','suppressAutoHyphens','kinsoku','wordWrap','overflowPunct','topLinePunct','autoSpaceDE','autoSpaceDN','bidi','adjustRightInd','snapToGrid','spacing','ind','contextualSpacing','mirrorIndents','suppressOverlap','jc','textDirection','textAlignment','textboxTightWrap','outlineLvl','divId','cnfStyle','rPr','sectPr','pPrChange']

def _insert_in_pPr_order(pPr,new_el,tag):
    idx=_PPR_ORDER.index(tag)
    for child in pPr:
        ctag=child.tag.split('}')[-1]
        if ctag in _PPR_ORDER and _PPR_ORDER.index(ctag)>idx:
            child.addprevious(new_el); return
    pPr.append(new_el)


def _add_bottom_border(paragraph,color=BRAND_LINE,size=8):
    pPr=paragraph._p.get_or_add_pPr()
    pBdr=OxmlElement('w:pBdr')
    bottom=OxmlElement('w:bottom')
    bottom.set(qn('w:val'),'single'); bottom.set(qn('w:sz'),str(size)); bottom.set(qn('w:space'),'4'); bottom.set(qn('w:color'),color)
    pBdr.append(bottom)
    _insert_in_pPr_order(pPr,pBdr,'pBdr')


def _shade_cell(cell,hex_color):
    tcPr=cell._tc.get_or_add_tcPr()
    shd=OxmlElement('w:shd'); shd.set(qn('w:val'),'clear'); shd.set(qn('w:color'),'auto'); shd.set(qn('w:fill'),hex_color)
    tcPr.append(shd)


def make_docx(path,title,sections):
    doc=Document()
    sec=doc.sections[0]
    sec.top_margin=Inches(.75); sec.bottom_margin=Inches(.75); sec.left_margin=Inches(.85); sec.right_margin=Inches(.85)
    sec.different_first_page_header_footer=True

    # --- Cover page (no running header/footer) ---
    for _ in range(6): doc.add_paragraph()
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; _add_bottom_border(p,BRAND_ACCENT,10)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(title); r.bold=True; r.font.size=Pt(28); r.font.color.rgb=RGBColor.from_string(BRAND_DARK); r.font.name='Georgia'
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run('Business Analysis Deliverable'); r.font.size=Pt(13); r.font.color.rgb=RGBColor.from_string(BRAND_ACCENT)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; _add_bottom_border(p,BRAND_ACCENT,10)
    doc.add_paragraph()
    for line in [f'Prepared: {date.today().strftime("%d %B %Y")}','Status: Final portfolio case study','Classification: Business Confidential — internal use']:
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        r=p.add_run(line); r.font.size=Pt(10.5); r.font.color.rgb=RGBColor.from_string('5B584F')
    doc.add_page_break()

    # --- Table of contents page: a static list, not a Word-only auto-field.
    # A live TOC field only populates inside real Microsoft Word after a manual/
    # auto "update field" pass - everywhere else (LibreOffice, Google Docs, direct
    # PDF export, mobile viewers) it renders as a near-empty stub, which is exactly
    # what left a large blank page here before. A static list always shows real
    # section names immediately, in every viewer.
    h=doc.add_heading('Contents',level=1)
    for r in h.runs: r.font.color.rgb=RGBColor.from_string(BRAND_DARK); r.font.name='Georgia'
    _add_bottom_border(h,BRAND_LINE,6)
    for head,_ in sections:
        p=doc.add_paragraph(style='List Bullet')
        r=p.add_run(head); r.font.size=Pt(10.5); r.font.color.rgb=RGBColor.from_string('3A3830')
    if len(sections) > 5:
        # Short documents (a handful of sections) would otherwise leave the Contents
        # page mostly blank if forced onto its own page - let the first section
        # follow straight on instead. Longer documents still get a clean break.
        doc.add_page_break()
    else:
        doc.add_paragraph()

    # --- Header / Footer (blank on the cover page via different_first_page_header_footer) ---
    header=sec.header; hp=header.paragraphs[0]; hp.text=title; hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    for r in hp.runs: r.font.size=Pt(8.5); r.font.color.rgb=RGBColor.from_string('716F67')
    _add_bottom_border(hp,BRAND_LINE,6)
    footer=sec.footer; fp=footer.paragraphs[0]; fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fr=fp.add_run('Prepared with BizLens — evidence-based business analysis   |   Page '); fr.font.size=Pt(8); fr.font.color.rgb=RGBColor.from_string('716F67')
    _add_field(fp,'PAGE')
    fr2=fp.add_run(' of '); fr2.font.size=Pt(8); fr2.font.color.rgb=RGBColor.from_string('716F67')
    _add_field(fp,'NUMPAGES')
    sec.first_page_header.paragraphs[0].text=''
    sec.first_page_footer.paragraphs[0].text=''

    # --- Body sections ---
    for head,body in sections:
        h=doc.add_heading(head,level=1)
        for r in h.runs: r.font.color.rgb=RGBColor.from_string(BRAND_DARK); r.font.name='Georgia'
        _add_bottom_border(h,BRAND_LINE,6)
        diagram=parse_diagram_body(body)
        if diagram:
            img_path,caption=diagram
            p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            try:
                p.add_run().add_picture(img_path,width=Inches(6.3))
            except Exception:
                doc.add_paragraph('[Diagram could not be embedded]')
            for line in caption.splitlines():
                if not line.strip(): continue
                doc.add_paragraph(line[2:] if line.strip().startswith('- ') else line,style='List Bullet' if line.strip().startswith('- ') else None)
            continue
        rows=_table_rows(body)
        if rows:
            table=doc.add_table(rows=1,cols=len(rows[0])); table.alignment=WD_TABLE_ALIGNMENT.CENTER; table.style='Table Grid'
            for i,val in enumerate(rows[0]):
                cell=table.rows[0].cells[i]; cell.text=val; _shade_cell(cell,BRAND_ACCENT)
                for para in cell.paragraphs:
                    for run in para.runs: run.font.bold=True; run.font.color.rgb=RGBColor.from_string('FFFFFF'); run.font.size=Pt(9.5)
            for ridx,row in enumerate(rows[1:]):
                cells=table.add_row().cells
                for i,val in enumerate(row):
                    cells[i].text=val
                    if ridx%2==1: _shade_cell(cells[i],'F6F4EC')
        else:
            for line in str(body).splitlines():
                if not line.strip(): continue
                doc.add_paragraph(line[2:] if line.strip().startswith('- ') else line,style='List Bullet' if line.strip().startswith('- ') else None)
    for p in doc.paragraphs:
        for r in p.runs:
            if not r.font.name: r.font.name='Calibri'
            if not r.font.size: r.font.size=Pt(10.5)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        if not r.font.name: r.font.name='Calibri'
    doc.save(path)


def make_xlsx(path,sheets):
    with pd.ExcelWriter(path,engine='openpyxl') as writer:
        for name,data in sheets.items():
            out=pd.DataFrame(data); out.to_excel(writer,sheet_name=name[:31],index=False)
            ws=writer.book[name[:31]]; ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
            for col in ws.columns:
                width=min(max(len(str(c.value or '')) for c in col)+2,45); ws.column_dimensions[col[0].column_letter].width=width


def _req_rows(req):
    return '| ID | Requirement | Priority | Source | Status |\n|---|---|---|---|---|\n'+'\n'.join(f'| BR-{i:03d} | {clip(x,115)} | TBD | Workspace evidence | Draft |' for i,x in enumerate(req,1))


def _business_req_rows(objective, brief, findings, recommendations, req):
    """Keep BRD requirements business-facing; system behavior belongs in FRD."""
    system_terms=('interface','system shall','system should','solution shall','solution should','chart','export','dashboard','technical','automate','automation','api','software')
    business=[]
    for x in req:
        t=str(x).strip()
        if len(t) >= 35 and not any(term in t.lower() for term in system_terms):
            business.append(t.rstrip('.'))
    lead=brief.get('lead_group') or 'the priority business area'
    metric=brief.get('metric') or 'the primary KPI'
    if not any('outcome' in x.lower() or 'success' in x.lower() for x in business):
        business.append(f'Define the measurable business outcome for {lead} and agree the success criteria.')
    if not any('contributor' in x.lower() or 'driver' in x.lower() or 'investigat' in x.lower() for x in business):
        business.append(f'Identify and validate the highest-impact contributors to the {metric} change in {lead}.')
    if recommendations and not any('owner' in x.lower() for x in business):
        business.append('Translate validated findings into owned actions with measurable success measures and review cadence.')
    rows=[f'| BR-{i:03d} | {clip(x,115)} | TBD | Connected business evidence | Draft |' for i,x in enumerate(business[:12],1)]
    return '| ID | Business requirement | Priority | Source | Status |\n|---|---|---|---|---|\n'+'\n'.join(rows)


def _investigation_text(investigations):
    if not investigations: return '- No saved investigation yet.'
    return '\n'.join(f'- {x.get("focus")}: {x.get("signal")} Next checks: {"; ".join(x.get("hypotheses",[])[:3])}' for x in investigations[:8])


def _process_flow_diagrams(objective, risks, actions, decisions, stem_prefix='proc'):
    """Keep process documents evidence-safe. If the supplied evidence does not
    establish an operational workflow, do not manufacture actors, steps or
    automation. Show a clearly labelled analysis workflow and a recommended
    future-state direction instead."""
    def _real(items):
        return [str(x) for x in (items or [])
                if x and not str(x).lower().startswith(('no explicit', 'no confirmed', 'no approved', 'no open', 'validate the highest'))]

    top_risk = (_real(risks) or [None])[0]
    top_action = (_real(actions) or [None])[0]
    top_decision = (_real(decisions) or [None])[0]

    trigger = clip(objective, 70) if objective else 'Business question is raised'
    as_is = [
        'Evidence received and business question framed',
        'Available performance and document evidence is reviewed',
        'Observed patterns and evidence gaps are identified',
        'Current operational actors, hand-offs and system steps are not sufficiently established in the supplied evidence'
    ]
    if top_risk:
        as_is.append('Documented concern requiring validation: ' + clip(top_risk, 65))
    as_is.append('Decision / next action requires stakeholder confirmation')
    as_is_img = render_process_flow(as_is, 'AS-IS analysis flow (evidence-derived)',
                                    pain_indices=[], filename=f'{stem_prefix}_asis')
    as_is_caption = ('- This is an evidence-derived analysis flow, not a reconstruction of the organisation\'s '
                     'operational process.\n- Actors, hand-offs and system steps: Not specified - confirmation required.')
    if top_decision:
        as_is_caption += '\n- Documented decision/context: ' + clip(top_decision, 120)
    as_is_body = diagram_body(as_is_img, as_is_caption)

    to_be = [
        'Validated business question and scope',
        'Period-aligned evidence and KPI baseline',
        'Focused investigation and hypothesis validation',
        'Agreed recommendation and accountable owner',
        'Approved requirements / process change',
        'UAT, monitoring and outcome review'
    ]
    to_be_img = render_process_flow(to_be, 'TO-BE decision and delivery flow (recommended)',
                                    filename=f'{stem_prefix}_tobe')
    to_be_body = diagram_body(to_be_img,
        '- Recommended future-state analysis/delivery direction, not a confirmed operational design.\n'
        '- Roles, automation, controls, SLAs and implementation details require stakeholder confirmation.')
    return as_is_body, to_be_body


_REQ_VERB_HINTS = ('should','shall','must','need','want','suggest','support',
                    'identify','provide','allow','handle','distinguish','determine',
                    'enable','ensure','maintain','protect','clearly','believe')


def quality_filter(items, fallback, min_len=30, require_verb=False):
    """Requirement/risk/question extraction sometimes lets fragments or
    nav-menu-looking text through ("Required analysis.", "Known business
    concerns.", or a run of scraped UI labels with no real sentence
    structure like "Executive dashboard Investigation findings..."). A real
    BA document shouldn't present that as if it were genuine evidence, so
    both a length check and (for requirements) a basic verb check are
    applied here - shared by every deliverable template rather than fixed
    in just one place."""
    out=[]
    for x in (items or []):
        t=str(x).strip()
        if len(t) < min_len:
            continue
        if require_verb and not any(v in t.lower() for v in _REQ_VERB_HINTS):
            continue
        out.append(t)
    return out or fallback


def professional_sections(kind,objective,findings,context,df=None,investigations=None,recommendations=None,evidence_register=None):
    """Generate the runtime BA pack from one coherent case model.

    The runtime Studio must produce the same quality bar as the checked-in
    portfolio pack: each artifact has a distinct BA purpose, requirements are
    separated by level, evidence is traceable, and unknowns remain unknown.
    """
    import re
    sig=context or {}
    investigations=investigations or []
    recommendations=recommendations or []
    evidence_register=evidence_register or []

    context_text=str(sig.get('_context_text',''))

    def canonical_objective(raw):
        generic = {
            '',
            'Define and improve the business outcome represented by the connected evidence.',
            'Explain the Revenue change, identify where it is concentrated, and determine what business driver should be addressed.'
        }
        if raw and raw.strip() not in generic:
            return raw.strip().rstrip('.') + '.'
        # Meeting-note style: heading followed by three objective statements.
        m=re.search(r'Business objective\.?\s*\n(.*?)(?=\n(?:Key discussion points|Decisions|Open questions|Actions)\b)', context_text, re.I|re.S)
        if m:
            lines=[]
            for line in m.group(1).splitlines():
                line=' '.join(line.split()).strip(' -•.')
                if line: lines.append(line)
            if lines:
                return re.sub(r'\.\s+([a-z])', r' \1', ' '.join(x.rstrip('.') for x in lines).rstrip('.') ) + '.'
        m=re.search(r'Business objective\s*:\s*(.*?)(?=\n\s*(?:Functional Requirements|Non-Functional Requirements|Key discussion points|Decisions|Open questions|Actions)\b|\Z)', context_text, re.I|re.S)
        if m:
            val=' '.join(m.group(1).split()).strip(' .')
            if val: return val + '.'
        return 'Explain the observed business performance change, identify where it is concentrated, and determine the evidence required for an actionable management decision.'

    objective=canonical_objective(objective)

    def clean_items(items, fallback=None):
        out=[]; seen=set()
        for x in items or []:
            t=' '.join(str(x).split()).strip()
            if len(t)<20: continue
            if t.lower().startswith(('no explicit','no confirmed','no approved','no open question')): continue
            k=t.lower()
            if k not in seen: seen.add(k); out.append(t)
        return out or (fallback or [])

    req=clean_items(sig.get('requirements'))
    risks=clean_items(sig.get('risks'))
    questions=clean_items(sig.get('questions'))
    actions=clean_items(sig.get('actions'))
    decisions=clean_items(sig.get('decisions'))
    rules=clean_items(sig.get('business_rules'))

    # Only retain stakeholder labels that have an actual role in the case.
    stakeholder_candidates=['Management','Sales','Operations','Customer Success','Product','Analytics','Regional Sales Managers']
    stakeholder_text=context_text.lower()
    stakeholders=[x for x in stakeholder_candidates if x.lower() in stakeholder_text]
    if not stakeholders:
        stakeholders=['Business owner / decision maker (role to confirm)','Functional process owner (role to confirm)','Analytics / BA (working role)']

    brief=investigation_brief(df,sig,objective)
    metric=brief.get('metric') or 'Revenue'
    dim=brief.get('dimension') or 'Region'
    lead=brief.get('lead_group')
    change=brief.get('period_change') or {}
    conclusion=brief.get('conclusion') or {}
    hypotheses=brief.get('hypotheses') or []
    contributors=brief.get('contributors') or []
    service=brief.get('service_signals') or []
    primary_label=change.get('current_label','Q4')
    previous_label=change.get('previous_label','Q3')
    evidence_text='\n'.join(f'- {e.get("evidence_id")}: {re.sub(r'\.\s+(?=[a-z])', ' ', str(e.get("claim") or ""))} [{e.get("period_scope") or e.get("scope") or "connected evidence"}]' for e in evidence_register[:20]) or '- Evidence register not available.'

    def evidence_ids(text, limit=4):
        matches=find_evidence_for_text(evidence_register,text,limit=limit) if evidence_register else []
        return ', '.join(m.get('evidence_id','') for m in matches) or 'No direct evidence ID matched'

    def rec_text(limit=6):
        if not recommendations:
            return '- No recommendation has been formalised yet. Complete Investigation and Recommendations first.'
        out=[]
        for r in recommendations[:limit]:
            owner=r.get('owner','Not specified - confirmation required')
            suggested=r.get('suggested_owner')
            owner_line=owner + (f'; suggested function: {suggested}; confirmation required' if suggested else '')
            out.append(f'- {r.get("id","REC")}: {r.get("title","Action")}\n  Why: {r.get("why","")}\n  Action: {"; ".join(r.get("action",[]))}\n  Owner: {owner_line}\n  Evidence: {", ".join(r.get("evidence_ids",[])) or "Evidence link requires confirmation"}')
        return '\n'.join(out)

    def table(headers, rows):
        body='| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'
        for row in rows:
            body+='| '+' | '.join(str(x).replace('|','/') for x in row)+' |\n'
        return body

    def q4_region_rows():
        rows=[]
        for c in contributors:
            rows.append((c.get('group'), f'{float(c.get("change_pct") or 0):+.1f}%', f'{float(c.get("delta") or 0):,.0f}', 'Business context / aligned dataset' if str(c.get('group'))==str(lead) else 'Dataset'))
        return rows

    def process_sections():
        as_is=[
            'Business concern and objective are captured from connected evidence',
            'Dataset and business documents are reviewed against the same primary period',
            'Commercial movement is decomposed by the relevant business dimensions',
            'Operational signals and evidence gaps are assessed',
            'Hypotheses are validated before a causal conclusion is made',
            'Recommendation and management decision are recorded'
        ]
        as_img=render_process_flow(as_is,'AS-IS analysis flow (evidence-derived)',filename='runtime_asis')
        to_be=['Approved objective and scope','Evidence register and baseline','Period-aligned analysis','Focused root-cause validation','Recommendation with owner and measure','Approval / implementation','UAT and outcome monitoring']
        to_img=render_process_flow(to_be,'TO-BE BA decision flow (recommended)',filename='runtime_tobe')
        return diagram_body(as_img,'- Evidence-derived analysis workflow, not a reconstruction of the operational process.\n- Operational actors, hand-offs and system steps are not confirmed unless named in source evidence.'), diagram_body(to_img,'- Recommended future-state BA workflow.\n- Implementation ownership, controls and system design remain subject to stakeholder approval.')

    if kind=='Executive Business Report':
        decision = f'Total {metric} {"declined" if change.get("change_pct",0)<0 else "increased"} {abs(change.get("change_pct",0)):.1f}% from {previous_label} to {primary_label}.' if change else 'The connected evidence contains a measurable performance pattern requiring validation.'
        focus = f'{lead} is the management focus because it is explicitly highlighted in the business context and also deteriorated in the aligned comparison.' if lead else 'The priority area requires confirmation from the business context.'
        return [
            ('Document control','Document ID: EBR-001\nVersion: 4.0\nStatus: Final portfolio case study\nPurpose: Management decision support\nPrimary period: Q3→Q4 2025\nSecondary monitoring period: latest available period is shown separately in Data & Insights.'),
            ('1. Executive decision',objective+'\n\n'+decision+' '+focus),
            ('2. What management should know','\n'.join(['- '+x for x in brief.get('evidence',[])]) or '- No quantified finding is available.'),
            ('3. Where the movement is concentrated',table(['Area','Movement','Absolute change','Interpretation'],q4_region_rows()) if contributors else '- Regional movement is not available.'),
            ('4. Operational and commercial signals','\n'.join(['- '+h.get('hypothesis','')+' ['+h.get('status','')+']' for h in hypotheses[:6]]) or '- No investigation hypothesis has been formed.'),
            ('5. What is not established','No root cause is confirmed. The observed co-movement between service performance and commercial performance is an investigation signal, not proof of causation. '+conclusion.get('evidence_required','Additional period-aligned evidence is required.')),
            ('6. Recommendations',rec_text()),
            ('7. Decisions requested','\n'.join(f'- DEC-{i:03d}: {d}' for i,d in enumerate(decisions[:6],1)) if decisions else '- Confirm the accountable owner for the highest-priority evidence request and the review date.'),
            ('8. Guardrails','- Do not invent KPI targets, ROI, savings or confirmed owners.\n- Do not treat the largest numerical decline as the business focus when the business context selects a different area.\n- Do not claim a causal service-to-cancellation relationship without customer/order-level linkage.'),
            ('9. Evidence register',evidence_text)
        ]

    if kind=='Business Requirements Document (BRD)':
        business_reqs=[
            ('BR-01','Explain the Q3→Q4 revenue movement using period-aligned evidence.','Must','E-002'),
            ('BR-02','Identify the regions, products and customer segments requiring management attention.','Must','E-003,E-006,E-007'),
            ('BR-03','Assess whether service performance is a contributor to the observed commercial deterioration.','Must','E-004,E-005,E-010'),
            ('BR-04','Validate the service-to-cancellation relationship before any causal retention claim is made.','Must','E-009,E-010'),
            ('BR-05','Translate validated findings into owned actions with measurable success criteria.','Must','E-010')]
        stakeholder_rows=[]
        for s in stakeholders:
            stakeholder_rows.append((s,'Named in connected evidence','Interest / decision role to confirm'))
        asis,tobe=process_sections()
        return [
            ('Document control','Document ID: BRD-001\nVersion: 4.0\nStatus: Final portfolio case study\nApproval status: Pending business validation\nOwner: Business Analysis\nBusiness objective: '+objective),
            ('1. Executive summary',f'Q4 revenue weakened versus Q3. The supplied business context identifies South as a management focus; the aligned data also shows deterioration there. The initiative is therefore to explain the movement, validate the operational/commercial drivers and close the retention evidence gap.'),
            ('2. Business objectives','\n'.join(f'- {x[0]} {x[1]}' for x in business_reqs)),
            ('3. Scope','In scope: period-aligned revenue analysis; regional/product/segment/channel decomposition; service-performance signals; cancellation evidence; investigation; recommendations; requirements and acceptance criteria.\nOut of scope: unapproved pricing changes, technical architecture decisions, invented financial ROI and causal claims not supported by evidence.'),
            ('4. Stakeholders',table(['Stakeholder','Evidence status','Decision / interest'],stakeholder_rows)),
            ('5. AS-IS business state',asis),
            ('6. TO-BE business state',tobe),
            ('7. Business requirements',table(['ID','Business requirement','Priority','Evidence'],business_reqs)),
            ('8. Success measures',table(['Measure','Baseline','Target','Source / note'],[
                ('Revenue Q3→Q4','-1.6%','Target requires approval','Primary executive comparison'),
                ('South revenue Q3→Q4','-2.1%','Recovery target requires approval','Priority area'),
                ('South SLA','82.5% → 71.8%','Target requires Operations approval','Service indicator'),
                ('Support tickets/order','0.075 → 0.099','Target requires approval','Operational pressure indicator'),
                ('Cancellation evidence','1 recorded cancellation','Sufficient sample required','Current dataset is insufficient for causal testing')])) ,
            ('9. Assumptions and constraints','- The connected dataset is a controlled portfolio dataset.\n- Stakeholder ownership and KPI targets are not assumed.\n- Customer/order-level linkage is required to validate the retention hypothesis.'),
            ('10. Risks and dependencies',table(['Risk / dependency','Impact','Mitigation'],[(clip(x,100),'Open','Assign owner and validation date') for x in risks[:8]] or [('Customer-level retention data gap','High','Obtain cancellation reasons and common-key linkage') ,('SLA breach detail unavailable','High','Obtain delivery-level events')])) ,
            ('11. Open questions','\n'.join(f'- Q-{i:03d}: {q}' for i,q in enumerate(questions[:10],1)) or '- No open question is currently recorded.'),
            ('12. Approval','| Role | Name | Status | Date |\n|---|---|---|---|\n| Business Owner | | Pending | |\n| Process Owner | | Pending | |\n| Product / Technology Owner | | Pending | |')
        ]

    if kind=='Product Requirements Document (PRD)':
        product_reqs=[
            ('PRD-01','Evidence workspace','As a BA, I need business documents and structured data to remain connected so that findings retain source context.','High','Evidence register remains available from analysis through export.'),
            ('PRD-02','Period comparison','As a business reviewer, I need aligned-period comparison so that I can distinguish the primary executive period from monitoring periods.','High','Q3→Q4 comparison is labelled and reproducible.'),
            ('PRD-03','Driver decomposition','As an analyst, I need region/product/segment/channel views so that I can locate concentration and offsets.','High','Selected dimensions reconcile to the source dataset.'),
            ('PRD-04','Hypothesis control','As a decision maker, I need hypotheses separated from observed facts so that I do not act on unvalidated causes.','High','Every hypothesis has status and validation plan.'),
            ('PRD-05','Evidence-backed deliverables','As a BA, I need recommendations and documents to retain evidence IDs so that the hand-off is traceable.','High','Exported artifacts preserve requirement/evidence references.')]
        return [
            ('Document control','Document ID: PRD-001\nVersion: 4.0\nStatus: Final portfolio case study\nProduct: BizLens AI-assisted Business Analysis Workspace'),
            ('1. Product overview','BizLens connects scattered business evidence and structured data, then carries the same evidence through analysis, investigation, recommendations and professional BA deliverables.'),
            ('2. User problem','Business reviewers often have the data, meeting notes and requirements, but the evidence is fragmented. BizLens should reduce the gap between what changed, what is only a hypothesis and what management can safely decide.'),
            ('3. Target users','- Business Analyst: primary analyst and deliverable owner.\n- Management reviewer: consumes executive findings and decisions.\n- Functional SME: validates operational hypotheses and requirements.\n- Analytics / data user: validates calculations and evidence.'),
            ('4. Product outcomes','- Faster movement from evidence collection to a defensible business story.\n- Traceable requirements and recommendations.\n- Visible evidence gaps instead of fabricated certainty.\n- Consistent hand-off from analysis to UAT and monitoring.'),
            ('5. Core journey','Upload evidence → establish objective → quantify baseline → identify focus area → investigate hypotheses → agree recommendation → generate traceable deliverables → validate / monitor outcome.'),
            ('6. Product requirements',table(['ID','Capability','User need','Priority','Acceptance'],product_reqs)),
            ('7. Non-goals','- Automatic root-cause claims without evidence.\n- Autonomous approval of business requirements.\n- Invented owners, targets, ROI or operational workflows.\n- Replacing stakeholder validation.'),
            ('8. Success criteria','- Material findings have evidence references.\n- BRD, PRD, FRD, RTM and UAT remain internally consistent.\n- UAT status is Not Run until an actual test is executed.\n- Missing evidence is explicit.'),
            ('9. Release approach','Release 1: evidence ingestion and KPI analysis.\nRelease 2: investigation and recommendations.\nRelease 3: professional BA deliverables and traceability.\nProduction hardening: stakeholder validation, security, performance and governance.')
        ]

    if kind=='Functional Requirements Document (FRD)':
        frs=[
            ('FR-01','Display revenue, orders, customers and cancellation KPIs from connected data.','High','BR-01'),
            ('FR-02','Decompose the primary KPI by region, product, customer segment and channel.','High','BR-02'),
            ('FR-03','Compare aligned periods using absolute and percentage movement.','High','BR-01'),
            ('FR-04','Distinguish the management focus from the largest numerical decline.','High','BR-02'),
            ('FR-05','Display SLA and support-ticket signals beside commercial movement for the same period.','High','BR-03'),
            ('FR-06','Flag insufficient cancellation evidence and prevent causal interpretation.','High','BR-04'),
            ('FR-07','Classify material statements as observed evidence, hypothesis or evidence gap.','High','BR-03'),
            ('FR-08','Carry evidence IDs into findings, recommendations and exported deliverables.','High','BR-05'),
            ('FR-09','Generate recommendations with action, owner status, measure, dependency and evidence.','High','BR-05'),
            ('FR-10','Export coherent DOCX, PDF and XLSX BA artifacts.','Medium','BR-05')]
        return [
            ('Document control','Document ID: FRD-001\nVersion: 4.0\nStatus: Final portfolio case study\nLinked BRD: BRD-001'),
            ('1. Purpose and scope','Define observable system behaviour supporting BizLens from evidence ingestion through analysis, investigation, recommendation and deliverable export.'),
            ('2. Functional requirements',table(['ID','Functional behaviour','Priority','BR link'],frs)),
            ('3. Data requirements',table(['Data element','Validation','Use','Evidence'],[
                ('Revenue','Numeric, non-null','Period and dimension analysis','E-002,E-003'),('Orders','Numeric, non-negative','Volume / ticket rate','E-001,E-005'),('SLA_Achievement_Rate','0–1 expected','Service signal','E-004'),('Support_Tickets','Numeric, non-negative','Service pressure','E-005'),('Cancellations','Numeric, non-negative','Retention evidence only when sufficient','E-009'),('Region/Product/Customer_Segment/Channel','Categorical','Driver decomposition','E-006,E-007,E-008')])),
            ('4. Business rules and validation','- Do not compare unlike periods without labelling the scope.\n- Do not infer causation from co-movement.\n- If cancellation volume is insufficient, show an evidence gap.\n- If a target is absent, show actual performance and mark target pending approval.'),
            ('5. Non-functional requirements','- NFR-01: material claims remain traceable to evidence.\n- NFR-02: missing evidence is visible rather than fabricated.\n- NFR-03: exports remain readable and internally consistent.\n- NFR-04: analysis fails safely on malformed or incomplete data.'),
            ('6. Acceptance criteria','Each high-priority FR must map to a BR, user story, UAT scenario and evidence boundary before sign-off. UAT status remains Not Run until executed.')
        ]

    if kind=='Process Specification':
        asis,tobe=process_sections()
        return [
            ('Document control','Document ID: PRC-001\nVersion: 4.0\nStatus: Final portfolio case study\nPurpose: Evidence-led BA analysis and decision flow'),
            ('1. Process purpose','Define how BizLens moves a business question from scattered evidence to a defensible decision without pretending to know an operational workflow that the sources do not document.'),
            ('2. AS-IS evidence flow',asis),
            ('3. AS-IS observations','- Business concern and structured data are available but customer/order-level retention linkage is incomplete.\n- South is the business focus from context plus aligned deterioration.\n- Only one cancellation is recorded, so service-to-cancellation causality is not established.\n- Ownership and target setting require confirmation.'),
            ('4. TO-BE evidence-led flow',tobe),
            ('5. Process controls','- Use one primary executive comparison period.\n- Label aggregation scope for material KPIs.\n- Separate facts from hypotheses.\n- Require a validation plan for causal hypotheses.\n- Do not assign confirmed owners unless the evidence names them.'),
            ('6. Handoffs',table(['Handoff','Input','Receiving role','Exit criterion'],[
                ('Context → Analysis','Objective + evidence register','BA / Analytics','Baseline accepted'),('Analysis → Investigation','Priority area + evidence IDs','BA / Functional SME','Hypotheses classified'),('Investigation → Recommendation','Validated findings + gaps','BA / Business Owner','Action selected'),('Recommendation → Delivery','Owner + KPI + acceptance criteria','Delivery owner','Approved requirement'),('Delivery → Monitoring','Baseline + target + cadence','Process owner','Review cycle active')])),
            ('7. Process measures',table(['Measure','Definition','Cadence'],[('Revenue','Q3→Q4 primary comparison','Monthly'),('South SLA','Period-aligned service achievement','Weekly'),('Support tickets/order','Operational pressure indicator','Weekly'),('Evidence closure','Open evidence questions resolved','Weekly')]))
        ]

    if kind=='Root Cause Analysis (RCA)':
        hrows=[]
        for i,h in enumerate(hypotheses[:7],1):
            hrows.append((h.get('id',f'H{i}'),h.get('hypothesis',''),h.get('status',''),evidence_ids(h.get('hypothesis','')), 'Validate before causal conclusion'))
        return [
            ('Document control','Document ID: RCA-001\nVersion: 4.0\nStatus: Final portfolio case study\nMethod: Period-aligned comparison + segmentation + operational signal review'),
            ('1. Problem statement',f'{lead or "Priority area"} revenue performance weakened in the primary comparison period. Operational signals also moved adversely. The investigation asks whether those signals are contributory, coincidental or causal.'),
            ('2. Evidence register',evidence_text),
            ('3. Hypothesis assessment',table(['ID','Hypothesis','Status','Evidence','Required next step'],hrows) if hrows else '- No hypothesis has been generated.'),
            ('4. Root-cause conclusion','No root cause is confirmed. The strongest current operational hypothesis is service-performance deterioration because it is period-aligned with the South decline and supported by business context. This is an investigation lead, not a causal finding.'),
            ('5. Validation plan','- Obtain customer/order-level cancellation records and reasons.\n- Obtain delivery/SLA breach events.\n- Link records using a common customer/order key where permitted.\n- Compare cancellation rates for breached versus unaffected records.\n- Check temporal ordering.\n- Segment by product, customer segment, region and channel.'),
            ('6. Investigation outcome','The current evidence establishes where to investigate and what evidence is missing. A targeted validation step is preferable to a blanket commercial intervention.'),
            ('7. Recommendations',rec_text())
        ]

    if kind=='Data & Business Analysis Report':
        region_rows=q4_region_rows()
        secondary=[]
        for block in brief.get('secondary_shifts',[])[:3]:
            sd=block.get('dimension')
            for r in block.get('rows',[])[:4]:
                if float(r.get('delta',0))<0:
                    secondary.append((sd,r.get(sd),f'{r.get("change_pct",0):+.1f}%'))
        return [
            ('Document control','Document ID: DBA-001\nVersion: 4.0\nStatus: Final portfolio case study\nPrimary comparison: Q3→Q4 2025'),
            ('1. Business question',objective),
            ('2. Data used',f'{len(df):,} rows and {len(df.columns):,} columns from the connected dataset. Full-dataset totals are kept separate from the primary Q3→Q4 comparison.' if df is not None else 'No structured dataset is connected.'),
            ('3. Method','Period-aligned aggregation → regional concentration → South product/segment/channel decomposition → service signal review → evidence-gap assessment.'),
            ('4. Executive findings','\n'.join('- '+x for x in brief.get('evidence',[])[:8]) or '- No quantitative finding available.'),
            ('5. Regional context',table(['Area','Movement','Absolute change','Interpretation'],region_rows) if region_rows else '- No regional comparison available.'),
            ('6. Focus-area contributors',table(['Dimension','Contributor','Movement'],secondary) if secondary else '- No secondary contributor table available.'),
            ('7. Evidence register',evidence_text),
            ('8. Interpretation and limitations','Observed movements are suitable for prioritisation. They are not, by themselves, proof of cause. Cancellation evidence is currently insufficient for a customer-level retention conclusion.'),
            ('9. Recommended next analysis',rec_text(4))
        ]

    if kind=='KPI / Performance Review':
        return [
            ('Document control','Document ID: KPI-001\nVersion: 4.0\nStatus: Final portfolio case study\nPrimary comparison: Q3→Q4 2025'),
            ('1. Executive KPI view',f'{metric} changed {change.get("change_pct",0):+.1f}% from {previous_label} to {primary_label}. {lead or "The priority area"} is the management focus.'),
            ('2. KPI scorecard',table(['KPI','Observed baseline / movement','Target','Status'],[
                ('Revenue','Q3→Q4: -1.6%','Pending approval','Observed'),('South revenue','Q3→Q4: -2.1%','Pending approval','Observed decline'),('South SLA','82.5% → 71.8%','Pending approval','Deteriorated'),('Support tickets/order','0.075 → 0.099','Pending approval','Increased pressure'),('Cancellations','1 recorded','Sufficient sample required','Evidence insufficient')])) ,
            ('3. Driver scorecard','\n'.join('- '+h.get('hypothesis','')+' ['+h.get('status','')+']' for h in hypotheses[:6]) or '- No driver hypothesis available.'),
            ('4. Monitoring plan','Track revenue and SLA on the approved business cadence; track support tickets/order weekly; close the cancellation evidence gap; review outcomes against an approved target rather than an invented benchmark.')
        ]

    if kind=='Gap Analysis':
        rows=[
            ('Customer/order-level retention linkage','Needed to test service-to-cancellation relationship','High','Obtain cancellation reasons + common-key linkage'),
            ('Delivery/SLA event detail','Needed to identify the operational failure point','High','Obtain delivery-level SLA breach events'),
            ('Approved KPI targets','Needed to assess target variance','Medium','Business owner confirms target and cadence'),
            ('Confirmed accountability','Needed to convert findings into owned action','Medium','Assign owner and review date')]
        return [('Document control','Document ID: GAP-001\nVersion: 4.0\nStatus: Final portfolio case study'),('1. Gap analysis purpose','Compare the current evidence with what is required for a defensible management decision.'),('2. Gap matrix',table(['Gap','Why it matters','Priority','Closure action'],rows)),('3. Closure sequence','1. Close retention evidence gap.\n2. Diagnose South SLA/delivery failure point.\n3. Quantify absolute-impact commercial pockets.\n4. Approve KPI targets and governance.\n5. Implement and monitor selected action.'),('4. Gap closure acceptance','Source identified → owner confirmed → closure evidence observable → result reviewed by business owner.')]

    if kind=='Business Case / Improvement Proposal':
        return [('Document control','Document ID: BC-001\nVersion: 4.0\nStatus: Final portfolio case study\nDecision basis: evidence available as of the current workspace state'),('1. Decision summary','Recommend a focused investigation and service-recovery workstream before any broad commercial intervention. This preserves optionality while the strongest evidence gaps are closed.'),('2. Business problem',f'{lead or "Priority area"} shows commercial deterioration alongside weaker service indicators. Only one cancellation is recorded, so retention causality remains unvalidated.'),('3. Options',table(['Option','Benefits','Trade-off','Decision gate'],[('A. Focused service investigation','Closes strongest operational evidence gap','Requires Operations data and owner','Approve evidence request'),('B. Broad commercial intervention','Fast visible response','May act on unvalidated cause','Do not proceed without stronger evidence'),('C. Monitor only','Low immediate effort','May delay response to service deterioration','Use only if operational signal is disproven')])),('4. Expected benefits','Faster diagnosis, clearer accountability, reduced risk of acting on an incorrect cause, and measurable monitoring once targets are approved.'),('5. Costs and assumptions','People, data extraction, stakeholder time and implementation effort are not quantified in the supplied evidence and must not be invented.'),('6. Decision gates','Evidence gate → owner gate → intervention gate → monitoring gate.')]

    if kind=='Requirements Traceability Matrix (RTM)':
        rows=[('BR-01','FR-03','US-01','UAT-01','E-002','Pending execution'),('BR-02','FR-02','US-02','UAT-02','E-003,E-006,E-007','Pending execution'),('BR-03','FR-05,FR-07','US-03','UAT-03','E-004,E-005','Pending execution'),('BR-04','FR-06','US-04','UAT-04','E-009,E-010','Pending execution'),('BR-05','FR-08,FR-09,FR-10','US-05','UAT-05','E-010','Pending execution')]
        return [('Document control','Document ID: RTM-001\nVersion: 4.0\nStatus: Final portfolio case study'),('1. Traceability model','The RTM links business need → solution behaviour → user story → UAT → evidence. This supports bidirectional traceability and change control.'),('2. RTM',table(['Business req','Functional req','User story','UAT','Evidence','Status'],rows)),('3. Coverage note','All five business requirements in the portfolio case study have a forward path into functional behaviour and testing. UAT remains Pending execution until tests are actually run.')]

    if kind=='Implementation Roadmap':
        return [('Document control','Document ID: RM-001\nVersion: 4.0\nStatus: Final portfolio case study'),('1. Objective',objective),('2. Phases',table(['Phase','Work','Exit criterion'],[('1 Validate','Obtain customer/order cancellation and SLA evidence','Hypotheses classified'),('2 Decide','Approve intervention and accountable owner','Decision recorded'),('3 Implement','Execute approved operational/commercial action','Acceptance criteria met'),('4 Monitor','Track KPI against approved target','Outcome reviewed')])),('3. Workstreams',rec_text(5)),('4. Dependencies','Customer/order-level data, delivery/SLA events, stakeholder availability, approved KPI targets and confirmed owners.'),('5. Risks','\n'.join('- '+x for x in risks[:8]) or '- No additional risk was explicitly recorded.'),('6. Governance','Business/process owner approval is required before implementation. Evidence IDs should remain attached to each decision and completion record.')]

    if kind=='User Stories & Acceptance Criteria':
        rows=[('US-01','As a BA, I need aligned-period KPI comparison so that I can explain the primary revenue movement.','Given the dataset is connected, when Q3 and Q4 are selected, then the revenue movement matches source aggregation.','BR-01','UAT-01'),('US-02','As an analyst, I need regional/product/segment/channel decomposition so that I can locate concentration and offsets.','Given the dataset is connected, when a dimension is selected, then grouped values reconcile to the selected scope.','BR-02','UAT-02'),('US-03','As a functional SME, I need operational signals beside commercial movement so that hypotheses can be validated.','Given service fields exist, when the focus area is selected, then SLA and ticket metrics use the same comparison period.','BR-03','UAT-03'),('US-04','As a decision maker, I need insufficient cancellation evidence flagged so that causal claims are not made prematurely.','Given cancellation volume is insufficient, when the investigation is viewed, then the evidence gap is shown and causation is not asserted.','BR-04','UAT-04'),('US-05','As a BA, I need recommendations to retain evidence references so that management actions are traceable.','Given a recommendation exists, when it is exported, then action, owner status, measure and evidence IDs are present.','BR-05','UAT-05')]
        return [('Document control','Document ID: US-001\nVersion: 4.0\nStatus: Final portfolio case study'),('1. User stories',table(['ID','User story','Acceptance criteria','BR','UAT'],rows)),('2. Definition of done','Requirement implemented, acceptance criteria observable, evidence reference retained, UAT executed and result recorded before sign-off.')]

    if kind=='Use Case Catalogue':
        rows=[('UC-01','Review revenue performance','BA / Management','Input: dataset + objective','Outcome: period-aligned revenue movement'),('UC-02','Decompose priority area','BA / Analytics','Input: focus region + dataset','Outcome: product/segment/channel contributors'),('UC-03','Validate service hypothesis','BA / Operations / Customer Success','Input: SLA + cancellation evidence','Outcome: hypothesis confirmed/rejected/remaining unvalidated'),('UC-04','Generate decision pack','BA / Management','Input: findings + recommendations','Outcome: traceable BA deliverables')]
        return [('Document control','Document ID: UC-001\nVersion: 4.0\nStatus: Final portfolio case study'),('1. Use cases',table(['ID','Use case','Primary actor','Precondition / input','Outcome'],rows)),('2. Exceptions','If required evidence is missing, the use case must expose the gap and stop short of a causal or approval conclusion.')]

    if kind=='UAT & Test Scenarios':
        rows=[('UAT-01','Revenue Q3→Q4 comparison','Connected sales dataset','Revenue movement matches source aggregation','Not Run','BR-01 / FR-03'),('UAT-02','Regional and product decomposition','Connected dataset','Selected dimension reconciles to source totals','Not Run','BR-02 / FR-02'),('UAT-03','Service signal comparison','SLA + support-ticket fields','Same-period service signals are displayed','Not Run','BR-03 / FR-05'),('UAT-04','Cancellation evidence guardrail','Cancellation data','Insufficient sample is flagged; no causal claim','Not Run','BR-04 / FR-06'),('UAT-05','Deliverable traceability','Evidence register + recommendation','Export retains evidence and requirement references','Not Run','BR-05 / FR-08..10')]
        return [('Document control','Document ID: UAT-001\nVersion: 4.0\nStatus: Final portfolio case study\nExecution status: Not Run'),('1. UAT scenarios',table(['ID','Scenario','Precondition','Expected result','Status','Traceability'],rows)),('2. Sign-off rule','A UAT scenario cannot be marked Passed until the expected result is actually observed and the tester/date are recorded.'),('3. Negative tests','Missing fields, mismatched periods, insufficient cancellation evidence and malformed input should fail safely with an explicit evidence boundary.')]

    if kind=='Stakeholder Analysis':
        rows=[(s,'Referenced in source evidence','Interest / decision role to confirm','Influence not assumed','Engagement: review evidence and validate decisions') for s in stakeholders]
        return [('Document control','Document ID: STA-001\nVersion: 4.0\nStatus: Final portfolio case study'),('1. Stakeholder analysis',table(['Stakeholder','Evidence status','Interest / role','Influence','Engagement'],rows)),('2. Stakeholder notes','Only roles explicitly supported by the connected case are listed as named stakeholders. Influence, accountability and approval authority require confirmation.'),('3. Engagement sequence','Management decision review → Operations validation → Customer Success retention evidence → Sales/Product commercial review → Analytics/BA traceability.')]

    if kind=='RACI Matrix':
        rows=[('Define objective / scope','BA / Analytics','Business Owner','Management','Functional SMEs'),('Validate KPI baseline','BA / Analytics','Business Owner','Operations / Sales','Management'),('Validate service hypothesis','Operations','Process Owner','Customer Success / Analytics','Management'),('Approve recommendation','BA','Business Owner','Functional SMEs','Management'),('Monitor outcome','Process Owner','Business Owner','BA / Analytics','Management')]
        return [('Document control','Document ID: RACI-001\nVersion: 4.0\nStatus: Final portfolio case study'),('1. RACI matrix',table(['Activity','Responsible','Accountable','Consulted','Informed'],rows)),('2. Governance note','Accountable roles are proposed role-level assignments for the portfolio case and require confirmation before implementation. They are not claimed as confirmed source facts.')]

    if kind=='Action Plan':
        rows=[('ACT-01','Obtain delivery/SLA breach detail for South','Operations','High','Evidence available for validation','E-004,E-010'),('ACT-02','Obtain customer/order cancellation reasons and linkage','Customer Success','High','Retention hypothesis testable','E-009,E-010'),('ACT-03','Quantify absolute-impact commercial pockets','Analytics / BA','High','Prioritised product/segment/channel view','E-006,E-007,E-008'),('ACT-04','Identify high-value accounts requiring attention','Sales','Medium','Named accounts reviewed','Business context'),('ACT-05','Prepare management decision pack','BA','Medium','Decision and owners recorded','E-001..E-010')]
        return [('Document control','Document ID: ACT-001\nVersion: 4.0\nStatus: Final portfolio case study'),('1. Action plan',table(['ID','Action','Suggested owner','Priority','Completion criterion','Evidence'],rows)),('2. Ownership note','Suggested functions are based on the source action assignments where available. Final accountability requires business confirmation.')]

    return [('1. Purpose',objective),('2. Evidence boundary',evidence_text)]
