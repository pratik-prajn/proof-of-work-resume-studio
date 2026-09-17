# Architecture and invariants

## Core path

```text
Browser / Next.js UI
  | Zod validates user-entered input
  v
Next.js server route /api/backend/*
  | allowlisted route + method; origin check; 2 MB body limit
  | Zod validates JSON again; secrets remain server-side
  v
FastAPI /v1/*
  | internal key; Pydantic strict models; explicit boolean consent
  v
Lossless source-line parser --> versioned deterministic coverage
  | original character spans, stable block IDs
  v
Deterministic or optional model proposals
  | closed-world guard checks exact source-local variants
  v
Approved text blocks --> isolated PDF worker --> Typst / ReportLab
  | font coverage + pdfplumber ordered text comparison
  v
Verified PDF bytes returned to browser, then downloaded
```

The proxy never accepts a client-supplied upstream URL or authorization header. Its internal API key and user-token signing secret are separate. The API is private in Compose. Direct exposure is not the intended deployment.

## Both validators have real jobs

`apps/web/lib/schemas.ts` validates browser actions and the server proxy boundary. `apps/api/app/models.py` is the authoritative backend contract. Unknown properties are rejected. Pydantic uses strict types and a special pre-validator for consent because Python's `True == 1` must not permit numeric consent.

Shared fixture files test the same accepted/rejected source inputs in both languages. Zod checks are not a replacement for Pydantic. Neither validator independently establishes the truth of a resume claim.

## Source preservation

The raw input is retained in the current request, not silently replaced with a generated summary. Each non-empty line becomes a source block with exact Python Unicode-code-point offsets. Original markers are recorded; the PDF consistently renders bullet blocks with `- `.

Rewrites are accepted only if identical to the original or an explicitly allowed transformation of that same block. Current rules collapse whitespace and remove a leading `I ` before a reviewed list of past-tense action verbs. No role reassignment, semantic synonym substitution, metric invention, hidden rounding or outcome conversion is allowed.

The parser is heuristic about presentation labels, not about claim truth. Section IDs are used only to move complete groups in the fresher layout. Facts are never harvested from one employer's bullet to enhance another's.

An export request contains the raw source and proposed overrides. The API reconstructs the source blocks and reruns the guard rather than trusting earlier browser approval. Its SHA-256 source hash prevents accidental stale edits, not deliberate false source input.

## Coverage

- Score = 100 * supported included known skill requirements / included known skill requirements.
- No denominator gives `null`, not 100%.
- One exact alias match supports a skill mention. A skills-list mention is visibly labelled `listed`; work/project mentions are `mentioned`, not verified demonstrations.
- Learning/negated phrases are surfaced but excluded from matches using conservative rules. These rules are not a complete language understanding system.
- Simple explicit `X or Y` is one alternative requirement. Repeated identical requirement groups count once.
- Unknown lines, years/degrees/other recognized non-skill constraints, and ambiguous OR expressions remain visible for review.
- Excluding an item requires a reason. A reviewed/complete indicator requires explicit review and no unresolved included lines.
- Users must read every JD line, including qualifications inside lines that contain recognized skills. The starter extractor does not claim full JD comprehension.
- The hash includes source input, reviewed decisions and ordering-independent decision IDs, algorithm/parser versions and the full taxonomy hash. Time of execution is not included.

## Export invariants

Only immutable template code is executed. User strings enter Typst through JSON data and `text()`, not through concatenated source or `eval()`. ReportLab escapes user strings before its paragraph parser.

The chosen font must cover every non-whitespace input character. Both engines use a minimum 10.5-point body size and a single column. The PDF's extracted text must equal approved text after NFC/whitespace normalization only. Meaningful punctuation and symbols are not stripped; word order is not sorted. Out-of-page characters and documents outside the supported page count are blocked.

This confirms fidelity against one extraction implementation; it does not certify all recruitment software or prove real-world statements.

## Optional history and authentication

Auth.js authenticates through a company-owned GitHub OAuth app. The Next.js server signs a 60-second JWT with a stable provider subject. FastAPI verifies signature, expiry, audience and issuer. Every query is restricted by owner. There is no client-controlled owner parameter.

History requires a separate explicit storage-consent flag. Title and workspace are encrypted together with Fernet before SQL storage. Owner identifier, creation time and expiry metadata remain readable to the database operator. PostgreSQL is the deployment option; SQLite is the local-test option. Expired rows are removed on reads and by a five-minute task while the API is operating.

## Outbound data

Default core processing makes no outbound model request. The frontend requests only its own Next.js server. Optional model calls require explicit user opt-in. Optional GitHub inspection uses a fixed API origin and explicit network consent. Dependency installation, OAuth and hosting infrastructure have their own data flows.

## Scope choices

No Redis/Celery, general-purpose document parser, fuzzy scorer, Git clone, or production notebook execution was added just to fill a stack list. The API uses bounded subprocess workers and an in-process concurrency gate. The original starter taxonomy is intentionally labelled as such. The actual company Project Gallery requires a real integration and assessed ownership model before an evidence badge can be issued.
