# Build and verification status

Build prepared: 16 September 2026.

## Delivered

A Next.js / TypeScript frontend with Zod contracts, a FastAPI / Python backend with strict Pydantic contracts, a deterministic skill matcher, a closed-world rewrite guard, checked PDF generation, optional artefact inspection, and optional authenticated encrypted workspace history. Dockerfiles, an optional PostgreSQL service, Alembic migration, setup script, tests, CI configuration and operational notes are included.

This is source code for a company-hosted application, not an already-deployed service. Resume content is processed by the server. The core needs no cloud-model API key or paid inference service. Hosting and maintenance are separate operating responsibilities.

## Executed checks

| Check | Actual result |
|---|---|
| Python backend suite | **92 passed, 2 skipped**, in 4.54 seconds. See `backend-test-results.xml`. |
| Skipped tests | Both require the unavailable Typst package. They were not treated as passes. |
| End-to-end backend example | Fictional resume and JD yielded 5/8 = 62.5% recognized-skill coverage, with unresolved JD requirements separately visible. |
| PDF generation | Explicit ReportLab renderer produced a real PDF; pdfplumber verified approved text and reading order. |
| PDF visual inspection | Fictional one-page example was rendered to an image and inspected for layout and readability. |
| Guard tests | Unsupported metrics, changed responsibility, cross-block facts, stale sources and unapproved edits rejected. |
| Input and privacy controls | Strict consent, request limits, sanitized validation errors, source validation and evidence input limits covered by tests. |
| Saved-history backend | Tested using temporary SQLite: encryption, owner isolation, token rejection, retention and deletion. No live OAuth provider was involved. |
| Alembic migration | Upgrade, downgrade and re-upgrade executed successfully against temporary SQLite. |
| TypeScript syntax | 14 TypeScript/TSX modules transpiled with zero syntax diagnostics. **This is not dependency-aware type checking or a frontend build.** |
| Setup script | Executed in a temporary copy: configuration generation, independent secrets and overwrite protection passed. |
| Source checks | JSON parsing, Python compilation and shell syntax checks passed. |

## Not executed in this environment

The environment could not download npm dependencies or the Typst package. No Docker daemon was available. Consequently, the following are supplied but **not verified here**:

- `npm install`, TypeScript dependency-aware type checking, Zod/Vitest execution and the Next.js production build.
- Playwright browser tests and responsive browser rendering.
- Actual Typst compilation and its two renderer tests.
- Docker image builds and Compose startup.
- PostgreSQL service, live PostgreSQL migration and multi-instance deployment.
- Live GitHub OAuth sign-in, public GitHub API calls and external model calls.
- External security/dependency audit, performance testing and legal/privacy sign-off.

No package lockfile has been fabricated. Generate and commit it after a successful dependency installation. Auth.js is pinned to `5.0.0-beta.32`; its optional live authentication integration still requires verification.

## Important scope boundaries

- This guard deliberately accepts only enumerated safe transformations. It is not a general semantic equivalence prover and cannot verify the truth of user-entered claims.
- The supplied taxonomy contains original starter entries with internal IDs, not a full ESCO/O*NET import. Scores do not measure hiring probability or proficiency.
- A PDF extraction check is not a universal ATS compatibility certification.
- No company Project Gallery endpoint or identity contract was supplied. There is no fabricated Gallery integration or verified-candidate badge.
- DOCX, cover letters, LinkedIn About generation, hosted portfolios, billing, a company administration console and parental-consent workflows are not included in this release.
- No real resume, credential, account secret, font file, dependency installation or user database is included in the archive. The example resume is fictional; the PDF contains embedded fonts as part of the document.

## First-run acceptance sequence

1. Run `python3 scripts/setup.py` and follow the Docker instructions in the README.
2. Install dependencies, generate a lockfile, run frontend type checks/tests/build and audit resolved dependencies.
3. Run the complete Python suite with Typst installed. Both previously skipped tests must pass before selecting that engine for users.
4. Exercise the supplied browser workflow and test both templates in your supported browsers.
5. Verify optional live OAuth and PostgreSQL separately before enabling history.
6. Replace the privacy notice's operator-configuration section and complete deployment/security review before using real learner data.

For the PDF path verified here, explicitly set `PDF_ENGINE=reportlab` in `.env`. The default remains Typst as requested. Neither renderer silently falls back to the other.
