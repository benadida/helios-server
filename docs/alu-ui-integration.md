# ALU election UI and Helios

The existing creation wizard, candidate cards, clear-choice controls, review,
committee dialogs and receipt design are reused. No Next.js voting action
receives choices. The preview reducer is not a voting engine.

## Creation and setup

1. `/elections/new` creates a server-owned Neon reservation and authenticated
   Helios draft. A fresh verified student committee session needs `election.create`.
   The server UUID becomes the planning record ID.
2. Existing browser records retain their URLs: **Connect this planning record**
   creates a unique server-owned alias and a new Helios draft. It does not overwrite
   the Alice/Bob test election. Conflicting organizer aliases are rejected.
3. Continue using the candidacy and published-field screens. Review approved
   candidates in **Sync & freeze approved ballot**. Both `ballot.configure` and
   `phase.advance` are checked. Helios independently fetches fresh Neon-backed
   capability authorization and checks its existing owner/admin relationships.
4. Freezing locks candidate order and schedule. A setup digest rejects a ballot
   changed after review. Dates use Africa/Kigali: opens at 00:00, closes at 23:59.
   Retrying cannot change a frozen ballot's candidates or schedule.
5. Close/tally, combine trustee decryptions and release results use the existing
   protected Helios handlers, including ballot policy checks and eager processing.

Only explicitly published fields of approved candidates are sent during setup.
Preview ballots, rejected candidacies, private endorsements and unrelated
submissions are excluded. Public cards are saved in Neon for other browsers.
Full planning/candidacy storage remains the existing browser prototype; this
change does not migrate that workflow to a shared candidate-management backend.

## Voting and verification

- `/vote/<planning-id>` resolves a server-owned link and fetches the exact raw
  Helios JSON. Its original serialization determines the election fingerprint.
  Private, unlinked, mismatched and unsupported ballots fail closed.
- A browser worker imports unmodified Helios crypto/verifier files, pinned by a
  SHA-256 provenance manifest. Browser `crypto.getRandomValues` seeds the existing
  SJCL/Helios encryption and proofs. Choices remain in browser memory.
- Review shows the actual ciphertext tracker. Auditing uses Helios's existing
  `verify_ballot` locally, opens the audited ballot only locally and destroys its
  castable ciphertext. Casting after audit requires fresh encryption. Audit
  openings are never uploaded automatically.
- A native form sends only `encrypted_vote` directly to Helios. The handoff checks
  the configured ALU Origin, exact ciphertext schema and election hash/UUID, and
  rejects plaintext/randomness or extra fields. It cannot cast or register a voter.
- The bound, single-use shared login supplies identity before explicit ALU-styled
  confirmation on Helios's origin. This avoids cross-site iframe-cookie reliance
  ([cookie behavior](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie)).
  Helios independently checks verified identity and current noncommittee eligibility
  immediately before accepting the ballot.
- Existing proof verification, registration, ciphertext storage, trustees and tally
  are unchanged. Tracker lookup distinguishes pending, verified, invalid, missing
  and superseded ballots. The UI does not claim a tracker was counted just because
  submission returned successfully. Results come only from released Helios results,
  with links to its independent verifiers.

Committee login does not grant or remove roles. Authorized creation grants
ownership of that new draft only, without setting a global Helios administrator
flag. Later committee appointments still require explicit ballot-policy review;
ballots are never silently deleted.

## Deployment and checks

Apply frontend migration `0014_helios_elections.sql` before deploying its async
allowlist loader. The bridge migration script includes it. Render startup applies
Helios migration `0012_aluelectionbinding`. No new secret, Google OAuth client,
paid service, worker or broker is required.

The management API shares the existing HTTPS secret boundary. Disable request
body/header capture. Authorization checks current verified Neon identity, active
official membership, capability overrides and a server-owned reservation. Helios
checks the client and its own owner/admin permissions, and serializes management
actions with a PostgreSQL transaction lock.

Tests use the actual React booth in an isolated DOM with real Helios JavaScript
encryption/auditing, then Django registration, CSRF confirmation, tracker lookup
and real eager encrypted tallying. The existing creation wizard is exercised,
including permission refusal and retry. Browser transport and Neon sessions are
fixtures; tests never fabricate production accounts. Run the full Helios suite
with sibling frontend dependencies for the React test. A Helios-only CI checkout
explicitly skips that cross-repository DOM test; backend security tests still run.

The demo supports one choice per seat and verified noncommittee students.
Cohort-specific voter rules fail closed until authoritative student profiles
exist; browser year/program fields are not voter eligibility. Free-host limits
and the role-change/ballot-write race in the security review still apply.

## Real nomination login and shared links

The nomination and public ballot screens now load server-owned setup rather than
localStorage. **Open nominations** persists setup in Neon, and **Publish
nomination link** repairs an older browser-only record after it is connected.
Preview candidates and ballots are not imported as authenticated submissions.

Nomination sign-in uses the existing Neon Auth Google redirect. Each draft/save
and submission validates a fresh server session and a verified `alustudent.com`
address. Identity is never inferred from a name or accepted from the browser.
Private drafts belong to the actual session subject; one final nomination per
student is enforced through atomic version checks. Concurrent submission and
closure cannot overwrite each other. Year/program and endorsements are
self-reported facts for committee review, not verified voter eligibility.

Authorized committee capabilities protect opening, closing, vetting, appeals and
publication on the server. Reviewer IDs come from the session, and server-approved
candidate decisions supply ballot freezing. Public projections exclude student
email, endorsers, private attestations and unpublished submissions. Candidate
setup/submissions now persist across browsers; unrelated planning/Q&A preview
features have not all been migrated to a shared backend.

Apply frontend migration `0015_helios_nominations.sql` before deploying this
update. No Render change or new OAuth credentials are needed. Tests cover actual
sign-in/nomination UI components with fixture transport plus server actions against
isolated PostgreSQL, including forged local sessions, cross-account draft access,
forged identity, duplicate/concurrent submission, phase closure and revoked roles.
