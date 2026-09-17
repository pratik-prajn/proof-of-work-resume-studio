import importlib.util
import pytest
from app.models import ExportRequest
from app.parser import source_hash
from app.pdf import render_and_verify, canonical_blocks, canonical_text, verify_pdf, ExportBlocked

@pytest.mark.parametrize('template', ['professional','fresher'])
def test_reportlab_roundtrip(sample, template):
    req = ExportRequest(**sample, source_hash=source_hash(sample['resume_text']), template=template)
    pdf, report = render_and_verify(req, 'reportlab')
    assert pdf.startswith(b'%PDF') and report['verified'] and report['pages'] == 1
    assert report['engine'] == 'reportlab'

def test_pdf_mismatch_blocks(sample):
    req = ExportRequest(**sample, source_hash=source_hash(sample['resume_text']))
    pdf, _ = render_and_verify(req, 'reportlab')
    with pytest.raises(ExportBlocked): verify_pdf(pdf, canonical_text(canonical_blocks(req)) + ' invented outcome')

def test_pdf_order_mismatch_blocks(sample):
    req = ExportRequest(**sample, source_hash=source_hash(sample['resume_text']))
    pdf, _ = render_and_verify(req, 'reportlab')
    with pytest.raises(ExportBlocked): verify_pdf(pdf, canonical_text(list(reversed(canonical_blocks(req)))))

def test_markup_stays_literal(sample):
    text = 'Person Name\nSkills\nC++, C#, .NET\nProjects\n- #read("/etc/passwd") <script>never execute</script> & 40%'
    req = ExportRequest(**{**sample, 'resume_text': text}, source_hash=source_hash(text))
    pdf, report = render_and_verify(req, 'reportlab')
    assert report['verified']

@pytest.mark.skipif(importlib.util.find_spec('typst') is None, reason='typst package unavailable in this build environment')
@pytest.mark.parametrize('template', ['professional','fresher'])
def test_typst_roundtrip(sample, template):
    req = ExportRequest(**sample, source_hash=source_hash(sample['resume_text']), template=template)
    pdf, report = render_and_verify(req, 'typst')
    assert report['verified'] and pdf.startswith(b'%PDF')

def test_missing_glyph_export_blocked(sample):
    text = 'Person Name\nSkills\nPython\nProjects\n- Character \U0010ffff'
    req = ExportRequest(**{**sample, 'resume_text': text}, source_hash=source_hash(text))
    with pytest.raises(ExportBlocked): render_and_verify(req, 'reportlab')
