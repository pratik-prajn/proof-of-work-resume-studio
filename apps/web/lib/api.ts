import type { z } from 'zod';
export async function api(path: string, body?: unknown, method?: string): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`/api/backend/${path}`, { method: method ?? (body ? 'POST' : 'GET'),
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined, cache: 'no-store' });
  } catch { throw new Error('Connection failed. Check that the frontend and API are running.'); }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data.detail;
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((x: {msg: string}) => x.msg).join(' ') : 'The request could not be completed.');
  }
  return response;
}
export async function jsonApi<T>(path: string, schema: z.ZodType<T>, body?: unknown): Promise<T> {
  return schema.parse(await (await api(path, body)).json());
}
export function download(data: Blob, name: string) {
  const url = URL.createObjectURL(data);
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function upload(path: string, file: File): Promise<unknown> {
  if (file.size > 1500000) throw new Error('Maximum upload size is 1.5 MB.');
  const form = new FormData(); form.append('file', file);
  const response = await fetch(`/api/backend/${path}`, { method: 'POST', body: form,
    headers: { 'X-Adult-Confirmed': 'true', 'X-Processing-Consent': 'true' } });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Upload failed.');
  return data;
}
