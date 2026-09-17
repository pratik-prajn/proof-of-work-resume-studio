"""Two renderers, one fail-closed verifier. User text is never executable markup."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import unicodedata
from xml.sax.saxutils import escape
import pdfplumber
from .guardrails import evaluate
from .models import ExportRequest
from .parser import parse_resume, ordered_blocks, source_hash

class ExportBlocked(ValueError):
    pass

def canonical_blocks(req: ExportRequest) -> list[dict]:
    if req.source_hash != source_hash(req.resume_text):
        raise ExportBlocked('Source changed. Analyze again before exporting.')
    blocks = parse_resume(req.resume_text)
    if set(req.overrides) - {b.id for b in blocks}:
        raise ExportBlocked('Unknown source block. Analyze again before exporting.')
    out = []
    for b in ordered_blocks(blocks, req.template):
        text = b.text
        if b.id in req.overrides:
            result = evaluate(b, req.overrides[b.id])
            if result['status'] != 'accepted':
                raise ExportBlocked('An edited block failed the preservation guard. Restore it before export.')
            text = result['output']
        out.append({'id': b.id, 'kind': b.kind, 'text': text, 'section': b.section})
    return out

def canonical_text(blocks: list[dict]) -> str:
    return '\n'.join(('- ' if b['kind'] == 'bullet' else '') + b['text'] for b in blocks)

def normalized(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', text).split())

def verify_pdf(pdf: bytes, expected: str) -> dict:
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        if not 1 <= len(doc.pages) <= 12:
            raise ExportBlocked('The document must contain between 1 and 12 pages.')
        extracts = []
        for page in doc.pages:
            for c in page.chars:
                if c.get('text', '').strip() and (c['x0'] < -1 or c['x1'] > page.width + 1 or c['top'] < -1 or c['bottom'] > page.height + 1):
                    raise ExportBlocked('PDF content would fall outside the page.')
            extracts.append(page.extract_text(x_tolerance=2, y_tolerance=3) or '')
        actual = '\n'.join(extracts)
        if normalized(actual) != normalized(expected):
            raise ExportBlocked('PDF text does not match approved content in reading order. Export blocked.')
        return {'verified': True, 'pages': len(doc.pages),
                'content_hash': hashlib.sha256(normalized(expected).encode()).hexdigest(),
                'pdf_hash': hashlib.sha256(pdf).hexdigest()}

def render_typst(blocks: list[dict]) -> bytes:
    import typst
    import datetime
    source = Path(__file__).with_name('resume.typ').read_bytes()
    return typst.compile(source, sys_inputs={'resume': json.dumps({'blocks': blocks}, ensure_ascii=False)},
                         timestamp=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))

def _font_paths() -> tuple[str, str]:
    configured = os.getenv('PDF_FONT_DIR')
    roots = [Path(configured)] if configured else []
    roots += [Path('/usr/share/fonts/truetype/noto'), Path('/usr/share/fonts/truetype/dejavu')]
    for root in roots:
        for family in ('NotoSans', 'DejaVuSans'):
            regular, bold = root / (family + '-Regular.ttf'), root / (family + '-Bold.ttf')
            if family == 'DejaVuSans':
                regular = root / 'DejaVuSans.ttf'
            if regular.exists() and bold.exists():
                return str(regular), str(bold)
    raise ExportBlocked('Install Noto Sans fonts or set PDF_FONT_DIR; fonts are not bundled.')

def render_reportlab(blocks: list[dict]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    regular, bold = _font_paths()
    pdfmetrics.registerFont(TTFont('Studio', regular))
    pdfmetrics.registerFont(TTFont('Studio-Bold', bold))
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=46, leftMargin=46,
                            topMargin=42, bottomMargin=42, title='Resume', author='', pageCompression=1)
    styles = {
        'name': ParagraphStyle('name', fontName='Studio-Bold', fontSize=22, leading=27, spaceAfter=8, keepWithNext=True),
        'heading': ParagraphStyle('heading', fontName='Studio-Bold', fontSize=11.5, leading=16, spaceBefore=12, spaceAfter=5, keepWithNext=True, textColor=colors.HexColor('#172F3D')),
        'line': ParagraphStyle('line', fontName='Studio', fontSize=10.5, leading=15, spaceAfter=4),
        'bullet': ParagraphStyle('bullet', fontName='Studio', fontSize=10.5, leading=15, spaceAfter=5),
    }
    story = [Paragraph(escape(('- ' if b['kind'] == 'bullet' else '') + b['text']), styles.get(b['kind'], styles['line'])) for b in blocks]
    doc.build(story)
    return output.getvalue()

def render_and_verify(req: ExportRequest, engine: str) -> tuple[bytes, dict]:
    blocks = canonical_blocks(req)
    # Missing glyphs can survive text extraction while displaying as blank boxes.
    # Fail closed before rendering rather than claiming that extraction alone checks this.
    from fontTools.ttLib import TTFont as FontReader
    regular, bold = _font_paths()
    for path in (regular, bold):
        with FontReader(path) as font:
            cmap = font.getBestCmap() or {}
            missing = {ord(c) for c in canonical_text(blocks) if not c.isspace() and ord(c) not in cmap}
        if missing:
            raise ExportBlocked('The configured font does not cover all input characters. Export blocked; use a compatible font configuration.')
    if engine == 'typst':
        pdf = render_typst(blocks)
    elif engine == 'reportlab':
        pdf = render_reportlab(blocks)
    else:
        raise ExportBlocked('Unknown PDF renderer.')
    verification = verify_pdf(pdf, canonical_text(blocks))
    verification['engine'] = engine
    return pdf, verification
