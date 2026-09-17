'use client';
import { useEffect, useRef, useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import Link from 'next/link';
import { signIn, signOut } from 'next-auth/react';
import { ArrowRight, ArrowLeft, Check, CheckCheck, CheckCircle2, ChevronRight, FileText, Download, Upload, ShieldCheck, LockKeyhole, Sparkles, RotateCcw, X, AlertTriangle, LoaderCircle, Layers3, ScanText, Code2, Save, Trash2, History, ExternalLink, CircleHelp } from 'lucide-react';
import { z } from 'zod';
import { api, jsonApi, download, upload } from '@/lib/api';
import { AnalyzeSchema, AnalysisSchema, ConfigSchema, RewriteSchema, RewriteResultSchema, GuardSchema, GuardResultSchema, ExportSchema, WorkspaceSchema, SaveDraftSchema, RepoSchema } from '@/lib/schemas';
import type { Analysis, Config, Decision, GuardResult, Workspace } from '@/lib/schemas';
import sample from '@/lib/sample.json';

const STEPS = [
  { title: 'Your sources', subtitle: 'Resume + job description', icon: FileText },
  { title: 'Skill coverage', subtitle: 'See the evidence', icon: ScanText },
  { title: 'Refine safely', subtitle: 'Improve, never invent', icon: ShieldCheck },
  { title: 'Export resume', subtitle: 'Verify, then download', icon: Download },
];
type Inspection = { kind: string; facts: string[]; limitations: string[]; sha256?: string; url?: string };
const InspectionSchema = z.object({ kind: z.string(), facts: z.array(z.string()), limitations: z.array(z.string()), sha256: z.string().optional(), url: z.string().optional() });
const HistorySchema = z.object({ items: z.array(z.object({ id: z.string(), title: z.string(), created_at: z.string(), expires_at: z.string() })) });
type HistoryItem = z.infer<typeof HistorySchema>['items'][number];

function SmallLabel({ children }: { children: ReactNode }) { return <span className="eyebrow">{children}</span>; }

export function Studio({ authEnabled, signedIn, userName }: { authEnabled: boolean; signedIn: boolean; userName: string }) {
  const [gate, setGate] = useState(false);
  const [adult, setAdult] = useState(false);
  const [consent, setConsent] = useState(false);
  const [step, setStep] = useState(0);
  const [resume, setResume] = useState('');
  const [jd, setJd] = useState('');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [reviewed, setReviewed] = useState(false);
  const [reviewDirty, setReviewDirty] = useState(false);
  const [rewrites, setRewrites] = useState<GuardResult[]>([]);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [template, setTemplate] = useState<'professional' | 'fresher'>('professional');
  const [candidate, setCandidate] = useState('');
  const [testBlock, setTestBlock] = useState('');
  const [guardResult, setGuardResult] = useState<GuardResult | null>(null);
  const [llmConsent, setLlmConsent] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pdfReport, setPdfReport] = useState<{ pages: string; hash: string; engine: string } | null>(null);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [repo, setRepo] = useState('');
  const [showEvidence, setShowEvidence] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [storageConsent, setStorageConsent] = useState(false);
  const [historyTitle, setHistoryTitle] = useState('My resume workspace');
  const fileInput = useRef<HTMLInputElement>(null);
  const workspaceInput = useRef<HTMLInputElement>(null);
  const notebookInput = useRef<HTMLInputElement>(null);

  useEffect(() => { jsonApi('config', ConfigSchema).then(setConfig).catch(() => setError('The API is not connected yet. Start the backend to use the studio.')); }, []);
  useEffect(() => {
    const prevent = (event: BeforeUnloadEvent) => { if (resume || jd) event.preventDefault(); };
    window.addEventListener('beforeunload', prevent); return () => window.removeEventListener('beforeunload', prevent);
  }, [resume, jd]);

  const source = () => ({ resume_text: resume, job_description: jd, adult_confirmed: true as const, processing_consent: true as const });
  function invalidate() { setAnalysis(null); setRewrites([]); setOverrides({}); setGuardResult(null); setPdfReport(null); setDecisions([]); setReviewed(false); setReviewDirty(false); }
  async function task(name: string, action: () => Promise<void>) {
    setBusy(name); setError(''); setNotice('');
    try { await action(); } catch (e) { setError(e instanceof z.ZodError ? e.issues.map(x => x.message).join(' ') : e instanceof Error ? e.message : 'Something went wrong.'); }
    finally { setBusy(''); }
  }
  function useSample() { invalidate(); setResume(sample.resume_text); setJd(sample.job_description); setNotice('Loaded a fictional example. Replace it with your own information.'); }
  async function analyzeNow() {
    await task('Analyzing sources', async () => {
      const body = AnalyzeSchema.parse({ ...source(), decisions, requirements_reviewed: reviewed });
      const result = await jsonApi('analyze', AnalysisSchema, body);
      setAnalysis(result); setStep(1); setReviewDirty(false);
      setTestBlock(result.blocks.find(x => x.kind === 'bullet')?.id ?? '');
    });
  }
  async function tighten() {
    if (!analysis) return;
    await task('Checking improvements', async () => {
      const body = RewriteSchema.parse({ ...source(), source_hash: analysis.source_hash, use_llm: llmConsent, llm_consent: llmConsent });
      const result = await jsonApi('rewrite', RewriteResultSchema, body);
      setRewrites(result.items); setNotice(result.notice);
    });
  }
  function applyRewrite(item: GuardResult) {
    if (item.status !== 'accepted') return;
    setOverrides(current => ({ ...current, [item.block_id]: item.output })); setPdfReport(null);
  }
  async function testGuard() {
    if (!analysis || !testBlock) return;
    await task('Checking proposed wording', async () => {
      const body = GuardSchema.parse({ ...source(), source_hash: analysis.source_hash, block_id: testBlock, candidate });
      setGuardResult(await jsonApi('guard', GuardResultSchema, body));
    });
  }
  function decide(id: string, exclude: boolean, reason = 'Reviewed manually; excluded from this skill-only assessment.') {
    setDecisions(current => [...current.filter(d => d.id !== id), ...(exclude ? [{ id, decision: 'exclude' as const, reason }] : [])]);
    setReviewDirty(true);
  }
  async function exportPdf() {
    if (!analysis) return;
    await task('Rendering and verifying PDF', async () => {
      const body = ExportSchema.parse({ ...source(), source_hash: analysis.source_hash, overrides, template });
      const response = await api('export/pdf', body);
      if (response.headers.get('x-text-verified') !== 'true') throw new Error('Export was not verified. Download blocked.');
      const blob = await response.blob();
      setPdfReport({ pages: response.headers.get('x-pdf-pages') ?? '?', hash: response.headers.get('x-content-sha256') ?? '', engine: response.headers.get('x-pdf-engine') ?? '' });
      download(blob, 'resume.pdf');
    });
  }
  const workspace = (): Workspace => WorkspaceSchema.parse({ schema_version: '1.0.0', ...{ resume_text: resume, job_description: jd }, template, decisions, requirements_reviewed: reviewed, overrides, source_hash: analysis?.source_hash ?? '' });
  function saveLocal() { download(new Blob([JSON.stringify(workspace(), null, 2)], { type: 'application/json' }), 'resume-workspace.json'); setNotice('Workspace downloaded. It contains personal information; keep it private.'); }
  function restore(value: unknown) {
    const data = WorkspaceSchema.parse(value); invalidate(); setResume(data.resume_text); setJd(data.job_description); setTemplate(data.template);
    setDecisions(data.decisions); setReviewed(data.requirements_reviewed); setStep(0);
    setNotice('Sources restored. Re-run analysis and improvements; saved edits are not trusted without fresh checks.');
  }
  async function loadFile(file?: File) {
    if (!file) return;
    await task('Opening workspace', async () => { if (file.size > 250000) throw new Error('Workspace is too large.'); restore(JSON.parse(await file.text())); });
  }
  async function importPdf(file?: File) {
    if (!file) return;
    await task('Reading PDF', async () => {
      const result = z.object({ text: z.string(), warning: z.string() }).parse(await upload('import/pdf', file));
      invalidate(); setResume(result.text); setNotice(result.warning);
    });
  }
  async function inspectNotebook(file?: File) {
    if (!file) return;
    await task('Inspecting notebook without execution', async () => { setInspection(InspectionSchema.parse(await upload('evidence/notebook', file))); });
  }
  async function inspectRepo() {
    await task('Inspecting public repository', async () => {
      const body = RepoSchema.parse({ url: repo, adult_confirmed: true, network_consent: true });
      setInspection(await jsonApi('evidence/github', InspectionSchema, body));
    });
  }
  async function openHistory() { setShowHistory(true); await task('Loading saved history', async () => { setHistory((await jsonApi('history', HistorySchema)).items); }); }
  async function saveHistory() {
    await task('Saving encrypted snapshot', async () => {
      const body = SaveDraftSchema.parse({ title: historyTitle, storage_consent: storageConsent, workspace: workspace() });
      await api('history', body); setHistory((await jsonApi('history', HistorySchema)).items); setNotice('Encrypted snapshot saved with a 30-day access window.');
    });
  }
  function clear() {
    if (!window.confirm('Clear the editor? Download a workspace first to keep your work. Saved server snapshots are not deleted by this action.')) return;
    invalidate(); setResume(''); setJd(''); setInspection(null); setCandidate(''); setStep(0); setNotice('Editor cleared.');
  }
  const bullets = analysis?.blocks.filter(x => x.kind === 'bullet') ?? [];
  const ordered = analysis ? [...analysis.blocks].sort((a, b) => {
    if (template === 'professional') return a.source_start - b.source_start;
    const priorities: Record<string, number> = { contact: 0, summary: 1, education: 2, projects: 3, experience: 4, skills: 5, certifications: 6, other: 7 };
    return (priorities[a.section] ?? 7) - (priorities[b.section] ?? 7) || a.group - b.group || a.source_start - b.source_start;
  }) : [];

  return <div className="app">
    <header className="topbar">
      <a href="/" className="brand" aria-label="Proof of Work home"><span className="brand-mark"><Layers3 size={21} /></span><span>proof<span className="brand-light">of</span>work<span className="brand-caption">RESUME STUDIO</span></span></a>
      <div className="topbar-right"><span className="status"><i className={config ? 'online' : ''} />{config ? 'Connected to your API' : 'Connecting to API'}</span>
        <Link href="/privacy" target="_blank" className="text-link">Privacy</Link>
        {authEnabled && (signedIn ? <button className="button small secondary" onClick={() => void signOut()}>Sign out</button> : <button className="button small secondary" onClick={() => void signIn('github')}>Sign in</button>)}
      </div>
    </header>
    {!gate ? <main className="welcome">
      <div className="welcome-copy"><SmallLabel>YOUR NEXT CHAPTER, ON YOUR TERMS</SmallLabel><h1>Your experience.<br /><em>Nothing invented.</em></h1><p>Know where you fit. Make every line count. Build a resume that stays true to your work.</p><div className="welcome-checks"><span><Check size={17} />Source-linked coverage</span><span><Check size={17} />No account required</span><span><Check size={17} />No paid AI needed</span></div></div>
      <section className="gate card" aria-labelledby="gate-title"><span className="icon-tile"><LockKeyhole size={24} /></span><h2 id="gate-title">Before we begin</h2><p>Your resume is personal. Here is how this studio handles it.</p>
        <label className="check-line"><input type="checkbox" checked={adult} onChange={e => setAdult(e.target.checked)} /><span>I confirm that I am 18 or older.</span></label>
        <label className="check-line"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} /><span>I agree to send my inputs to this company's processing server for the actions I request. Anonymous resumes are not intentionally saved to a database.</span></label>
        <p className="micro">No model receives your text unless you separately opt in. Download a workspace to keep your work before leaving.</p>
        <button className="button primary full" disabled={!adult || !consent} onClick={() => setGate(true)}>Open studio <ArrowRight size={17} /></button>
        <Link href="/privacy" target="_blank" className="micro underlined">Read the processing and privacy notes</Link>
      </section>
    </main> : <>
      <div className="workspace-heading"><div><SmallLabel>YOUR CAREER. YOUR SOURCE OF TRUTH.</SmallLabel><h1>Resume studio<span className="version-label">01</span></h1><p>Real experience, clearly presented. No invented achievements.</p></div>
        <div className="workspace-tools"><button className="button secondary small" onClick={() => workspaceInput.current?.click()} disabled={!!busy}><Upload size={15} />Open workspace</button><button className="button secondary small" onClick={saveLocal} disabled={!!busy || !resume}><Save size={15} />Save locally</button><button className="icon-button" title="Clear editor" aria-label="Clear editor" onClick={clear} disabled={!!busy}><Trash2 size={17} /></button></div>
      </div>
      <input hidden type="file" accept=".json,application/json" ref={workspaceInput} onChange={e => { void loadFile(e.target.files?.[0]); e.target.value = ''; }} />
      <input hidden type="file" accept=".pdf,application/pdf" ref={fileInput} onChange={e => { void importPdf(e.target.files?.[0]); e.target.value = ''; }} />
      <input hidden type="file" accept=".ipynb,application/json" ref={notebookInput} onChange={e => { void inspectNotebook(e.target.files?.[0]); e.target.value = ''; }} />
      {error && <div className="notification error" role="alert"><AlertTriangle size={17} /><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}><X size={16} /></button></div>}
      {notice && <div className="notification info" role="status"><CircleHelp size={17} /><span>{notice}</span><button aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={16} /></button></div>}
      {busy && <div className="busy-bar" role="status"><LoaderCircle className="spin" size={16} />{busy}...</div>}
      <fieldset className="workspace-layout" disabled={!!busy}>
        <aside className="sidebar">
          <nav aria-label="Studio steps">{STEPS.map((item, i) => <button key={item.title} className={`step-button ${step === i ? 'active' : ''}`} disabled={i > 0 && !analysis} onClick={() => setStep(i)}><span className="step-number">{i < step ? <Check size={16} /> : `0${i + 1}`}</span><span><strong>{item.title}</strong><small>{item.subtitle}</small></span>{step === i && <ChevronRight size={15} />}</button>)}</nav>
          <div className="sidebar-note"><ShieldCheck size={24} /><strong>Truth is the feature.</strong><p>The tool preserves your input. It does not verify employment or claim your achievements are true.</p><span className="pill muted">USER-PROVIDED CLAIMS</span></div>
          <div className="sidebar-bottom"><button className="text-button" onClick={() => setShowEvidence(!showEvidence)}><Code2 size={16} />Inspect an artefact</button>{config?.history_enabled && signedIn && <button className="text-button" onClick={() => void openHistory()}><History size={16} />Saved history</button>}<small>{signedIn ? `Signed in as ${userName || 'learner'}` : 'Guest workspace'}<br />Nothing is auto-saved.</small></div>
        </aside>
        <main className="content">
          {step === 0 && <>
            <div className="section-heading"><div><span className="step-kicker">STEP 01 / SOURCE MATERIAL</span><h2>Start with what is real.</h2><p>Paste your existing resume and the role you are considering.</p></div><button className="text-button" onClick={useSample}><Sparkles size={16} />Load fictional example</button></div>
            <div className="source-grid">
              <section className="source-card card"><div className="card-header"><div><span className="icon-tile small"><FileText size={18} /></span><h3>Your resume</h3></div><button className="text-button" onClick={() => fileInput.current?.click()}><Upload size={14} />Import PDF</button></div>
                <label className="sr-only" htmlFor="resume-input">Your resume</label><textarea id="resume-input" className="source-textarea" value={resume} maxLength={20000} onChange={e => { invalidate(); setResume(e.target.value); }} placeholder={'YOUR NAME\nCity | Email | Phone\n\nExperience\nJob title | Company\nDates exactly as you know them\n- I created monthly reports using Excel.\n\nSkills\nExcel\n\nEducation\nYour qualification and institution'} spellCheck={false} />
                <div className="card-footer"><span>Use section headings and one bullet per line.</span><span>{resume.length.toLocaleString()} / 20,000</span></div>
              </section>
              <section className="source-card card"><div className="card-header"><div><span className="icon-tile small neutral"><ScanText size={18} /></span><h3>Target job description</h3></div><span className="pill muted">PASTE TEXT</span></div>
                <label className="sr-only" htmlFor="jd-input">Target job description</label><textarea id="jd-input" className="source-textarea" value={jd} maxLength={30000} onChange={e => { invalidate(); setJd(e.target.value); }} placeholder={'Paste the job description here.\n\nInclude responsibilities, required skills and preferred qualifications.\n\nWe show recognized skill requirements and surface unclassified lines for your review. Nothing from the job description is automatically added to your resume.'} spellCheck={false} />
                <div className="card-footer"><span>Requirements are suggestions until you review them.</span><span>{jd.length.toLocaleString()} / 30,000</span></div>
              </section>
            </div>
            <div className="source-hint"><LockKeyhole size={16} /><p>Sent to your company's API when you analyze. No automatic storage. No external AI call.</p></div>
            <div className="bottom-actions"><span><span className="mini-check"><Check size={12} /></span>Zod validates here. Pydantic validates again on the server.</span><button className="button primary" onClick={() => void analyzeNow()} disabled={!resume.trim() || !jd.trim()}>Analyze skill coverage <ArrowRight size={17} /></button></div>
          </>}
          {step === 1 && analysis && <>
            <div className="section-heading"><div><span className="step-kicker">STEP 02 / EVIDENCE, NOT GUESSWORK</span><h2>See where your experience connects.</h2><p>Every match points to text you supplied. Missing means not found, not that you lack the skill.</p></div></div>
            <section className="score-card card"><div className="score-ring" style={{ '--progress': `${analysis.score ?? 0}%` } as CSSProperties}><div><strong>{analysis.score === null ? '--' : `${analysis.score}%`}</strong><span>COVERAGE</span></div></div><div className="score-copy"><span className={`pill ${analysis.complete ? 'green' : 'amber'}`}>{analysis.complete ? 'REVIEWED SKILL COVERAGE' : 'PROVISIONAL SKILL COVERAGE'}</span><h3>{analysis.matched} of {analysis.total} recognized requirements supported</h3><p>Unweighted coverage of included skill requirements. It does not measure proficiency, experience duration or hiring probability.</p><div className="score-stats"><span><i className="dot green-dot" />{analysis.matched} supported</span><span><i className="dot amber-dot" />{analysis.total - analysis.matched} not found</span><span><i className="dot gray-dot" />{analysis.unresolved} unresolved lines</span></div></div></section>
            <div className="review-toolbar"><label className="check-line"><input type="checkbox" checked={reviewed} onChange={e => { setReviewed(e.target.checked); setReviewDirty(true); }} /><span>I reviewed the JD requirements and the original text below.</span></label><button className="button secondary small" onClick={() => void analyzeNow()}><RotateCcw size={14} />{reviewDirty ? 'Recalculate changes' : 'Recalculate'}</button></div>
            {reviewDirty && <p className="inline-warning">Your review changed. Recalculate before using this score or report.</p>}
            <div className="requirements-list">{analysis.requirements.map(req => {
              const excluded = decisions.some(d => d.id === req.id && d.decision === 'exclude');
              return <article className={`requirement card ${excluded ? 'excluded' : ''}`} key={req.id}><div className="requirement-top"><span className={`match-icon ${req.status}`}>{req.status === 'matched' ? <Check size={16} /> : req.status === 'missing' ? <X size={16} /> : <CircleHelp size={16} />}</span><div><h3>{req.label}</h3><span className="micro">{req.kind === 'unresolved' ? 'Not automatically scored' : `${req.priority} / ${req.alternative ? 'either skill satisfies this item' : 'one requirement'}`}</span></div><span className={`pill ${req.status === 'matched' ? 'green' : req.status === 'missing' ? 'amber' : 'muted'}`}>{req.status === 'matched' ? 'SUPPORTED' : req.status === 'missing' ? 'NOT FOUND' : req.status.toUpperCase()}</span></div>
                <p className="jd-quote"><span>JD</span>{req.jd_text}</p>
                {req.evidence.map((ev, i) => <div className={`evidence-quote ${ev.status}`} key={`${ev.block_id}-${i}`}><span className="source-tag">YOUR SOURCE / {ev.status.toUpperCase()}</span><p>{ev.quote}</p><small>Matched: <mark>{ev.text}</mark> &middot; characters {ev.start}-{ev.end}</small></div>)}
                {req.status === 'missing' && <p className="micro">Do not add this just to improve the score. Add it to your source only when you can honestly support the claim.</p>}
                <div className="requirement-review"><label className="check-line"><input type="checkbox" checked={excluded} onChange={e => decide(req.id, e.target.checked)} /><span>Exclude from this skill-only assessment</span></label>{excluded && <input aria-label={`Reason for excluding ${req.label}`} className="input reason-input" maxLength={300} value={decisions.find(d => d.id === req.id)?.reason ?? ''} onChange={e => decide(req.id, true, e.target.value)} />}</div>
              </article>;
            })}</div>
            <details className="audit-details"><summary>Reproducibility record</summary><p>Same inputs, decisions and versions produce the same assessment.</p><pre>{JSON.stringify({ assessment_hash: analysis.assessment_hash, source_hash: analysis.source_hash, ...analysis.versions }, null, 2)}</pre></details>
            <div className="bottom-actions"><button className="text-button" disabled={reviewDirty} onClick={() => download(new Blob([JSON.stringify(analysis, null, 2)], { type: 'application/json' }), 'coverage-report.json')}><Download size={15} />Download private report</button><button className="button primary" onClick={() => setStep(2)}>Refine safely <ArrowRight size={17} /></button></div>
          </>}
          {step === 2 && analysis && <>
            <div className="section-heading"><div><span className="step-kicker">STEP 03 / THE GUARD IS THE FEATURE</span><h2>Sharper wording. Same facts.</h2><p>Only approved transformations can pass. The original stays when a proposed change fails.</p></div><button className="button primary" onClick={() => void tighten()}><Sparkles size={16} />Find safe improvements</button></div>
            <div className="callout"><ShieldCheck size={23} /><div><strong>A deliberately conservative editor.</strong><p>This release removes a leading "I" before supported past-tense verbs and normalizes spacing. Arbitrary paraphrases are rejected, even when they sound plausible.</p></div></div>
            {config?.llm_enabled && <label className="check-line model-consent"><input type="checkbox" checked={llmConsent} onChange={e => setLlmConsent(e.target.checked)} /><span>Use the administrator-configured model. I consent to sending my bullet text, which may contain personal information. The same guard still applies.</span></label>}
            {!bullets.length && <div className="empty-state card"><FileText size={30} /><h3>No bullets detected</h3><p>Return to your sources and place each bullet on its own line, starting with a hyphen. Your existing text can still be exported.</p></div>}
            {bullets.length > 0 && rewrites.length === 0 && <div className="empty-state card"><ShieldCheck size={32} /><h3>{bullets.length} source bullets ready to check</h3><p>Find safe improvements, review each change and choose which to apply.</p></div>}
            <div className="rewrite-list">{rewrites.map(item => <article className="rewrite-card card" key={item.block_id}>
              <div className="rewrite-card-top"><span className={`pill ${item.status === 'rejected' ? 'red' : item.changed ? 'green' : 'muted'}`}>{item.status === 'rejected' ? 'REJECTED / ORIGINAL KEPT' : item.changed ? 'SAFE CHANGE' : 'ORIGINAL RETAINED'}</span><small>Source {item.source_start}-{item.source_end}</small></div>
              <div className="rewrite-grid"><div><SmallLabel>ORIGINAL</SmallLabel><p>{item.original}</p></div><div><SmallLabel>{item.status === 'rejected' ? 'REJECTED PROPOSAL' : 'PROPOSED'}</SmallLabel><p>{item.candidate}</p></div></div>
              <div className="rewrite-bottom"><p>{item.reasons.join(' ')}</p>{item.changed && item.status === 'accepted' && <button className={`button small ${overrides[item.block_id] === item.output ? 'applied' : 'secondary'}`} onClick={() => applyRewrite(item)}><Check size={14} />{overrides[item.block_id] === item.output ? 'Applied' : 'Apply change'}</button>}</div>
            </article>)}</div>
            <section className="guard-lab card"><div className="guard-lab-header"><span className="icon-tile warning"><ShieldCheck size={21} /></span><div><h3>Try to break the guard.</h3><p>Paste an inflated rewrite. Watch the tool refuse to add it.</p></div><span className="pill muted">LIVE CHECK</span></div>
              <label className="field-label" htmlFor="source-block">Source bullet</label><select id="source-block" className="input" value={testBlock} onChange={e => { setTestBlock(e.target.value); setGuardResult(null); }}>{bullets.map(b => <option value={b.id} key={b.id}>{b.text.slice(0, 100)}</option>)}</select>
              <label className="field-label" htmlFor="proposed-text">Proposed rewrite</label><textarea id="proposed-text" className="input candidate-input" value={candidate} onChange={e => { setCandidate(e.target.value); setGuardResult(null); }} maxLength={3000} placeholder="Paste the wording you want the guard to check." />
              <div className="guard-actions"><button className="text-button" onClick={() => { setCandidate('Led campaigns worth \u20b92 crore and increased ROAS by 40%.'); setGuardResult(null); }}>Insert an unsupported example</button><button className="button secondary" disabled={!testBlock || !candidate} onClick={() => void testGuard()}>Check rewrite <ShieldCheck size={16} /></button></div>
              {guardResult && <div className={`guard-result ${guardResult.status}`} role="status"><strong>{guardResult.status === 'rejected' ? 'Rejected. Your original stays.' : 'Accepted by the preservation guard.'}</strong>{guardResult.reasons.map(reason => <p key={reason}>{reason}</p>)}{guardResult.status === 'accepted' && guardResult.changed && <button className="button small secondary" onClick={() => applyRewrite(guardResult)}>Apply checked change</button>}</div>}
            </section>
            <div className="bottom-actions"><span>{Object.keys(overrides).length} approved changes applied</span><button className="button primary" onClick={() => setStep(3)}>Preview and export <ArrowRight size={17} /></button></div>
          </>}
          {step === 3 && analysis && <>
            <div className="section-heading"><div><span className="step-kicker">STEP 04 / READY TO REPRESENT YOU</span><h2>A clean resume. A checked export.</h2><p>No score, watermark or verification claim is placed on your resume.</p></div></div>
            <div className="export-layout"><aside className="export-settings"><section className="card settings-card"><SmallLabel>LAYOUT</SmallLabel><h3>Choose your structure</h3>
              <button className={`template-option ${template === 'professional' ? 'selected' : ''}`} onClick={() => { setTemplate('professional'); setPdfReport(null); }}><FileText size={20} /><span><strong>Professional</strong><small>Preserves your section order</small></span>{template === 'professional' && <CheckCircle2 size={17} />}</button>
              <button className={`template-option ${template === 'fresher' ? 'selected' : ''}`} onClick={() => { setTemplate('fresher'); setPdfReport(null); }}><Layers3 size={20} /><span><strong>Fresher</strong><small>Education and projects first</small></span>{template === 'fresher' && <CheckCircle2 size={17} />}</button>
              <p className="micro">Entire sections move together. Employers, dates and source facts are not reassigned.</p>
            </section><section className="card settings-card"><SmallLabel>EXPORT CHECKS</SmallLabel><div className="export-check"><Check size={16} /><span>Every edit revalidated on server</span></div><div className="export-check"><Check size={16} /><span>Single-column, selectable text</span></div><div className="export-check"><Check size={16} /><span>PDF text checked in reading order</span></div><p className="micro">Extraction checks do not guarantee compatibility with every recruitment system.</p><button className="button primary full" onClick={() => void exportPdf()}><Download size={17} />Export checked PDF</button></section>
              {pdfReport && <div className="export-success"><CheckCheck size={24} /><strong>PDF text check passed</strong><p>{pdfReport.pages} page(s), rendered with {pdfReport.engine}.</p><small>Content SHA-256</small><code>{pdfReport.hash}</code></div>}
            </aside><div className="preview-wrap"><div className="preview-label"><span>CONTENT PREVIEW</span><span>Final pagination is checked during export</span></div><article className="resume-paper" aria-label="Resume content preview">{ordered.map(block => {
              const text = overrides[block.id] ?? block.text;
              return block.kind === 'name' ? <h2 key={block.id}>{text}</h2> : block.kind === 'heading' ? <h3 key={block.id}>{text}</h3> : <p className={block.kind === 'bullet' ? 'resume-bullet' : ''} key={block.id}>{block.kind === 'bullet' ? '- ' : ''}{text}</p>;
            })}</article></div></div>
          </>}
          {showEvidence && <section className="card evidence-panel"><div className="section-heading"><div><SmallLabel>ARTEFACT INSPECTION</SmallLabel><h3>Look at the work, not just the claim.</h3></div><button className="icon-button" aria-label="Close artefact inspector" onClick={() => setShowEvidence(false)}><X size={18} /></button></div><p>Inspections report observable file contents. They do not prove authorship, proficiency or business outcomes, and never add claims to your resume automatically.</p><button className="button secondary" onClick={() => notebookInput.current?.click()}><Upload size={16} />Inspect a notebook (.ipynb)</button>
            {config?.github_enabled && <div className="repo-form"><label htmlFor="repo-url" className="field-label">Public GitHub repository</label><input id="repo-url" className="input" value={repo} onChange={e => setRepo(e.target.value)} placeholder="https://github.com/owner/repository" /><p className="micro">By inspecting, you agree to send this public repository identifier to GitHub.</p><button className="button secondary" disabled={!repo} onClick={() => void inspectRepo()}>Inspect repository <ExternalLink size={15} /></button></div>}
            {inspection && <div className="inspection-result"><span className="pill green">OBSERVED CONTENTS ONLY</span>{inspection.facts.map(f => <p key={f}><Check size={14} />{f}</p>)}{inspection.limitations.map(l => <small key={l}>{l}</small>)}{inspection.sha256 && <code>SHA-256: {inspection.sha256}</code>}</div>}
          </section>}
        </main>
      </fieldset>
      <footer className="footer"><span>Proof of Work &middot; Source-preserving by design</span><span>{config?.skill_count ?? '--'} starter skills &middot; {config?.taxonomy_version ?? 'Loading taxonomy'}</span><Link href="/privacy" target="_blank">Privacy and limitations</Link></footer>
    </>}
    {showHistory && <div className="modal-overlay"><section role="dialog" aria-modal="true" aria-labelledby="history-heading" className="history-modal card"><div className="section-heading"><div><SmallLabel>OPTIONAL / ENCRYPTED / 30 DAYS</SmallLabel><h2 id="history-heading">Saved history</h2></div><button className="icon-button" aria-label="Close history" onClick={() => setShowHistory(false)}><X size={19} /></button></div>
      <label className="field-label" htmlFor="snapshot-title">Snapshot name</label><input className="input" id="snapshot-title" value={historyTitle} onChange={e => setHistoryTitle(e.target.value)} maxLength={100} />
      <label className="check-line"><input type="checkbox" checked={storageConsent} onChange={e => setStorageConsent(e.target.checked)} /><span>I agree to store this workspace on the company's server with a 30-day access window. Expired records are cleaned up while the service is running.</span></label><button className="button primary" disabled={!storageConsent || !resume || !!busy} onClick={() => void saveHistory()}><Save size={15} />Save snapshot</button>
      <div className="history-list">{history.length === 0 && <p>No saved snapshots.</p>}{history.map(item => <div key={item.id} className="history-item"><div><strong>{item.title}</strong><small>Expires {new Date(item.expires_at).toLocaleDateString()}</small></div><button className="button small secondary" disabled={!!busy} onClick={() => void task('Opening snapshot', async () => { const data = await (await api(`history/${item.id}`)).json(); restore(data.workspace); setShowHistory(false); })}>Open</button><button className="icon-button danger" title="Delete snapshot" aria-label={`Delete ${item.title}`} disabled={!!busy} onClick={() => void task('Deleting snapshot', async () => { await api(`history/${item.id}`, undefined, 'DELETE'); setHistory(current => current.filter(x => x.id !== item.id)); })}><Trash2 size={16} /></button></div>)}</div>
      {history.length > 0 && <button className="text-button danger" disabled={!!busy} onClick={() => { if (window.confirm('Delete all your saved snapshots? This cannot be undone.')) void task('Deleting history', async () => { await api('history', undefined, 'DELETE'); setHistory([]); }); }}>Delete all saved snapshots</button>}
    </section></div>}
  </div>;
}
