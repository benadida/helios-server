# Verified submission and email confirmation

The paired frontend implements the voting screen and authenticated `/api/helios/submit/[id]` and `/api/helios/vote-email` routes. See the sibling app's `docs/verified-vote-submission.md` for the complete protocol, failure behavior, validation and coordinated rollout.

This backend adds an authenticated `/helios/elections/[uuid]/ui/cast` endpoint that redeems the existing single-use PKCE grant, independently rechecks student eligibility, serializes first registration and ballot acceptance, and records the encrypted ballot and verification job atomically. The status read now retains explicit rejected and verification-attention states. Verified status requires the ballot to be stored for counting, not merely a verification timestamp.

Migration `0015_vote_confirmation_email` is required before enabling this path. Successful proof verification and storing the ballot create one durable confirmation entry in the same transaction. `run_vote_confirmation_sender` delivers it through the authenticated frontend, using stable idempotency, leases and bounded automatic retries. The container supervisor runs this sender independently from the HTTP server and proof verifiers. Pending mail keeps the lifecycle recovery probe active, including after publication. No extra provider credential is needed in the backend.

Use `python manage.py run_vote_confirmation_sender --status` for aggregate delivery states; investigate `review_required` entries before any manual retry. Automatic retries stop at 23 hours from their first attempt. The mail has no candidate choices, proof, tracker or subject ID. Existing historical ballots are not backfilled. An email delivery failure cannot undo a verified vote.

No production rollout or real student email was performed by this implementation. Apply the migration and coordinate Worker/backend/frontend deployment, then validate a dedicated test student's complete flow and inbox before relying on it for a live election.

## SendByte provider migration

Verified-vote confirmation requests now include `provider: "sendbyte"` when calling the portal. Backend migration `0016_sendbyte_email_provider` preserves sent Resend records, moves never-attempted jobs to SendByte and holds previously attempted unsent jobs as `review_required`. Stop old senders and drain in-flight sends before migration; deploy the matching portal endpoint and backend together before resuming delivery. The portal alone holds `SENDBYTE_API_KEY`; no provider secret is added to Helios. The existing 23-hour automatic retry period remains an application policy. Review legacy Resend records before replacing any ambiguous message. See the portal's `docs/sendbyte-migration.md` for the coordinated rollout and configuration.
