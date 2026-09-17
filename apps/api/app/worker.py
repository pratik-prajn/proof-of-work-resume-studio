"""Bounded child process for PDF parsing/rendering and notebook inspection."""
import base64
import io
import json
import sys

def limit_resources():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
    except (ImportError, ValueError, OSError):
        pass

def process(payload: dict) -> dict:
    action = payload['action']
    if action == 'render':
        from .models import ExportRequest
        from .pdf import render_and_verify
        data, report = render_and_verify(ExportRequest.model_validate(payload['request']), payload['engine'])
        return {'pdf': base64.b64encode(data).decode(), 'verification': report}
    if action == 'import_pdf':
        import pdfplumber
        raw = base64.b64decode(payload['data'], validate=True)
        if not raw.startswith(b'%PDF-'):
            raise ValueError('Not a PDF.')
        with pdfplumber.open(io.BytesIO(raw)) as doc:
            if len(doc.pages) > 12:
                raise ValueError('PDF import supports up to 12 pages.')
            text = '\n\n'.join(p.extract_text() or '' for p in doc.pages)
        if len(text.strip()) < 10:
            raise ValueError('No extractable text; scanned PDFs are not supported.')
        if len(text) > 20000:
            raise ValueError('Imported text exceeds 20,000 characters.')
        return {'text': text, 'warning': 'Review all imported text. Columns, tables and OCR are not inferred. Import is not evidence verification.'}
    if action == 'notebook':
        from .evidence import inspect_notebook
        return inspect_notebook(base64.b64decode(payload['data'], validate=True))
    raise ValueError('Unknown worker action.')

def main():
    limit_resources()
    try:
        payload = json.loads(sys.stdin.buffer.read(3 * 1024 * 1024))
        print(json.dumps({'ok': True, 'result': process(payload)}))
    except Exception as exc:
        from .pdf import ExportBlocked
        # No stack traces or user-supplied compiler snippets in logs or responses.
        message = str(exc) if isinstance(exc, ExportBlocked) else 'The file could not be processed safely. Check its format, installed renderer, and size. Scanned PDFs are not supported.'
        print(json.dumps({'ok': False, 'error': message}))
        sys.exit(1)

if __name__ == '__main__':
    main()
