"""Real flowchart rendering for AS-IS / TO-BE process specs, using graphviz -
the same category of tool as draw.io/Visio, not a text placeholder."""
import os
import re
import tempfile
import graphviz

BRAND_DARK = '1F2A24'
BRAND_ACCENT = '4B5D3A'
BRAND_LINE = 'C9C2AE'
DECISION_FILL = 'E9C77B'
STEP_FILL = 'F3F1E7'
PAIN_FILL = 'DD8E7A'


def render_process_flow(steps, title, pain_indices=None, decision_indices=None, filename=None):
    """Render a left-to-right swimlane-style flowchart: Start -> step boxes ->
    decision diamonds where flagged -> End. Steps flagged as pain points are
    shaded red so a reviewer can see exactly where the process breaks down.
    Returns the path to a rendered PNG file. Falls back to a pure-Python
    (PIL) renderer if the Graphviz binary isn't installed on this machine,
    so the app still works without a separate Graphviz install."""
    try:
        return _render_with_graphviz(steps, title, pain_indices, decision_indices, filename)
    except Exception:
        return _render_with_pil(steps, title, pain_indices, decision_indices, filename)


def _render_with_graphviz(steps, title, pain_indices=None, decision_indices=None, filename=None):
    pain_indices = set(pain_indices or [])
    decision_indices = set(decision_indices or [])
    g = graphviz.Digraph(format='png')
    g.attr(rankdir='LR', bgcolor='white', fontsize='11', fontname='Helvetica', dpi='170',
           label=title, labelloc='t', fontcolor='#' + BRAND_DARK, nodesep='0.35', ranksep='0.55')
    g.attr('node', fontname='Helvetica', fontsize='10', fontcolor='#' + BRAND_DARK)
    g.attr('edge', color='#' + BRAND_ACCENT, arrowsize='0.7')

    g.node('start', 'Start', shape='ellipse', style='filled',
           fillcolor='#' + BRAND_ACCENT, fontcolor='white')
    prev = 'start'
    for i, step in enumerate(steps, 1):
        nid = f's{i}'
        label = _wrap(step, 28)
        if i in decision_indices:
            g.node(nid, label, shape='diamond', style='filled', fillcolor='#' + DECISION_FILL)
        elif i in pain_indices:
            g.node(nid, label, shape='box', style='rounded,filled', fillcolor='#' + PAIN_FILL,
                   fontcolor='white')
        else:
            g.node(nid, label, shape='box', style='rounded,filled', fillcolor='#' + STEP_FILL)
        g.edge(prev, nid)
        prev = nid
    g.node('end', 'End', shape='ellipse', style='filled', fillcolor='#' + BRAND_ACCENT, fontcolor='white')
    g.edge(prev, 'end')

    out_dir = tempfile.mkdtemp(prefix='bizlens_diagram_')
    stem = os.path.join(out_dir, filename or 'flow')
    rendered_path = g.render(filename=stem, cleanup=True)
    return rendered_path


def _render_with_pil(steps, title, pain_indices=None, decision_indices=None, filename=None):
    """Dependency-free fallback: draws the same left-to-right box-and-arrow
    flow with plain PIL when the Graphviz binary isn't on this machine."""
    from PIL import Image, ImageDraw, ImageFont
    pain_indices = set(pain_indices or [])
    decision_indices = set(decision_indices or [])
    labels = ['Start'] + [_wrap(s, 22) for s in steps] + ['End']
    box_w, box_h, gap, pad_top = 190, 90, 55, 60
    width = pad_top + len(labels) * (box_w + gap)
    height = box_h + 2 * pad_top
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
    except Exception:
        font = ImageFont.load_default(); title_font = font
    draw.text((width / 2, 24), title, fill='#' + BRAND_DARK, font=title_font, anchor='mm')

    x = pad_top // 2
    centers = []
    for i, label in enumerate(labels):
        y = pad_top
        step_idx = i  # 0 = start, len-1 = end
        is_start_end = step_idx == 0 or step_idx == len(labels) - 1
        if is_start_end:
            fill = '#' + BRAND_ACCENT; text_color = 'white'
            draw.ellipse([x, y, x + box_w, y + box_h], fill=fill)
        elif step_idx in decision_indices:
            fill = '#' + DECISION_FILL; text_color = '#' + BRAND_DARK
            cx, cy = x + box_w / 2, y + box_h / 2
            draw.polygon([(cx, y), (x + box_w, cy), (cx, y + box_h), (x, cy)], fill=fill)
        elif step_idx in pain_indices:
            fill = '#' + PAIN_FILL; text_color = 'white'
            draw.rounded_rectangle([x, y, x + box_w, y + box_h], radius=14, fill=fill)
        else:
            fill = '#' + STEP_FILL; text_color = '#' + BRAND_DARK
            draw.rounded_rectangle([x, y, x + box_w, y + box_h], radius=14, fill=fill)
        draw.multiline_text((x + box_w / 2, y + box_h / 2), label, fill=text_color, font=font,
                             anchor='mm', align='center')
        centers.append((x + box_w, y + box_h / 2))
        x += box_w + gap

    for i in range(len(centers) - 1):
        x1, y1 = centers[i]
        x2, y2 = x1 + gap, y1
        draw.line([x1, y1, x2, y2], fill='#' + BRAND_ACCENT, width=3)
        draw.polygon([(x2, y2), (x2 - 10, y2 - 6), (x2 - 10, y2 + 6)], fill='#' + BRAND_ACCENT)

    out_dir = tempfile.mkdtemp(prefix='bizlens_diagram_')
    path = os.path.join(out_dir, (filename or 'flow') + '.png')
    img.save(path)
    return path


def _wrap(text, width):
    words = str(text).split()
    lines, cur = [], ''
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return '\n'.join(lines[:4])


IMAGE_MARKER = '::IMAGE::'


def diagram_body(image_path, caption=''):
    """Body-string protocol so make_docx/make_pdf can detect a diagram section
    and embed the rendered PNG instead of dumping raw text."""
    return f'{IMAGE_MARKER}{image_path}{IMAGE_MARKER}\n{caption}'


def parse_diagram_body(body):
    """Returns (image_path, caption_text) if body is a diagram section, else None."""
    m = re.match(rf'^{re.escape(IMAGE_MARKER)}(.*?){re.escape(IMAGE_MARKER)}\n?(.*)$', str(body), re.S)
    if not m:
        return None
    return m.group(1), m.group(2)
