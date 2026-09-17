# Deployment guide

## Local verification first

Run `python3 scripts/setup.py`, install dependencies, run API tests, install frontend dependencies, then run `npm run typecheck`, `npm test`, `npm run build` and `npm run test:e2e` with the API running. Commit the generated npm lockfile and lock the complete Python environment. Run dependency audits before exposing the app.

The authoring environment could execute the Python stack, but had no usable npm/Typst downloads and no Docker daemon. Treat the supplied CI workflow as a verification gate, not as an already-passed badge.

## Single-host Compose deployment

The default Compose configuration starts only the Next.js web application and FastAPI service. The PostgreSQL service is behind the `history` profile. Core processing does not need a database.

Generate secrets before Compose starts. The web port binds to host loopback (`127.0.0.1:3000`). Put a company-managed HTTPS reverse proxy in front of it. Do not publish the API's port to the internet. Both services run as non-root; API application files are read-only; temporary processing uses a bounded `/tmp` mount.

Set the external origin consistently:

```dotenv
APP_ORIGIN=https://resume.YOUR-COMPANY.example
AUTH_URL=https://resume.YOUR-COMPANY.example
```

The company domain above is a placeholder, not a deployed service. Configure DNS/TLS through infrastructure you control. Reject unexpected Host headers and apply trusted-proxy forwarding rules, body limits, timeouts and per-client rate limits. No proxy or domain has been provisioned by this repository.

Restart containers after configuration changes:

```bash
docker compose up -d --build
```

After startup, check the API container's health status and complete the fictional browser workflow through the external hostname. Verify that origin checks reject requests from another site and that browser network requests never reveal internal keys.

## Renderer

`PDF_ENGINE=typst` is the default. `typst-py` runs the bundled fixed `.typ` template and returns PDF bytes. The template does not use external packages or user-generated markup. Noto Sans is installed by the API Dockerfile.

`PDF_ENGINE=reportlab` is an explicit alternative. It uses the same source preparation, font coverage check and `pdfplumber` verifier. This was the engine exercised in the authoring environment. The UI/export response reports the actual engine. There is no silent fallback.

Template layout deliberately favors readable text over page compression. Long resumes may span multiple pages; the supported export range is 1-12 pages. No automatic shrinking below the body-size floor is applied.

## Optional PostgreSQL history

Read the README's history section. The important ordering is:

```bash
docker compose --profile history up -d --wait db
docker compose --profile history up -d --build api web
```

Set `ENABLE_HISTORY=true` and `DATABASE_URL` to the private `db` hostname with the generated database password. Migrations run at API startup. Set real GitHub OAuth credentials for the Next.js service; use a separate OAuth app/callback for each environment. Do not add the database encryption key to the web service.

Back up the history encryption key separately from the database. Test restore and key rotation. Retention cleanup deletes live-table records after expiry; database storage, WAL, snapshots and backups require their own operator-managed retention. A deleted record is not a claim that every historic backup has already been erased.

## Cost model

The default flow makes zero model API calls. There is no subscription/paywall in this implementation. Scoring, gap reporting, restricted rewriting and rendering run on your infrastructure.

Your team still supplies development time, CPU/RAM, bandwidth, domain/TLS operations, monitoring, maintenance and any enabled database backups. A public Next.js + Python service is not guaranteed to cost zero. No free-tier provider is assumed or provisioned.

## Operational limits

The API uses one server worker, a two-worker processing gate, a global in-process request limiter, 2 MB HTTP-body limits, 1.5 MB upload limits, worker CPU/address-space limits on Linux, and a 25-second worker wall timeout. The Next.js proxy applies its own body limit and 35-second upstream timeout.

These are starter limits, not load-test results or a multi-tenant service-level commitment. Benchmark throughput, queueing, memory and error handling with your expected concurrent users. Stronger upload isolation and distributed rate limiting may be appropriate before a broad public release.
