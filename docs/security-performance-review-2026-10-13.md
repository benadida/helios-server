# ALU Elections security and performance review — 13 October 2026

All changes are local. No pushes, deployments, production database mutations, real votes, or real emails were made for this review.

## Scope and limits

Reviewed dependency locks and installed versions, voting handoffs and confirmation, provider-session validation, role checks, bridge authorization, file publication/upload validation, email delivery, live counts, server startup configuration and response headers. Ran local rendering, cryptographic, database and security checks. Sampled public HTTP responses without authenticating as anyone.

This is a source/dependency review with focused regression tests, not a complete penetration test or a production capacity certification. No browser trace/Core Web Vitals numbers were collected. The web-perf skill requires: “If unavailable, STOP—the chrome-devtools MCP server isn't configured.” That tool is absent here, so its browser-tracing workflow was stopped; source/HTTP checks continued independently. Production infrastructure settings and historical Git credentials were not comprehensively inspected.

## Findings and local fixes

| Finding | Why it matters | Local action and evidence |
| --- | --- | --- |
| Backend pinned Django 5.2.9 and older dependencies | The lock matched published advisories, including denial-of-service risks. Some advisories depend on features this app does not use; version matches alone are not proof of exploitation. | Updated Django to 5.2.18, Bleach to its final 6.4.0 release, Gunicorn to supported 25.3.0, and refreshed compatible transitive dependencies. OSV scan before: 12 package names with advisory matches among 66 checked. After: no matches among 68 checked, including development dependencies. |
| Two independent login cookies | App sign-out leaves the voting service's cookie intact. Reusing that cookie after switching app accounts could attribute the vote to the previous student. | Every modal-confirmed submission now expires the old voting login and renews through the app's fresh signed-in identity. A regression test switches students and confirms the vote belongs to the newly authenticated student. The two-second login throttle remains; a confirmed submission waits and retries automatically rather than displaying a dead end. |
| Mutation authorization used the provider's cached session | Live database role checks were already present, but a cached provider session could remain usable briefly after provider-session revocation. | Privileged actions now require fresh provider-session validation, bound to the same user as the role lookup. Fresh checks are deduplicated only within the current request, not shared across users. Revocation, identity mismatch, unverified identity and revoked-role tests pass. |
| App responses lacked browser protection headers | Missing framing restrictions make clickjacking easier; missing nosniff permits unnecessary MIME guessing. | Added frame denial, nosniff, referrer policy, camera/microphone/location restrictions and a minimal CSP for framing, objects and base URLs. Disabled the framework identification header. This is not a full nonce-based script CSP or a blanket XSS fix. |
| One synchronous web worker/thread | External account checks and eager vote verification could block unrelated requests. | Default startup now uses one gthread worker with four configurable threads. Local simulated 250 ms I/O stall: unrelated request took 256.4 ms with one thread and 1.4 ms with four. This measures I/O concurrency only; it does not prove faster CPU-bound cryptography or production capacity. |
| Interim candidate counts exposed voting choices through differences between updates | A single arriving vote can reveal a student’s choices even without names in the response. | User approved withholding candidate totals while voting is open. The stats API now returns turnout/pending checks only during voting and never decrypts interim votes. After voting closes it returns the existing completed final count, without requiring publication. Public results remain hidden until publication. Database and UI tests enforce the boundary. |
| Committee snapshots loaded inline uploads on recurring refreshes | Large files increased database-to-app transfer even though the UI later replaced them with URLs. | Added a read-only JSON projection that removes file bytes before the database response. Existing authorized attachment URLs are built afterward. A PostgreSQL test turns a plan with a 1 MB photo into a sub-1 KB DTO while preserving the stored bytes and safe URL encoding. Mutation reads remain authoritative/full. |
| Crypto worker loaded only after confirmation | The browser had to fetch/initialize voting assets after the student confirmed. | The worker now initializes on the eligible open voting screen; it receives no choices until final confirmation. Committee, signed-out and results views do not warm it. Cryptographic/UI tests pass. No browser timing saving is claimed. |
| Vulnerable brace-expansion versions in development dependencies | Crafted glob patterns can exhaust CPU/stack in development tools. | Applied compatible lockfile fixes to 1.1.21 and 5.0.12. Production npm audit: zero known advisories. Five development alerts remain in one unpatched braces dependency chain; no unsafe forced framework downgrade was applied. |

## Important decisions and deployment work remaining

