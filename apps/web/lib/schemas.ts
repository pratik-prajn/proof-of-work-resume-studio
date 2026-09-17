import { z } from 'zod';

// This contract intentionally mirrors the strict Pydantic request models.
// Limits use Unicode code points, matching Python rather than UTF-16 units.
const sourceText = (max: number) => z.string().superRefine((value, ctx) => {
  if ([...value].length > max || [...value.trim()].length < 10)
    ctx.addIssue({ code: 'custom', message: `Enter between 10 and ${max.toLocaleString()} characters.` });
  if (/[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\u202a-\u202e\u2066-\u2069]/u.test(value))
    ctx.addIssue({ code: 'custom', message: 'Unsupported control characters. Paste plain text.' });
  const lines = value.split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/u);
  if (lines.at(-1) === '') lines.pop();
  if (lines.length > 250)
    ctx.addIssue({ code: 'custom', message: 'Maximum 250 lines per input.' });
});
export const SourceSchema = z.strictObject({
  resume_text: sourceText(20000), job_description: sourceText(30000),
  adult_confirmed: z.literal(true), processing_consent: z.literal(true),
});
export const DecisionSchema = z.strictObject({
  id: z.string().min(1).max(80), decision: z.enum(['include', 'exclude']), reason: z.string().max(300).default(''),
});
export const AnalyzeSchema = z.strictObject({
  ...SourceSchema.shape, decisions: z.array(DecisionSchema).max(200).default([]), requirements_reviewed: z.boolean().default(false),
}).refine(v => new Set(v.decisions.map(d => d.id)).size === v.decisions.length, 'Duplicate requirement decisions.');
const hash = z.string().regex(/^[a-f0-9]{64}$/);
export const RewriteSchema = z.strictObject({
  ...SourceSchema.shape, source_hash: hash, use_llm: z.boolean().default(false), llm_consent: z.boolean().default(false),
});
export const GuardSchema = z.strictObject({
  ...SourceSchema.shape, source_hash: hash, block_id: z.string().min(1).max(80), candidate: z.string().min(1).max(3000),
});
const overrides = z.record(z.string().max(80), z.string().max(3000)).refine(v => Object.keys(v).length <= 200);
export const ExportSchema = z.strictObject({
  ...SourceSchema.shape, source_hash: hash, overrides: overrides.default({}), template: z.enum(['professional', 'fresher']).default('professional'),
});
export const WorkspaceSchema = z.strictObject({
  schema_version: z.literal('1.0.0').default('1.0.0'),
  resume_text: z.string().max(20000), job_description: z.string().max(30000),
  template: z.enum(['professional', 'fresher']).default('professional'),
  decisions: z.array(DecisionSchema).max(200).default([]), requirements_reviewed: z.boolean().default(false),
  overrides: overrides.default({}), source_hash: z.string().default(''),
});
export const SaveDraftSchema = z.strictObject({ title: z.string().min(1).max(100), storage_consent: z.literal(true), workspace: WorkspaceSchema });
export const RepoSchema = z.strictObject({ url: z.string().max(300), adult_confirmed: z.literal(true), network_consent: z.literal(true) });

export const BlockSchema = z.object({
  id: z.string(), kind: z.enum(['name', 'heading', 'line', 'bullet']), section: z.string(), group: z.number(),
  text: z.string(), source_start: z.number(), source_end: z.number(), source_text: z.string(), evidence: z.literal('user_provided'),
});
const EvidenceSchema = z.object({ block_id: z.string(), text: z.string(), quote: z.string(), start: z.number(), end: z.number(), status: z.enum(['negated', 'learning', 'listed', 'mentioned']), source: z.string() });
export const RequirementSchema = z.object({
  id: z.string(), kind: z.enum(['skill', 'unresolved']), skill_ids: z.array(z.string()), label: z.string(),
  jd_text: z.string(), jd_start: z.number(), jd_end: z.number(), priority: z.string(), alternative: z.boolean(),
  excluded: z.boolean(), exclusion_reason: z.string(), evidence: z.array(EvidenceSchema),
  status: z.enum(['matched', 'missing', 'unresolved', 'excluded']),
});
export const AnalysisSchema = z.object({
  source_hash: hash, assessment_hash: hash, score: z.number().nullable(), matched: z.number(), total: z.number(),
  unresolved: z.number(), complete: z.boolean(), requirements: z.array(RequirementSchema), blocks: z.array(BlockSchema),
  versions: z.record(z.string(), z.string()), warnings: z.array(z.string()),
});
export const GuardResultSchema = z.object({
  block_id: z.string(), status: z.enum(['accepted', 'rejected']), original: z.string(), candidate: z.string(), output: z.string(),
  changed: z.boolean(), reasons: z.array(z.string()), source_start: z.number(), source_end: z.number(), guard_version: z.string(),
});
export const RewriteResultSchema = z.object({ items: z.array(GuardResultSchema), notice: z.string() });
export const ConfigSchema = z.object({ contract_version: z.string(), taxonomy_version: z.string(), skill_count: z.number(), history_enabled: z.boolean(), llm_enabled: z.boolean(), github_enabled: z.boolean(), pdf_engine: z.string(), max_upload_bytes: z.number() });
export type Analysis = z.infer<typeof AnalysisSchema>;
export type Block = z.infer<typeof BlockSchema>;
export type Decision = z.infer<typeof DecisionSchema>;
export type GuardResult = z.infer<typeof GuardResultSchema>;
export type Workspace = z.infer<typeof WorkspaceSchema>;
export type Config = z.infer<typeof ConfigSchema>;
