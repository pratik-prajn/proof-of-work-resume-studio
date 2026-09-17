from __future__ import annotations
import asyncio
import base64
from collections import deque
from contextlib import asynccontextmanager, suppress
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from .config import settings
from .models import AnalyzeRequest, RewriteRequest, GuardRequest, ExportRequest, SaveDraftRequest, InspectRepoRequest
from .parser import parse_resume, source_hash
from .scoring import analyze, TAXONOMY
from .guardrails import evaluate, suggestion
from .security import BodyLimitMiddleware, internal_boundary, authenticated_owner
from . import storage

@asynccontextmanager
async def lifespan(app):
    settings()
    storage.init_storage()
    async def retention_loop():
        while True:
            if settings().history_enabled:
                try:
                    await run_in_threadpool(storage.prune_expired)
                except Exception:
                    pass  # Fail closed on reads; monitor database health separately.
            await asyncio.sleep(300)
    retention = asyncio.create_task(retention_loop())
    try:
        yield
    finally:
        retention.cancel()
        with suppress(asyncio.CancelledError):
            await retention

app = FastAPI(title='Proof-of-Work Resume Studio', version='1.0.0', lifespan=lifespan,
              docs_url='/docs' if os.getenv('APP_ENV') != 'production' else None,
              redoc_url=None, openapi_url='/openapi.json' if os.getenv('APP_ENV') != 'production' else None)
app.add_middleware(BodyLimitMiddleware)
router = APIRouter(prefix='/v1', dependencies=[Depends(internal_boundary)])
workers = asyncio.Semaphore(2)
request_times: deque = deque()

@app.middleware('http')
async def privacy_headers(request: Request, call_next):
    # In-process global safety limit. Configure per-IP limits at the production ingress.
    now = time.monotonic()
    while request_times and request_times[0] < now - 60:
        request_times.popleft()
    if request.url.path != '/health' and len(request_times) >= 240:
        return JSONResponse({'detail': 'Service busy. Try again shortly.'}, status_code=429, headers={'Retry-After': '60'})
    if request.url.path != '/health':
        request_times.append(now)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Do not echo Pydantic's `input` field, which can contain the entire resume.
    return JSONResponse({'detail': [{'loc': list(e['loc']), 'msg': e['msg'], 'type': e['type']} for e in exc.errors()]}, status_code=422)

@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=422)

@app.get('/health')
def health():
    return {'status': 'ok', 'version': '1.0.0'}

@router.get('/config')
def config():
    cfg = settings()
    return {'contract_version': '1.0.0', 'taxonomy_version': TAXONOMY['version'],
            'skill_count': len(TAXONOMY['skills']), 'history_enabled': cfg.history_enabled,
            'llm_enabled': bool(cfg.llm_url and cfg.llm_model), 'github_enabled': cfg.github_enabled,
            'pdf_engine': cfg.pdf_engine, 'max_upload_bytes': 1500000}

@router.post('/analyze')
def analyze_route(req: AnalyzeRequest):
    return analyze(req)

def check_source(req):
    if req.source_hash != source_hash(req.resume_text):
        raise HTTPException(409, 'Source changed. Analyze again.')

@router.post('/rewrite')
async def rewrite(req: RewriteRequest):
    check_source(req)
    blocks = parse_resume(req.resume_text)
    candidates = {}
    notice = 'Deterministic rules only. No model call was made.'
    if req.use_llm:
        if not req.llm_consent:
            raise HTTPException(422, 'Explicit consent is required before sending bullet text to a configured model.')
        if not settings().llm_url:
            raise HTTPException(503, 'No model is configured. Use deterministic improvements.')
        from .llm import propose
        try:
            candidates = await propose(blocks)
            notice = 'The configured model received bullet text. Every proposal was checked by the same closed-world guard.'
        except Exception:
            notice = 'Model unavailable or invalid response. No model output was used; deterministic rules were applied.'
    return {'items': [evaluate(b, candidates.get(b.id, suggestion(b))) for b in blocks if b.kind == 'bullet'], 'notice': notice}

@router.post('/guard')
def guard(req: GuardRequest):
    check_source(req)
    block = next((b for b in parse_resume(req.resume_text) if b.id == req.block_id), None)
    if not block:
        raise HTTPException(404, 'Source block not found.')
    return evaluate(block, req.candidate)

def child(payload):
    try:
        result = subprocess.run([sys.executable, '-m', 'app.worker'], input=json.dumps(payload).encode(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25,
                                cwd=Path(__file__).resolve().parent.parent)
        response = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        raise HTTPException(422, 'Processing exceeded safe limits or the worker could not start.') from None
    if not response.get('ok'):
        raise HTTPException(422, response.get('error', 'Processing failed.'))
    return response['result']

async def run_child(payload):
    async with workers:
        return await run_in_threadpool(child, payload)

@router.post('/export/pdf')
async def export_pdf(req: ExportRequest):
    check_source(req)
    from .pdf import canonical_blocks
    canonical_blocks(req)  # Validate before creating a worker.
    result = await run_child({'action': 'render', 'request': req.model_dump(), 'engine': settings().pdf_engine})
    report = result['verification']
    return Response(base64.b64decode(result['pdf']), media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="resume.pdf"',
        'X-Text-Verified': 'true', 'X-Content-SHA256': report['content_hash'],
        'X-PDF-SHA256': report['pdf_hash'], 'X-PDF-Pages': str(report['pages']), 'X-PDF-Engine': report['engine'],
    })

async def upload_bytes(request: Request, file: UploadFile):
    # Age and processing consent precede file upload, too.
    if request.headers.get('x-adult-confirmed') != 'true' or request.headers.get('x-processing-consent') != 'true':
        raise HTTPException(422, 'Confirm age and processing consent before uploading.')
    raw = await file.read(1500001)
    await file.close()
    if len(raw) > 1500000:
        raise HTTPException(413, 'Maximum upload size is 1.5 MB.')
    return raw

@router.post('/import/pdf')
async def import_pdf(request: Request, file: UploadFile = File()):
    raw = await upload_bytes(request, file)
    return await run_child({'action': 'import_pdf', 'data': base64.b64encode(raw).decode()})

@router.post('/evidence/notebook')
async def notebook(request: Request, file: UploadFile = File()):
    raw = await upload_bytes(request, file)
    return await run_child({'action': 'notebook', 'data': base64.b64encode(raw).decode()})

@router.post('/evidence/github')
async def github(req: InspectRepoRequest):
    if not settings().github_enabled:
        raise HTTPException(403, 'The administrator has not enabled public GitHub inspection.')
    from .evidence import inspect_github
    return await inspect_github(req.url)

@router.get('/history')
def history(owner: str = Depends(authenticated_owner)):
    return {'items': storage.list_drafts(owner)}

@router.post('/history', status_code=201)
def save_history(req: SaveDraftRequest, owner: str = Depends(authenticated_owner)):
    return storage.save(owner, req.title, req.workspace.model_dump())

@router.get('/history/{draft_id}')
def get_history(draft_id: str, owner: str = Depends(authenticated_owner)):
    result = storage.get_draft(owner, draft_id)
    if result is None:
        raise HTTPException(404, 'Snapshot not found.')
    return result

@router.delete('/history/{draft_id}')
def delete_history(draft_id: str, owner: str = Depends(authenticated_owner)):
    if not storage.remove(owner, draft_id):
        raise HTTPException(404, 'Snapshot not found.')
    return {'deleted': True}

@router.delete('/history')
def delete_all_history(owner: str = Depends(authenticated_owner)):
    return {'deleted': storage.remove(owner)}

app.include_router(router)