1. **Live candidate privacy policy implemented.** The user approved turnout-only live monitoring. Candidate totals are absent from the stats response while voting is open, rather than merely hidden on the screen. Closed elections show a counting state until the native final count is ready; then the authorized committee can see candidate totals/photos. Public publication remains separate. No interim decryption is performed by stats.
2. **Server-held decryption keys.** The demo can compute live totals only when all necessary trustee keys are held by the server. A voting-server/database operator with those keys can decrypt stored ballots. External trustee-held keys provide stronger separation, but exact live totals then cannot be supplied without trustee participation. Do not bypass external trustees or put their keys into the web app to obtain live counts.
3. **Free hosting and inline work remain a reliability limit.** render.yaml uses the free plan and eager verification. Free services can sleep after inactivity. Always-on hosting and a dedicated verification worker/broker are the appropriate production changes. Threads help waiting on I/O; they do not make the single CPU unlimited.
4. **Abuse protection needs infrastructure coverage.** The existing login cooldown is per session; new sessions can bypass a per-session limit. Use shared/platform rate limits for login starts and public APIs, with correctly trusted client-IP handling. Do not rely on a per-process counter as distributed protection. No CDN/WAF/rate-limit configuration was changed in this review.
5. **Uploads are not malware-scanned.** Size, MIME and magic-byte checks, publication rules, nosniff and sandbox/download headers are present and tested. They are not an antivirus scanner; JPEG/WebP decompressed dimensions are not uniformly checked like PNG/GIF. Add image decoding/re-encoding with pixel limits and malware scanning for documents before broad production use.
6. **Next.js update due 14 October 2026.** The maintainer has announced an upcoming release for two critical and one high upstream issue. Its details/fixes are not yet published as of this review. Next 16.3.8 / React 19.2.8 currently have no production audit matches; that does not certify immunity to the forthcoming issues. Re-audit and apply the supported patch when published.
7. **Legacy Django script CSP.** settings.py still permits unsafe-inline and unsafe-eval for legacy voting assets/templates. The new app header deliberately restricts framing/objects/base URLs without breaking framework bootstrap scripts; it is not a strict script CSP. Removing those allowances needs nonce/external-script migration and browser testing. Do not blindly tighten it and interrupt real voting.
8. **Bleach is archived.** The final patched version was applied, but a maintained sanitizer or plain-text-only rendering is the longer-term replacement. The sanitizer advisory is conditional; it should not be described as a demonstrated script execution exploit in this app.

## HTTP observations

One signed-out public login request returned 200 in 4.35 seconds total from this machine. It had HSTS and private/no-store caching, but lacked the additional headers now added locally. A public voting-service ballot request timed out after 26.28 seconds. These are sparse end-to-end observations, not browser paint metrics and not proof that Render cold start was the only cause.

## Verification

- Production Next.js build completed successfully.
- TypeScript and targeted ESLint completed successfully.
- 63 local PostgreSQL/backend tests passed and cover ballot submission/proof verification, one-vote locking and races, account renewal/switching, authenticated live totals, CSRF, rendering/deployment guards, and ciphertext avoidance and withholding candidate totals while voting remains open.
- Actual React/crypto flow tests run within the backend suite, including blank choices, select/deselect, modal cancellation and duplicate confirmation.
- 28 candidate-email/outbox checks passed with PostgreSQL and a stub provider; no real mail sent.
- Additional checks cover fresh mutation sessions, committee snapshot size, 29 upload checks, 16 attachment/publication checks, live candidate updates, nomination-email links, pending invitation routing and published-result rendering.
- Selected private-key/AWS/GitHub-token patterns found no matches in tracked working-tree files; no credential values were printed. This was not an exhaustive historic secret scan.
- Legacy standalone team and bridge scripts were not counted as passed: their required isolated database/setup was not provided by the generic test invocation. They were not redirected to the production database. The active bridge/role/CSRF paths have separate passing focused checks.

## Primary references

- Django security release, 6 October: https://www.djangoproject.com/weblog/2026/oct/06/security-releases/
- Gunicorn supported releases: https://github.com/benoitc/gunicorn/security
- Gunicorn thread setting: https://gunicorn.org/reference/settings/
- Bleach final sanitizer advisory: https://github.com/mozilla/bleach/security/advisories/GHSA-8rfp-98v4-mmr6
- Unpatched braces advisory: https://github.com/advisories/GHSA-vfj7-8cjw-p6xm
- Brace-expansion advisory: https://github.com/advisories/GHSA-qhr7-859c-m2p7
- Next.js upcoming update: https://nextjs.org/blog/upcoming-nextjs-security-update-october-2026
- Render free-service limitations: https://render.com/docs/free
- OSV API: https://google.github.io/osv.dev/api/
