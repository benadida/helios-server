# Server-managed demo guardrails

Helios retains its native client-side ballot encryption, proof checks, trackers and homomorphic tally. One server-owned trustee decrypts the aggregate; human key uploads are retired for new elections. This trusts the application host and database administrators with key custody. Database encryption alone does not protect a key from a fully compromised application server.

## Implemented controls

- Shared-login codes are hashed, short-lived, atomically single-use and browser/election bound. Identity comes from the verified Neon session.
- Fresh server-side capability checks protect management. Verified student eligibility and committee exclusion are checked at casting. Existing role permissions are preserved.
- Management serializes operations per election. Frozen ballots cannot be changed. Tally requires freezing; combination requires a computed encrypted tally and ready contributions; publication requires a result. Repeated completed actions remain idempotent.
- Helios caps request parsing at 2 MiB and 100 form fields; management requests are capped at 64 KiB. Bridge JSON handlers cap streaming bodies at 8 KiB.
- Authenticated ALU ballot/register requests share an atomic PostgreSQL counter limited to 20 per database-clock minute per server-session identity; rejected requests return 429 and Retry-After. No browser subject or forwarded IP is trusted for this limit. Receipt GETs are not limited by it.
- Rate counters survive worker restarts and are shared across workers using the existing database. Counters store hashed identity, saturate at 20, and delete expired rows in bounded batches. A database failure returns 503 before protected work. This remains an application guard, not a DDoS guarantee: the database itself has finite capacity. Migration 0013_shared_request_limits must run before this middleware is deployed; Render startup already runs migrations.

## Hosting and operational requirements

Render provides automatic free edge DDoS protection: https://render.com/docs/ddos-protection . Application request limits supplement it as recommended by https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html .

Keep DEBUG off in hosting, HTTPS and secure cookies on, host allowlists exact, and credentials server-only. Disable request header/body logging. Restrict Render/Vercel/Neon operator accounts and enable MFA. Do not expose production databases beyond required operator access.

Back up the Helios database, including the server trustee key, encrypted under a separately protected backup secret; test restoring into an isolated environment. This is an operator requirement, not an automated backup already provisioned by this change. OWASP key guidance: https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html .

Render Free sleeps after idle periods and its free database expires. Check https://render.com/docs/free before scheduling elections. It is a small demo, not demonstrated capacity for 3,000 concurrent voters. Eager Celery runs expensive work synchronously. Production requires measured capacity, durable backups and a scalable shared limit/queue design.

No live denial-of-service testing is performed. Render prohibits it: https://render.com/docs/penetration-testing . Test abuse locally and run only authorized, bounded security checks.
