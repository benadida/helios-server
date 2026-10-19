# Durable vote verification

`ALU_VOTE_VERIFICATION_BACKEND=database` stores each verification job in PostgreSQL
in the same transaction as its submitted vote. The request returns without doing
cryptographic verification. Existing `celery` mode remains the default.

Apply migrations before enabling the database backend. The existing container
startup script runs migrations, then starts the HTTP server and supervised
verification processes when database mode is enabled:

```sh
ALU_VOTE_VERIFICATION_BACKEND=database
WEB_CONCURRENCY=2
VOTE_VERIFIER_CONCURRENCY=2
```

These processes share the container's CPU and RAM. Additional processes do not
provide additional CPU. Validate concurrency with the final ballot and host.
Alternatively, deploy the verifier as a separately supervised service:

```sh
python manage.py run_vote_verifier
```

PostgreSQL row locks prevent two workers processing the same job. Verification,
updating the counted vote and marking the job complete commit together. A restart
rolls back interrupted work; a restarted worker automatically picks it up. Startup
also recovers pending submissions created before database queue mode was enabled.
It also repairs an older interrupted write where a vote was verified but not yet
stored for counting. It preserves newer votes and refuses to add a missing vote
after counting has started; that inconsistency requires operator review.
Quarantined votes wait for release, and deleted elections are excluded.

Unexpected verification failures retry with backoff, up to eight attempts. A bad
cryptographic proof is invalidated rather than repeatedly retried. Exhausted jobs
remain `failed` with the exception class only; no voter identity, ciphertext or
connection string is logged. Operators must investigate failed jobs, then reset
their state, attempts and next-attempt time through authorized database/admin
operations. Pending votes continue to block final counting.

Use `python manage.py run_vote_verifier --once` to drain currently due work during
diagnostics. It does not wait for future retries. A stopped/sleeping container
cannot run workers: hosting must restart it and provide a wake-up/recovery strategy
if pending work remains. Cloudflare deployment wiring is a separate step.

Use `python manage.py run_vote_verifier --status` to inspect aggregate job counts.

The worker queue contains vote IDs and processing metadata only. Candidate
choices stay encrypted in the existing ballot records. Notifications run after
commit; a notification failure cannot undo a vote. External social status updates
are retained in legacy Celery mode, not stored in the database queue.
