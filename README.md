# Proof-of-Work Resume Studio

A company-hosted resume application with a **Next.js frontend, Zod validation, FastAPI backend, Pydantic validation, deterministic skill coverage, a conservative preservation guard, and checked PDF export**.

**Start with `docs/BUILD_STATUS.md`.** This is a working backend plus a complete frontend source implementation, not an already-deployed or security-certified production service. The build environment could not download npm packages or Typst. Backend tests were executed with the explicit ReportLab renderer; frontend production build, live OAuth, PostgreSQL runtime and Typst need verification on your machine/CI.

## Start here: Docker

Install Docker with Compose and Python 3 for the setup script. Initial builds need an internet connection to download dependencies.

```bash
python3 scripts/setup.py
docker compose up --build
```

Open **http://localhost:3000**. Use that hostname: the request-origin check is configured for `localhost`, not a different IP/hostname. The API is reachable by the frontend on the private Compose network, not exposed publicly.

The default uses **Typst**, as requested. A second, fully implemented renderer is available: set `PDF_ENGINE=reportlab` in `.env` and restart the API. Both renderers use the same source guard and `pdfplumber` text verification. There is **no silent fallback** between them.

No cloud-model key, login, database service or paid API is needed for the core flow. Guest requests are processed on your server; this is **not** a browser-only privacy architecture.

### Try the complete flow

1. Confirm age eligibility and processing consent, then open the studio.
2. Click **Load fictional example**, then **Analyze skill coverage**. The supplied fixture produces **5/8 = 62.5%** known-skill coverage and two unresolved JD lines.
3. Review the original JD text. Exclude non-skill/context lines only with a recorded reason, check the review box, and recalculate.
4. Open **Refine safely**, generate safe changes and apply one. In the guard panel, insert the unsupported example and check it: the invented amount/ownership is rejected.
5. Choose a template and export. The server rechecks every override, renders a PDF, extracts its text and compares it with the approved content before responding.

The example is fictional. Never submit it as your own resume.

## What is implemented

| Feature | Implementation |
|---|---|
| Input | Text paste; bounded PDF import with explicit review; workspace JSON import/export |
| Validation | Zod in browser and Next.js proxy; strict Pydantic on API; shared acceptance fixtures |
| Coverage | Versioned original starter dictionary; exact aliases; explicit `or` groups; source spans; learning/negation handling; unresolved lines; exclusion reasons; deterministic assessment hash |
| Rewriting | Free deterministic rules; optional consent-based model proposal adapter; every output goes through the same closed-world guard |
| Guard | Only enumerated transformations of one exact source block are accepted; stale/unknown/cross-block edits are rejected |
| PDF | Professional/source-order and fresher/education-first layouts; Typst or explicit ReportLab engine; font coverage and text-order verification; no watermark or score on resume |
| Evidence | Notebook AST inspection without execution; optional bounded public GitHub metadata/language inspection; no automatic achievement claims |
| History | Optional GitHub sign-in with Auth.js; short-lived internal JWTs; encrypted SQLAlchemy snapshots; owner isolation; expiry and deletion |
| Deployment | Docker, optional PostgreSQL profile, Alembic migration, test suites, CI configuration, privacy notes |

## Local development

Use Node.js 22 and Python 3.12 or newer. Install Noto Sans on the API machine. Docker includes it. Font files are deliberately not bundled in the repository.

```bash
python3 scripts/setup.py
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements-dev.txt
cd apps/api
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file ../../.env --no-access-log
```

In another terminal:

```bash
cd apps/web
npm install
npm run dev
```

On Windows, activate the virtual environment with `.venv\Scripts\Activate.ps1` instead. Docker is recommended for Linux worker resource limits and fonts.

After the first successful npm installation, **commit `apps/web/package-lock.json`** and use `npm ci` in builds. No dependency lockfile was fabricated in the offline build environment. The Python direct dependencies are pinned where tested; resolve and lock the full dependency graph for your release.

Development API docs are available at `http://127.0.0.1:8000/docs`. Requests under `/v1` need the `X-Internal-Key` from your local `.env`; the browser never receives that secret. The frontend supplies it on the server. Documentation is disabled in production.

## Test commands

```bash
# API, including scoring, guard, PDF round trips and encrypted-history isolation
cd apps/api
python -m pytest -q

# Frontend contracts, types and production build
cd ../web
npm run typecheck
npm test
npm run build

# Browser workflow; keep the API running first
npx playwright install chromium
npm run test:e2e
```

The browser test covers the age gate, fictional example, source-linked score, rejected fabricated rewrite and PDF download. It is provided but was not executed in the original offline build environment. `docs/backend-test-results.xml` records the executed Python test run.

## Enable optional saved history

Guest mode works without this. History requires authentication **and** explicit user storage consent.

