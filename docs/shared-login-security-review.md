# Shared-login bridge review

Reviewed the shared-login implementation and committee-exclusion extension in both repositories. Base bridge: Helios `267c619`, Next.js `f26af8d`.

| Threat | Enforced control | Validation |
| --- | --- | --- |
| Login forgery | Server SDK validates the current Neon session with cookie-cache bypass; signed Helios requests and authenticated HTTPS redemption | Invalid signature, missing session, ineligible account, missing exchange authentication rejected |
| Account substitution | Stable managed user ID; matching managed session user ID; verified exact domain; current email and session rechecked at redemption; no email-based linking | Browser identity fields ignored; changed email, substituted session subject and revoked session rejected |
| Replay/concurrent redemption | Random 256-bit code, SHA-256 storage, max 60-second expiry; single PostgreSQL DELETE RETURNING; independently locked/consumed Helios browser request | Concurrent PostgreSQL requests produce exactly one winner; replay and expiry rejected |
| Login CSRF | Signed state/PKCE request; Helios session-key hash; exact Origin and existing custom CSRF checks; session and CSRF rotation | Wrong state, Origin, CSRF and browser session rejected |
| Open redirect | Exact configured HTTPS origins/callback; server-selected fixed local election return paths; redirect following disabled on exchange | Signed attacker callback rejected; client also checks fixed destination |
| Unauthorized election access | Election/client/PKCE/state binding, explicit allowlists in both apps, independent Helios enrollment/private-election checks | Wrong-election redemption/view, closed registration, private enrollment, legacy password-voter sessions and roster uploads rejected |
| Privilege escalation | No role inputs/claims in browser protocol; new Helios users have no admin flag; existing role checks remain server-side | Student tally request returns 403; existing explicit admin grant preserved; bootstrap grants one election only |
| Committee voting exclusion | Server-selected access-only committee grants; current official-role membership checked at issuance, voter-code redemption, enrollment and immediately before casting; no browser eligibility inputs | Committee direct URLs and existing sessions denied; pre-appointment voter code rejected; fresh-check outage/tampered reply fails closed; existing admin grant preserved |
| Membership after casting | Private trigger history survives revocation/reclassification; durable per-event policy review; pending reviews block tally, combination and release; explicit administrator retain decision with reason and actor | Verified ciphertext/proof/tracker retained; student cannot resolve; unsupported deletion rejected; model/task tally also blocked; later appointment creates another pending review |
| Credential disclosure | Fragments plus POST bodies; no-store/no-referrer; no request/body/token exception logging; credentials only server environment; grant table RLS with no browser policies | Migration applied in Neon and no browser policies present; no secrets committed |

234 Helios tests passed. 37 frontend security checks passed against isolated real
PostgreSQL. A cross-language integration test used Python-signed requests and the
production TypeScript authorization/exchange handlers, then real Helios encryption,
automatic voter registration, proof verification, closing and synchronous trustee
tallying. Only the managed Auth network session was a trusted fixture; no fake Auth
schema was created in Neon. Clean frontend production build passed. Next.js runtime
was patched from 16.3.4 to 16.3.8 following its dependency advisory.
The transitive source-map-js runtime dependency was patched to 1.2.2; the final
runtime-only npm audit reports zero advisories.

Remaining practical limits:

The UI integration and authenticated management API are reviewed in
[ALU UI integration](alu-ui-integration.md). Creation uses fresh verified committee
identity and capabilities, then grants ownership of the new draft only. Login
never grants this ownership. Existing election updates require both current
Neon capability checks and Helios's owner/admin check. Ciphertext handoff requires
the configured Origin and schema, and explicit same-origin CSRF confirmation.

- Render Free Docker startup and the hosted HTTPS exchange were verified. An existing
  Neon browser session opened Helios without another Google login, preserved the
  organizer controls, and direct ballot confirmation returned 403 for the committee
  account. A noncommittee student's live booth, casting and tally remain pending.
- The bridge trusts Neon Auth and both servers plus the shared secret. This is a
  reviewed custom demo protocol, not an independent security audit.
- Managed-session revocation after successful exchange takes up to five minutes
  to invalidate the Helios session. Committee membership and current verified
  student status are checked fresh for every ballot; the bridge does not synchronize
  or automatically grant Helios administrator roles.
- Membership reads in Neon and ballot writes in Helios are not one distributed
  transaction. A simultaneous role grant can race the final check; subsequent
  policy checks flag current membership conflicts and recorded post-cast grants.
  Historical grant/cast comparisons depend on provider UTC clocks. A production
  election needs role freezing or a coordinated authorization/commit protocol.
- Policy reviews are discovered during voting denial, explicit administrator
  review, tallying, combination and release, not proactively by a worker.
  Changes after publication require a governance decision; published results are
  never silently rewritten. This demo supports explicit retention only; any
  exclusion must be separately specified and reviewed.
- Committee means active `role_assignments` joined to `roles.is_official` using
  the existing back-office admission definition, including observers and trustees.
  The bridge does not change Neon role assignment or capability checks.
- Browser XSS or compromised app/deployment credentials defeats the corresponding
  identity boundary. Do not enable request-body/header capture in hosting logs.
- One free web worker and synchronous cryptography limit availability. Session
  throttling is small-demo protection, not a distributed abuse-control system.
- A single Helios trustee and temporary Free PostgreSQL are demo choices, not
  production election governance or durable hosting.
- npm reports development-tool advisories in the existing ESLint dependency tree;
  the patched Next.js runtime has no reported runtime advisory in that audit.
