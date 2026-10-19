# ALU Helios Election Server

The Django / Helios backend for the [ALU Rwanda SRC election portal](https://github.com/einsteinnnamah/ALU_Election_App). It stores encrypted ballots, verifies cryptographic proofs, enforces voting eligibility, computes tallies and releases results.

The Next.js portal owns account sign-in, committee workflows, shared nomination plans, surveys, email delivery and published report snapshots. This backend independently authorizes sensitive operations through the portal's authenticated bridge. Each application uses its own Neon PostgreSQL database.

## Runtime

| Component | Purpose |
| --- | --- |
| Python 3.13+, Django 5.2 and Gunicorn | Helios HTTP service |
| PostgreSQL | Elections, voters, encrypted ballots, verification jobs and confirmation outbox |
| Database verification workers | Durable proof verification with row locking and retry handling |
| Confirmation sender | Sends verified-vote notifications through the portal |
| Cloudflare Worker and Container | Public request protection and backend hosting |
| Recovery Durable Object | Scheduled prewarming and lifecycle/verification recovery |

Production uses `settings_cloudflare`. The container supervisor runs HTTP workers, database proof verifiers and the confirmation sender together. Legacy tally tasks run synchronously. Pending votes, active elections and unfinished publication keep lifecycle recovery active; the container can sleep after its inactivity period when work completes.

New elections use a server-managed trustee key. The browser encrypts student choices, while Helios verifies proofs and tallies encrypted aggregates. Server administrators are trusted with stored key custody. Authorized committee users can access provisional aggregate counts when all required keys are held by the server; the normal eligibility review, tally and release workflow remains authoritative.

## Portal integration

- Management calls use a shared private bridge secret and an independent portal capability callback. Helios also checks election ownership/admin access.
- Student submission redeems an election-bound, single-use authorization grant and rechecks current eligibility. Committee members cannot vote.
- Accepted ballots and verification jobs commit atomically. Retries reconcile an existing active submission rather than creating another one.
- Successful verification stores the counted encrypted ballot and queues its confirmation in one transaction.
- The portal saves validated released ballots and reports, allowing published-result reads without waking this backend.

See [the UI integration](docs/alu-ui-integration.md), [verified submission](docs/verified-vote-submission.md) and [verification queue](docs/vote-verification-queue.md) documentation for details.

## Configuration and deployment

Follow the [Cloudflare deployment guide](docs/cloudflare-backend.md) for the complete configuration, startup and deployment procedure.

| Variables | Purpose |
| --- | --- |
| `DATABASE_URL` | Backend PostgreSQL database; separate from the portal database |
| `SECRET_KEY`, `EMAIL_OPTOUT_SECRET` | Django and email opt-out signing secrets |
| `ALU_BRIDGE_SECRET` | Must match the portal's bridge secret |
| `ALU_BRIDGE_APP_ORIGIN` | Exact public HTTPS portal origin |
| `ALU_BRIDGE_CLIENT_ID` | Must match the portal's bridge client identifier |
| `ALU_BRIDGE_ELECTIONS` | Optional additional election UUID allowlist |
| `RECOVERY_SECRET` | Private lifecycle-probe authentication |
| `PUBLIC_BACKEND_ORIGIN` | Exact public HTTPS Worker origin; forwarded to Django as `URL_HOST` |

The container validates configuration and applies Django migrations before starting the service. Database schema migrations under `helios/migrations/` and other Django applications are versioned source code required for setup and upgrades.

Credentials belong in the deployment's secret store or ignored local configuration. `cloudflare/.dev.vars.example` contains placeholders. Local databases, private backups and `.local-testing/` do not belong in Git or the container image. Dependency installation uses the committed `uv.lock` and Cloudflare package lockfile.

## SendByte email

The portal holds `SENDBYTE_API_KEY` and `TEAM_EMAIL_FROM`; no SendByte credential is needed here. The supervised confirmation sender calls the authenticated portal endpoint after vote verification. Messages contain no candidate choices, ballot proofs or trackers, and email failures do not undo a verified vote.

The provider switch requires backend migration `0016_sendbyte_email_provider`, the matching portal migration `0023_sendbyte_email_provider.sql`, and coordinated deployment. Previously attempted unsent Resend confirmations require review. Never-attempted jobs transfer to SendByte; sent records are preserved. Stop old senders and drain in-flight sends before switching providers. See [the confirmation migration notes](docs/verified-vote-submission.md#sendbyte-provider-migration) and the portal's `docs/sendbyte-migration.md`.

## Development and tests

Install Python 3.13+, uv, PostgreSQL and the LDAP development libraries required by the dependencies, then install the locked environment:

```sh
uv sync --frozen
```

The CI suite uses PostgreSQL 16. `settings_ci.py` expects a local `helios` database at `localhost:5432` with the test credentials defined in that file. Use a dedicated test server; Django creates and removes its test database.

```sh
uv run python manage.py test --settings=settings_ci
```

For the encrypted submission and confirmation flow specifically:

```sh
uv run python manage.py test helios.test_alu_submission --settings=settings_ci
```

Tests use synthetic fixtures and stub external authentication/email boundaries. They do not establish live inbox delivery or production throughput. GitHub Actions runs the backend test suite; Cloudflare deployment is a separate manual workflow.

## Main source locations

- `helios/models.py`: elections, voters, ballots, trustees and durable jobs.
- `helios/alu_management.py`: portal-controlled election management.
- `helios/alu_submission.py`: authenticated encrypted submission.
- `helios/bridge_eligibility.py`: independent student and committee checks.
- `helios/vote_verification.py`: database-backed verification queue.
- `helios/vote_confirmation.py`: durable confirmation delivery.
- `helios_auth/`: shared login protocol and authentication.
- `cloudflare/`: Worker, Container and recovery scheduling.
- `scripts/`: startup and process supervision.

This fork builds on the Helios Election System and retains its Apache 2.0 license. Hosted rehearsal evidence is documented in the deployment guide and the companion portal; complete student rehearsals and capacity measurement remain necessary before relying on the system for a live election.
