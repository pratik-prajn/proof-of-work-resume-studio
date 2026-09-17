import { NextRequest, NextResponse } from 'next/server';
import { SignJWT } from 'jose';
import { auth } from '@/auth';
import { AnalyzeSchema, RewriteSchema, GuardSchema, ExportSchema, RepoSchema, SaveDraftSchema } from '@/lib/schemas';
import { z } from 'zod';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const DEV_SECRET = 'local-development-only-change-before-deployment';
const schemas: Record<string, z.ZodType> = { analyze: AnalyzeSchema, rewrite: RewriteSchema, guard: GuardSchema, 'export/pdf': ExportSchema, 'evidence/github': RepoSchema, history: SaveDraftSchema };
const MAX = 2 * 1024 * 1024;
async function boundedBody(request: NextRequest): Promise<Uint8Array> {
  const reader = request.body?.getReader();
  if (!reader) return new Uint8Array();
  const chunks: Uint8Array[] = []; let size = 0;
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    size += value.byteLength;
    if (size > MAX) { await reader.cancel(); throw new Error('Request exceeds 2 MB.'); }
    chunks.push(value);
  }
  const all = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { all.set(chunk, offset); offset += chunk.byteLength; }
  return all;
}
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path.join('/');
  if (!/^(config|analyze|rewrite|guard|export\/pdf|import\/pdf|evidence\/(notebook|github)|history(?:\/[a-f0-9-]{36})?)$/.test(path))
    return NextResponse.json({ detail: 'Not found.' }, { status: 404 });
  const method = request.method;
  if ((path === 'config' && method !== 'GET') || (!['config', 'history'].includes(path) && !path.startsWith('history/') && method !== 'POST') || (path.startsWith('history/') && !['GET', 'DELETE'].includes(method)))
    return NextResponse.json({ detail: 'Method not allowed.' }, { status: 405 });
  if (method !== 'GET') {
    const expected = new URL(process.env.APP_ORIGIN || request.url).origin;
    if (request.headers.get('origin') !== expected)
      return NextResponse.json({ detail: 'Origin check failed.' }, { status: 403 });
  }
  const internalKey = process.env.INTERNAL_API_KEY || DEV_SECRET;
  const tokenSecret = process.env.API_TOKEN_SECRET || DEV_SECRET;
  if (process.env.NODE_ENV === 'production' && (internalKey === DEV_SECRET || tokenSecret === DEV_SECRET))
    return NextResponse.json({ detail: 'Server secrets are not configured. Run scripts/setup.py.' }, { status: 503 });
  const headers = new Headers({ 'X-Internal-Key': internalKey });
  if (path.startsWith('history')) {
    const session = await auth();
    if (!session?.user?.id?.startsWith('github:'))
      return NextResponse.json({ detail: 'Sign in to use saved history.' }, { status: 401 });
    const token = await new SignJWT({}).setProtectedHeader({ alg: 'HS256' }).setSubject(session.user.id)
      .setIssuer('resume-web').setAudience('resume-api').setIssuedAt().setExpirationTime('60s')
      .sign(new TextEncoder().encode(tokenSecret));
    headers.set('Authorization', `Bearer ${token}`);
  }
  try {
    let body: BodyInit | undefined;
    if (method === 'POST') {
      const bytes = await boundedBody(request);
      if (schemas[path]) {
        const parsed = schemas[path].safeParse(JSON.parse(new TextDecoder().decode(bytes)));
        if (!parsed.success) return NextResponse.json({ detail: parsed.error.issues.map(x => ({ msg: x.message, path: x.path })) }, { status: 422 });
        body = JSON.stringify(parsed.data); headers.set('Content-Type', 'application/json');
      } else {
        body = new Blob([bytes as BlobPart]);
        headers.set('Content-Type', request.headers.get('content-type') || 'application/octet-stream');
        headers.set('X-Adult-Confirmed', request.headers.get('x-adult-confirmed') || 'false');
        headers.set('X-Processing-Consent', request.headers.get('x-processing-consent') || 'false');
      }
    }
    const upstream = await fetch(`${process.env.API_BASE_URL || 'http://127.0.0.1:8000'}/v1/${path}`, {
      method, headers, body, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(35000),
    });
    const safe = new Headers({ 'Cache-Control': 'no-store' });
    for (const key of ['content-type', 'content-disposition', 'x-text-verified', 'x-content-sha256', 'x-pdf-sha256', 'x-pdf-pages', 'x-pdf-engine', 'retry-after']) {
      const value = upstream.headers.get(key); if (value) safe.set(key, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: safe });
  } catch (error) {
    const badInput = error instanceof SyntaxError || (error instanceof Error && error.message === 'Request exceeds 2 MB.');
    return NextResponse.json({ detail: badInput ? 'Invalid or oversized request.' : 'API unavailable or processing timed out. Start the FastAPI service and retry.' }, { status: badInput ? 422 : 502 });
  }
}
export { proxy as GET, proxy as POST, proxy as DELETE };
