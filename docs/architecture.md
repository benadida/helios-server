# Helios Architecture

This document describes how the Helios server is built. It is meant as a map
for developers. For an explanation aimed at election administrators, voters
and trustees, see [How Helios Works](how-helios-works.md).

## Overview

Helios is a Django application backed by PostgreSQL, with Celery (over
RabbitMQ) for background work. Ballots are encrypted in the voter's browser
by a JavaScript voting booth, so the server only ever receives encrypted
ballots. The server adds the encrypted ballots together homomorphically, the
election's trustees each partially decrypt that encrypted tally, and the
partial decryptions are combined into the result.

```
 browser                                   server
 ───────                                   ──────
 voting booth (heliosbooth/)  ──ballot──▶  Django: helios/, helios_auth/, server_ui/
 verifiers (heliosverifier/,  ◀──JSON───        │
   heliosbooth/single-ballot-verify.html)       ├── PostgreSQL
 trustee key/decrypt pages    ◀────────▶        └── Celery worker (RabbitMQ)
```

Runtime: Python 3.13, Django 5.2, PostgreSQL, Celery, dependencies managed
with `uv` (`pyproject.toml`, `uv.lock`). Cryptography on the server uses
pycryptodome for hashing and randomness and Python integers for the group
arithmetic.

## Code layout

| Path | Contents |
| --- | --- |
| `helios/` | The election application: models, views, crypto, Celery tasks, templates, tests. |
| `helios/crypto/` | ElGamal, zero-knowledge proofs, number theory, hashing helpers. |
| `helios/workflows/homomorphic.py` | Encrypted answers, encrypted votes and the homomorphic tally. |
| `helios/datatypes/` | JSON serialization of crypto and election objects (the `legacy/...` formats). |
| `helios_auth/` | User accounts and the pluggable login systems (`auth_systems/`). |
| `server_ui/` | The site shell: home/about/FAQ/privacy pages, the shared base template (`templates/base.html`) and the site CSS (`media/`). |
| `heliosbooth/` | The JavaScript voting booth, and the single-ballot verifier. |
| `heliosverifier/` | The JavaScript whole-election verifier. |
| `settings.py`, `urls.py` | Project settings and top-level URL routing. |

URL prefixes (`urls.py`): `/helios/` election app, `/auth/` login, `/booth/`
and `/verifier/` static JavaScript apps, `/static/` media, `/optout/` and
`/optin/` email opt-out, and `/` for the `server_ui` pages. Every election
URL lives under `/helios/elections/<uuid>/` (`helios/election_urls.py`).

## Data model

All in `helios/models.py` except `User`:

- **`User`** (`helios_auth`): an account from one login system, identified by
  `(user_type, user_id)`, e.g. `('google', 'alice@example.com')`. `admin_p`
  marks site administrators.
- **`Election`**: settings, questions, the election public key, timestamps
  for each lifecycle step, and after tallying the `encrypted_tally` and
  `result`. Has a creator (`admin`) plus optional co-administrators
  (`admins`). Deleting an election is a soft delete (`deleted_at`); the
  default manager hides deleted elections.
- **`Voter`**: one entry on an election's voter list. Either linked to a
  `User` (Google, GitHub, CAS, ...) or, for password voters, holding a
  login ID and a generated password directly. Keeps a copy of the voter's
  latest verified ballot (`vote`, `vote_hash`, `cast_at`), which is what gets
  tallied. Optional alias (`V1`, `V2`, ...) for elections that hide voter
  names.
- **`CastVote`**: every ballot a voter submits, with its hash (the ballot
  tracker), a short hash for URLs, and when it was verified or rejected.
- **`AuditedBallot`**: a ballot the voter chose to spoil and audit instead of
  cast. Includes the encryption randomness, so anyone can check it.
- **`Trustee`**: holds a share of the election key: public key, proof of
  knowledge of the secret key, and later the partial decryption of the tally
  with proofs. A trustee whose `secret_key` is set is the Helios trustee,
  whose key the server holds.
- **`VoterFile`**: an uploaded voter CSV, stored in the database and
  processed in the background.
- **`ElectionLog`**: a short audit log of major events (voter file added,
  frozen, trustee added, administrator added or removed, voters removed,
  decryptions combined, deleted/undeleted).
- **`EmailOptOut`**: SHA-256 hashes of email addresses that asked not to
  receive Helios email.

## Election lifecycle

1. **Create** (`election_new`). Any logged-in user can create an election
   unless `HELIOS_ADMIN_ONLY` is set. Creation also creates the Helios
   trustee, with a key pair generated on the server.
2. **Configure** (before freeze). The administrator edits questions, adds
   trustees, uploads voters, and for public elections chooses the
   registration mode: closed list, open to anyone, or open to a group from
   the administrator's login system.
   - External trustees generate their key pair in their browser
     (`election_keygenerator.html`). Only the public key and a proof of
     knowledge of the secret key are uploaded; the server checks the proof.
   - Trustees are reached through a secret link
     (`/helios/t/<short_name>/<email>/<secret>`) that the administrator can
     email them.
