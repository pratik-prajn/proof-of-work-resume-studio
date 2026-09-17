import { describe, expect, it } from 'vitest';
import { SourceSchema, AnalyzeSchema, ExportSchema, WorkspaceSchema } from '../lib/schemas';
import cases from './contract-cases.json';
import sample from '../lib/sample.json';
describe('Shared Pydantic/Zod request fixtures', () => {
  for (const item of cases) it(item.name, () => expect(SourceSchema.safeParse(item.payload).success).toBe(item.valid));
});
it('does not coerce review flags', () => {
  expect(AnalyzeSchema.safeParse({ ...sample, requirements_reviewed: 'true' }).success).toBe(false);
});
it('rejects duplicate decisions', () => {
  expect(AnalyzeSchema.safeParse({ ...sample, decisions: [{ id: 'a', decision: 'include' }, { id: 'a', decision: 'include' }] }).success).toBe(false);
});
it('requires a source hash for export', () => {
  expect(ExportSchema.safeParse(sample).success).toBe(false);
});
it('rejects unknown template and fields', () => {
  expect(ExportSchema.safeParse({ ...sample, source_hash: 'a'.repeat(64), template: 'invented' }).success).toBe(false);
  expect(WorkspaceSchema.safeParse({ resume_text: '', job_description: '', secret: 'no' }).success).toBe(false);
});
it('retains original whitespace, rather than quietly editing facts', () => {
  const result = SourceSchema.parse({ ...sample, resume_text: '  Person Name\nSkills\nPython  ' });
  expect(result.resume_text).toBe('  Person Name\nSkills\nPython  ');
});
