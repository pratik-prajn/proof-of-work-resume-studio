# Security and privacy release checklist

This repository includes defensive controls, not a security audit or compliance certification.

## Must resolve before public access

1. Run the build/test/audit pipeline with network access and commit dependency lockfiles. Review Auth.js's beta integration and provider scopes. Patch dependencies before handling real resumes.
2. Keep FastAPI private. Expose only Next.js through a trusted TLS reverse proxy. Set `APP_ORIGIN` and `AUTH_URL` to the exact HTTPS public origin. Reject unexpected Host headers at ingress; configure trusted forwarding headers. HSTS belongs at the HTTPS ingress.
3. Generate independent secrets through `scripts/setup.py`. Use a secret manager for deployment. Do not commit `.env`, `.env.local` or encryption keys. Do not run setup with `--force` after storing real history without an encryption-key migration.
4. Set per-client rate limits, concurrent-request limits and upload limits at ingress. The API's 240 requests/minute limiter is global, in-process, and deliberately not presented as a distributed abuse-prevention system. Keep one worker in this starter deployment. Use distributed controls before scaling replicas.
5. Verify Linux child-process limits, container memory/CPU caps, fonts, upload rejection and export timeouts under adversarial files. Workers are resource-limited processes, not a complete hardened malware sandbox. Consider stronger process isolation for broad public uploads.
6. No session replay, form-content analytics, request-body logging or third-party tracking is included. Ensure that your reverse proxy, error monitoring, cloud platform and support tooling do not start collecting resume content or authorization headers.
7. Confirm encrypted-history deletion, expired-record cleanup, failed cleanup alerting, backup retention, key rotation and account deletion. Encryption does not remove the company's access to decrypted data or its responsibilities. OAuth provider IDs remain plaintext metadata.
8. Publish the actual operator name, contact/grievance route, purposes, processors, retention, user rights/request procedure and applicable consent process. The bundled privacy page is a technical disclosure that explicitly requires operator configuration, not a completed legal notice.
9. Keep the initial audience 18+. Age self-declaration is not age verification. Do not enable under-18 use until a reviewed consent and safeguarding flow exists.
10. Approve any model provider's data policy before enabling it. Make its identity clear to users. Bullets may contain personal or confidential information even when names/contact fields are excluded. Do not silently route to another provider.
11. Test keyboard navigation, mobile browsers, screen readers, dialog focus handling and error recovery. The supplied responsive CSS and semantic labels do not substitute for an accessibility audit. Replace permissive inline-script CSP with a tested nonce strategy when hardening deployment.
12. Do not market the coverage percentage as an employer's ranking or the guard as candidate-truth verification. Do not use a watermark/fee to force a fresher to advertise your company. Any future evidence badge must state the exact assessment it represents.

## Already implemented

- Same-origin write checks and an allowlisted Next.js proxy; client authorization headers are not forwarded.
- Strict Zod/Pydantic contracts, bounded bodies, unknown-field rejection and explicit boolean consent.
- Fail-closed source-local rewrite rules and fresh export validation.
- Safe string rendering; no dynamic Typst execution from resume input.
- Font coverage checks, PDF text comparison and geometry/page-count checks.
- File limits, worker wall time and Linux resource caps, no notebook/code execution.
- Fixed-origin GitHub requests without redirects or arbitrary fetch URLs.
- No external LLM by default; separate opt-in when configured.
- Owner-scoped encrypted history, short-lived internal user JWTs and deletion endpoints.
- No-store response headers and validation errors that omit Pydantic's raw input field.

## Threat boundary

The user can lie in their source. The system does not prevent that. It prevents the application from inserting unapproved transformations into the submitted resume. User-controlled source hashes are integrity aids, not third-party attestations.

External dependency resolution and production network controls were not exercised in the offline authoring environment. See BUILD_STATUS.md.