1. Register your own GitHub OAuth application. Set its callback to `http://localhost:3000/api/auth/callback/github` for local development, or the corresponding HTTPS company URL for deployment.
2. Set `AUTH_GITHUB_ID` and `AUTH_GITHUB_SECRET` in `.env`; mirror those two settings in `apps/web/.env.local` for non-Docker development. Keep the independently generated `AUTH_SECRET`, `API_TOKEN_SECRET` and `INTERNAL_API_KEY` private.
3. Set `ENABLE_HISTORY=true`. For Compose PostgreSQL, set:

```dotenv
DATABASE_URL=postgresql+psycopg://studio:YOUR_POSTGRES_PASSWORD@db:5432/studio
```

Use the value already generated as `POSTGRES_PASSWORD`. Keep `HISTORY_ENCRYPTION_KEY` backed up securely. Changing it without a migration makes existing snapshots unreadable.

4. Start the database and wait for health **before** starting the API with history enabled:

```bash
docker compose --profile history up -d --wait db
docker compose --profile history up --build web api
```

The API entrypoint runs Alembic for PostgreSQL. SQLite is available for local history development; a Docker SQLite path must point to the writable volume, e.g. `sqlite:////data/studio.db`, not the read-only application directory.

Snapshots expire after 30 days. Reads prune expired rows and an in-process task checks every five minutes while the API is operating. Encrypted snapshots, database backups, service logs and OAuth-provider metadata have different lifecycles: configure an honest company retention policy for all of them.

Auth.js is an optional v5 beta integration. Its live provider flow and the selected package version must pass your dependency/security review before public enablement.

## Enable optional model proposals

No model is used by default. The deterministic editor is functional on its own.

```dotenv
LLM_BASE_URL=https://YOUR_APPROVED_PROVIDER/v1
LLM_API_KEY=YOUR_KEY_IF_REQUIRED
LLM_MODEL=YOUR_MODEL
```

Use an operator-approved OpenAI-compatible endpoint. A locally hosted compatible model may also be used. Provider setup, model download, hardware, licensing and provider data policy are the operator's responsibility. The browser requires a separate opt-in and sends only bullet text through the API; bullets can still contain personal information. Model output must match a permitted transformation or it is rejected. If the model fails, the application explicitly reports that rules were used instead.

Do not put API keys in `NEXT_PUBLIC_*` environment variables.

## Enable optional GitHub inspection

Set `ENABLE_GITHUB_INSPECTOR=true`. The UI then offers public repository inspection with a separate network disclosure. Only standard `https://github.com/owner/repository` URLs are accepted. Requests go to a fixed GitHub API origin, redirects are disabled, and response/time limits apply. No repository is cloned or executed.

Notebook inspection works without GitHub. It reads a version-4 notebook as data, looks for import statements through Python's AST, and reports narrowly scoped observations. Neither inspector proves authorship or proficiency.

**Your actual Be10X Project Gallery is not connected.** A real Gallery endpoint, identity/ownership rules and a reviewer process were not supplied. The app does not invent verified badges or silently treat its fictional example as Gallery evidence.

## Important limitations

- The guard preserves input; it cannot prove that a user-provided claim is true.
- The line parser recognizes a limited set of English section headings. Review the parsed source and preview. It is not a general semantic resume parser.
- The taxonomy is an original starter dictionary with internal IDs, **not an imported ESCO/O*NET corpus**. The score only covers included recognized skills. Read every JD line and non-skill constraint.
- Many valid paraphrases are intentionally rejected. This is safer than describing an entity diff as a proof of semantic equivalence.
- PDF extraction checks do not guarantee compatibility with every ATS. The font check blocks unsupported characters; advanced multilingual shaping/RTL templates need separate testing.
- PDF import does not OCR scanned documents or reconstruct complex tables/columns. Uploads are limited to 1.5 MB and PDFs to 12 pages.
- Unrestricted cover letters, DOCX export, hosted portfolios, subscriptions, a company admin console, and parent-consent support are not included.
- The public pilot is 18+ only. A checkbox is not identity verification or a completed legal compliance program.
- No account, hosting service, domain, external provider or live company system has been created or deployed for you.

## Before public launch

Follow `docs/SECURITY.md` and `docs/DEPLOYMENT.md`. Verify the frontend production build, Typst export, real OAuth, PostgreSQL migrations and the browser test in your deployment environment. Audit dependencies and freeze lockfiles. Replace the privacy page's operator-configuration section with your reviewed company notice and contact details. Pilot with synthetic data before real resumes.

## Project map

```text
apps/web/                Next.js UI, Zod contracts, server proxy, Auth.js
apps/api/app/            FastAPI, Pydantic, matcher, guard, renderers, workers, history
apps/api/alembic/        PostgreSQL-compatible schema migration
apps/api/tests/          Executed backend regression tests
apps/web/tests/          Zod fixtures and Playwright workflow
fixtures/               Fictional sample inputs and an example PDF
scripts/                Secret setup and OpenAPI export
docs/                   Architecture, deployment, security, test status and API spec
.github/workflows/      CI gates
```

Technical reference links used during implementation are in `docs/REFERENCES.md`.
