# Cloudflare backend deployment

The frontend stays on its existing host. Cloudflare runs the Django/Helios backend in a container. The backend uses its own Neon `helios` database; the frontend uses `neondb`. Cloudinary remains the image store.

## Required configuration

Worker: `alu-voting-backend`, ALU Cloudflare account.

Text variables:

- `PUBLIC_BACKEND_ORIGIN`: `https://alu-voting-backend.e-nnamah.workers.dev`
- `ALU_BRIDGE_APP_ORIGIN`: `https://elections.getpesa.xyz`
- `ALU_BRIDGE_CLIENT_ID`: `alu-helios-demo`
- `ALU_BRIDGE_ELECTIONS`: optional comma-separated election UUIDs; existing management bindings also authorize elections.

Secrets:

- `DATABASE_URL`: backend Neon database connection, including SSL configuration.
- `SECRET_KEY`, `EMAIL_OPTOUT_SECRET`, `ALU_BRIDGE_SECRET`: preserve the existing backend values; the bridge secret must match the frontend.
- `RECOVERY_SECRET`: separate random secret of at least 32 bytes.

Keep Cloudflare Access off for the public Worker. The app checks student identity and committee permissions itself.

## Deploy

Run from `cloudflare/`, with Docker running:

```sh
npm ci
npm run types
npm run check
npx wrangler deploy --dry-run --keep-vars
npx wrangler deploy --keep-vars
```

Dashboard secrets survive deployment. `--keep-vars` also preserves dashboard variables. Never place secret values in command arguments, config files tracked by Git, or Docker build arguments. `.dev.vars` is ignored and local only.

The container checks Django configuration and applies migrations to its configured backend database before serving requests. HTTP workers and vote verifiers run together under a supervisor. Accepted votes and verification jobs commit together in PostgreSQL. A separate Durable Object alarm keeps recovery running while votes await verification. When the queue is empty, it stops polling; the container can sleep after ten idle minutes.

## Switch the frontend

First make a private backup and verify copied elections, voters, submissions, results, and sessions. Check for changes on the old database immediately before switching. Pause submissions and reconcile changes if an election is open; an old snapshot cannot safely replace newer votes.

After hosted backend checks pass, change the frontend deployment's `HELIOS_BASE_URL` to the Worker origin and redeploy the frontend. Its authentication bridge only accepts the exact configured backend callback origin, so sign-in on the new backend cannot complete before that change. Keep the same bridge secret and client identifier.

Test one test election end to end: student sign-in, optional positions, confirmation, submission, verification, locked repeat voting, committee permissions, counts, closing, publication and reloading results. Use synthetic or consenting test users and a test election. Do not add load-test votes to a real election.

## Rollback and cost

Render hosting is retired. Cloudflare and its Neon backend database are authoritative. Restore or roll back using the current authoritative data and a reviewed backup; do not switch to an obsolete database snapshot.

Workers Paid is the account subscription. Container CPU, memory, disk and network usage have their own metered charges; the monthly subscription is not an all-inclusive backend hosting price. The current instance cap is one `standard-4` container. Neon and the frontend host have separate allowances and charges.

Local backups, credentials, test scripts and reports belong under `.local-testing/` and must stay out of Git and the container image.

## GitHub source and deployment

A CLI deployment uploads local files; it does not connect Cloudflare to GitHub. `.github/workflows/cloudflare-deploy.yml` prepares a separate, manual GitHub deployment using the selected committed revision. It checks Worker types and builds the backend first. It never deploys on a push or pull request.

After local review, commit the app changes. For the workflow, create a GitHub environment named `cloudflare-production`, add a scoped `CLOUDFLARE_API_TOKEN` as an environment secret, and require deployment review if available for the repository. Use Cloudflare's account-scoped Worker, Durable Object and Container deployment permissions for that token; keep database and application secrets in Cloudflare. The workflow account ID is the ALU account. No token belongs in a committed file.

Alternatively, connect the repository in the Worker's Settings → Builds through the Cloudflare GitHub app, select the intended production branch, set the root directory to `cloudflare`, the build command to `npm ci && npm run types && npm run check`, and the deploy command to `npx wrangler deploy --keep-vars`. Container builds need the repository's parent Dockerfile and build context. Disable nonproduction automatic deployments before enabling that connection. Choose one deployment path to avoid competing deployments.

## Traffic protection

The Worker has local source protections for oversized POST bodies (including chunked requests), incorrect voting origins, unsupported HTTP methods, attempts to reach private endpoints, unauthenticated management calls, and repeated submissions from the same browser session. Rejections happen before starting the backend container. Browser-session rate limits are supplementary: they are not identity verification and can be bypassed by changing cookies. Django separately verifies the student, permissions, CSRF and the shared per-student database limit. Students sharing a campus IP are not grouped into one retry limit.

These source changes take effect only after deployment. Worker hosting is not proof that the frontend domain has been placed behind Cloudflare's firewall. At the local rehearsal, the ALU account returned no `getpesa.xyz` zone and public DNS used Namecheap nameservers. Before changing DNS, add/review the zone in the intended account, preserve every existing DNS and mail record, and verify the frontend host's proxy support. Then configure the proxied election hostname, HTTPS and supported firewall rules. A nameserver change affects the whole domain, so schedule it separately from local testing.

Apply supported managed attack rules, and test legitimate student login, the browser-to-backend form handoff and server-to-server bridge calls. Do not add JavaScript challenges to bridge API endpoints, cache authenticated responses, or set a tight shared-IP voting limit. Bind the backend to its own protected hostname if zone firewall rules are required there; a `workers.dev` URL alone does not provide your zone's custom WAF rules. Keep Access off for public student voting.

Local tests simulate browser and identity-provider boundaries with synthetic accounts. Real Google/Neon sign-in, edge WAF challenges, internet latency, DNS and hosted cold starts still require a controlled staging check before the real election.