3. **Freeze** (`Election.freeze`). Requires at least one question, at least
   one trustee, every trustee's public key, and voters unless registration
   is open. The election public key is the product of the trustees' public
   keys. After freezing, questions, trustees and election settings can't
   change (voting can still be extended).
   Voters can still be uploaded or removed until tallying starts
   (`can_modify_voters`).
4. **Voting.** Open between `voting_starts_at` and `voting_ends_at` (both
   optional), with optional extension (`voting_extended_until`). See
   [Casting a ballot](#casting-a-ballot).
5. **Tally** (`one_election_compute_tally`). Refused while any cast ballot is
   still waiting for verification. Ends voting if it hasn't ended, then a
   Celery task multiplies together every voter's latest verified ballot to
   get the encrypted tally. If the election has a Helios trustee, a second
   task computes that trustee's partial decryption.
6. **Trustee decryption.** Each external trustee opens the decryption page,
   pastes in their secret key, and their browser computes partial
   decryptions of the tally with proofs. The server checks the proofs before
   saving them (`trustee_upload_decryption`).
7. **Combine** (`combine_decryptions`). When every trustee has submitted, the
   administrator combines the partial decryptions into vote counts.
8. **Release** (`release_result`). Results are visible to administrators after
   combining, and to everyone else only after release. The administrator can
   then email voters the result.

Winners are worked out each time results are displayed
(`electionalgs.one_question_result`). The top `max` answers win, but if
answers tie for the last seat none of them wins and the seat is left
unfilled. Single-winner questions with absolute majority also require more
than half of the ballots cast.

## Casting a ballot

1. The voter opens the booth (`/booth/vote.html?election_url=...`). It
   downloads the election JSON, seeds its random number generator with
   browser entropy plus 32 bytes from the server (`get-randomness`), and
   encrypts each answer in a Web Worker.
2. The booth shows the ballot tracker: the base64 SHA-256 hash of the
   encrypted ballot JSON. The voter can either:
   - **spoil and audit** the ballot: the booth reveals the encryption
     randomness, can post the ballot to the public audited-ballots list, and
     the voter starts again; or
   - **cast** it: the booth POSTs the encrypted ballot to the election's
     `cast_url`.
3. `one_election_cast` stores the encrypted ballot in the session and sends
   the voter to `one_election_cast_confirm`. That page asks the voter to log
   in if needed, offering only the login methods the election's voters use
   (`Election.voter_auth_systems`).
4. On confirmation the server saves a `CastVote` and queues
   `cast_vote_verify_and_store`. That task checks the ballot belongs to this
   election (election hash and UUID), that every ciphertext is in the right
   group, and every zero-knowledge proof. If all checks pass, the ballot
   becomes the voter's current vote, and the voter is emailed their tracker.
5. Voters can vote again. Each new verified ballot replaces the previous one.
   Earlier ballots remain in `CastVote`.

## Cryptography

- **Scheme.** ElGamal over a fixed prime-order subgroup (`ELGAMAL_PARAMS` in
  `helios/views.py`: a 2048-bit `p` and 256-bit `q`), with each answer
  encrypted as `g^0` or `g^1` ("exponential ElGamal"). Multiplying
  ciphertexts adds the underlying votes, so the tally is computed without
  decrypting any ballot.
- **Ballot proofs.** For each answer, a disjunctive Chaum-Pedersen proof that
  it encrypts 0 or 1. For each question with a `max`, a proof that the sum of
  its answers is between `min` and `max`. Proofs are made non-interactive
  with Fiat-Shamir using SHA-1, in both the Python and the JavaScript code.
- **Keys and decryption.** Each trustee has its own ElGamal key; the election
  key is their product. Decryption needs a partial decryption from every
  trustee (all of them, not a threshold). Each partial decryption carries a
  Chaum-Pedersen proof that it was computed correctly. The final counts are
  recovered from `g^count` by table lookup.
- **Hashes.** Ballot trackers, the election fingerprint and similar values
  are base64 SHA-256 (`helios/crypto/utils.hash_b64`). A ballot includes the
  hash of the election JSON it was made for.
- **Browser code.** The booth and verifiers use bundled JavaScript (jsbn for
  big integers, SJCL for randomness and hashing, plus Helios's own
  `elgamal.js` and `helios.js`). The booth page loads a compressed bundle
  (`heliosbooth/js/20160507-helios-booth-compressed.js`).

## Authentication and access control

- **Login systems** (`helios_auth/auth_systems/`). Each is a Python module with
  the same set of functions:
  - required: `get_auth_url`, `get_user_info_after_auth`, `send_message`,
    `can_create_election`;
  - optional: `check_constraint`/`list_categories` for group-based
    eligibility, `do_logout`.

  The registered systems are password, Google, GitHub, GitLab, Facebook,
  LinkedIn, Yahoo, CAS, LDAP, and `devlogin` (debug mode only).
  `AUTH_ENABLED_SYSTEMS` picks which are offered. After login,
  `helios_auth.views.after` stores the user in the session. An
  `AuthenticationError` raised by a system is shown to the user.
- **Password voters** are separate from site accounts. They log in to one
  election with the voter ID and password Helios generated and emailed them.
  The session then records `CURRENT_VOTER_ID`.
- **Permission checks** are decorators in `helios/security.py`:
  - `election_view` loads the election and, for private elections, redirects
    anyone who isn't an administrator, a trustee or a voter to a login page;
  - `election_admin` requires the creator, a co-administrator or a site
    administrator;
  - `trustee_check` requires the trustee logged in through their secret link.

  Both election decorators can also require the election to be frozen or not.
- **Site administrators** (`User.admin_p`) can administer any election, mark
  elections as featured, and use the `/helios/stats/` pages.

## Background tasks

Celery tasks live in `helios/tasks.py`; the worker runs with `--beat
--concurrency 1`. Tasks: verifying cast ballots, processing voter files,
computing the encrypted tally, the Helios trustee's partial decryption, and
sending email (to voters in bulk or individually, and notices to the
election creator). In tests, tasks run immediately (`CELERY_TASK_ALWAYS_EAGER`).

## Email

Voter emails are plain text, rendered from `helios/templates/email/` with
HTML escaping turned off. They are sent through the voter's login system:
password, Google, GitHub and most others send email via Django's mail backend
(SMTP, Mailgun or Amazon SES depending on settings). Every voter email
includes a signed opt-out link (`EMAIL_OPTOUT_SECRET`). Opted-out addresses
are skipped when sending and refused when voters are uploaded. Voter emails
are disabled `HELIOS_VOTER_EMAIL_CUTOFF_WEEKS` weeks after tallying.

## Public data

The JSON endpoints under `/helios/elections/<uuid>/` let anyone verify an
election independently:

- the election itself, including questions and public key;
- the voter list (`voters/`), showing names and hashed voter IDs, or only
  aliases;
- each voter's ballots (`ballots/<voter_uuid>/all`, `.../last`);
- the cast-ballot list (`ballots/`);
- trustees with their keys, proofs and partial decryptions (`trustees/`);
- audited ballots;
- the result, after release.

For private elections all of this is visible only to the election's voters,
administrators and trustees. `heliosverifier/verify.html` uses these
endpoints to check every ballot's proofs, the trustees' keys, the combined
key, the recomputed tally, the partial decryptions and the result.

## Web security

- **CSRF:** Django's CSRF middleware is off. Helios checks a session token on
  each state-changing POST (`check_csrf`), backed by a `SameSite=Lax` session
  cookie.
- **Headers:** a Content Security Policy (django-csp; inline scripts are still
  allowed for legacy pages), optional HTTPS redirect and secure cookies
  (`SSL=1`), and optional HSTS (`HSTS=1`).
- **Sanitizing:** election descriptions are sanitized with bleach before
  display.
- **Plaintext passwords:** voter passwords are stored in plaintext so they can
  be emailed and re-sent. The password login system also stores account
  passwords in plaintext (`User.info['password']`).

## Configuration and deployment

All settings are in `settings.py` and read from environment variables.
`get_from_env` ignores the environment while tests run. The main ones:

- `DEBUG`: on unless set to `0`; turning it on also enables `devlogin`.
- `SECRET_KEY`, `EMAIL_OPTOUT_SECRET`.
- `DATABASE_URL`, `CELERY_BROKER_URL`.
- `URL_HOST` and `SECURE_URL_HOST`: the election `cast_url` is built from
  `SECURE_URL_HOST`, so don't change it once elections exist.
- `ALLOWED_HOSTS`, `SSL`, `HSTS`.
- `AUTH_ENABLED_SYSTEMS` and `AUTH_DEFAULT_SYSTEM`, plus each login system's
  client ID and secret.
- Email: `EMAIL_HOST` etc., `MAILGUN_API_KEY`, or `EMAIL_USE_AWS`.
- Branding: `SITE_TITLE`, `WELCOME_MESSAGE`, `FOOTER_LINKS`, ...
- `ROLLBAR_ACCESS_TOKEN` for error reporting.

The `Procfile` runs a gunicorn web process and one Celery worker with beat.
Static files, the booth and the verifier are served by Django's static view
(`urls.py`). Setup steps are in [INSTALL.md](../INSTALL.md).

## Tests

Tests use Django's test runner with django-webtest, against PostgreSQL:

- `helios/tests.py`: models, views, end-to-end elections, crypto;
- `helios/test_csrf_smoke.py`: CSRF checks;
- `helios_auth/tests.py`: login systems;
- fixtures in `helios/fixtures/`.

CI (`.github/workflows/ci.yml`) runs:

```
uv run python manage.py test -v 2 --settings=settings_ci
```
