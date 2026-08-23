# Helios System Architecture

## Overview

This document describes the technical architecture and implementation of the Helios voting system. For a conceptual understanding of how Helios works from a user perspective, see [How Helios Works](how-helios-works.md).

## Technology Stack

### Backend
- **Language**: Python 3.12
- **Web Framework**: Django 5.2
- **Database**: PostgreSQL 9.5+
- **Task Queue**: Celery with RabbitMQ broker
- **Cryptography**: pycryptodome library

### Frontend
- **Voting Booth**: Pure JavaScript (no framework dependencies)
- **Admin Interface**: Django templates with jQuery
- **Verification Tool**: Pure JavaScript

### Infrastructure
- **Web Server**: Compatible with WSGI (Gunicorn, uWSGI)
- **Message Broker**: RabbitMQ for Celery tasks
- **Deployment**: Supports Heroku, Docker, traditional servers

## System Components

### 1. Core Application (`helios/`)

The heart of the Helios system, containing all election logic, cryptography, and workflows.

**Key Files:**
- `models.py` (~42,000 lines) - Data models for elections, voters, votes, trustees
- `views.py` (~2,000 lines) - HTTP request handlers and API endpoints
- `workflows/homomorphic.py` - Tallying and decryption workflows
- `crypto/` - Cryptographic primitives (ElGamal, zero-knowledge proofs)
- `tasks.py` - Asynchronous Celery tasks
- `security.py` - Access control decorators

**Responsibilities:**
- Election lifecycle management
- Vote encryption/decryption
- Cryptographic proof generation and verification
- Tallying with homomorphic encryption
- Voter management
- Trustee coordination
- Audit logging

### 2. Authentication System (`helios_auth/`)

Modular authentication supporting multiple identity providers.

**Supported Systems:**
- Google OAuth
- Facebook OAuth
- GitHub OAuth
- GitLab OAuth
- LinkedIn OAuth
- Yahoo OAuth
- CAS (Central Authentication Service)
- LDAP (Lightweight Directory Access Protocol)
- Clever (education platform)
- Local password authentication
- DevLogin (development mode only)

**Architecture:**
- Abstract base class `AuthenticationExpired` defines interface
- Each auth system in `auth_systems/` directory implements the interface
- Settings determine which systems are enabled
- Support for eligibility constraints (e.g., must be in specific LDAP group)

**Key Files:**
- `models.py` - User model with flexible authentication
- `auth_systems/` - Individual auth backend implementations
- `views.py` - Login/logout flows
- `jsonfield.py` - JSON field for storing auth metadata

### 3. Voting Booth (`heliosbooth/`)

Client-side JavaScript application for ballot encryption and casting.

**Architecture:**
- Runs entirely in voter's browser
- No server-side dependencies for encryption
- Uses Web Crypto API and custom JavaScript crypto libraries
- Communicates with server only to fetch election data and submit encrypted votes

**Key Files:**
- `vote.html` - Main voting interface
- `templates/question.html` - Individual question rendering
- `js/` - Cryptographic JavaScript libraries
  - ElGamal encryption
  - Zero-knowledge proof generation
  - Random number generation

**Workflow:**
1. Load election parameters from server (public key, questions, candidates)
2. Display ballot to voter
3. Collect voter's choices
4. Encrypt each answer client-side using election public key
5. Generate zero-knowledge proofs for each encrypted answer
6. Display ballot summary and tracking hash
7. Submit encrypted vote + proofs to server
8. Show confirmation with ballot tracker

**Security Properties:**
- Server never sees plaintext votes
- Encryption happens in isolated context
- Random number generation uses secure browser APIs
- All cryptographic operations visible in browser console (for expert verification)

### 4. Verification Tool (`heliosverifier/`)

Client-side tool for voters to verify their encrypted ballots.

**Features:**
- Enter ballot tracking number
- Display encrypted vote in human-readable format
- Verify cryptographic proofs
- Confirm vote is included in encrypted tally
- Independent verification (doesn't require server trust)

**Key Files:**
- `verify.html` - Main verification interface
- JavaScript for proof verification

### 5. Admin Interface (`server_ui/`)

Web-based administration panel for election management.

**Features:**
- Election creation wizard
- Question and answer management
- Voter registration (bulk upload via CSV)
- Trustee management
- Election freezing
- Tally computation
- Result release
- Email notifications to voters

**Key Files:**
- `templates/` - Django templates for admin pages
- `views.py` - Admin-specific views
- Forms for election configuration

## Data Models

### Core Entities

#### Election
The central entity representing a voting event.

**Key Fields:**
- `uuid` - Unique identifier
- `short_name` - URL-friendly name
- `admin` - Creator/primary administrator
- `admins` - Additional administrators (many-to-many)
- `questions` - JSON array of question objects with answers
- `public_key` - Combined ElGamal public key from all trustees
- `private_key` - Present only if Helios is sole trustee
- `encrypted_tally` - Homomorphic sum of all encrypted votes
- `result` - Final decrypted tally
- Timestamp fields: `created_at`, `frozen_at`, `voting_starts_at`, `voting_ends_at`, etc.
- Flags: `private_p` (restricted access), `openreg` (open registration), `featured_p`

#### Voter
Represents an eligible voter in an election.

**Key Fields:**
- `election` - Foreign key to Election
- `user` - Foreign key to User (null for password-based voters)
- `voter_login_id` - Login identifier
- `voter_password_hash` - Hashed password for local auth
- `voter_email`, `voter_name` - Contact information
- `alias` - Optional anonymized identifier
- `vote` - Most recent encrypted vote (JSON)
- `vote_hash` - SHA-256 hash used as ballot tracker
- `cast_at` - Timestamp of most recent vote

**Note**: A voter can cast multiple times; only the latest vote counts.

#### CastVote
Immutable record of each vote submission.

**Key Fields:**
- `voter` - Foreign key to Voter
- `vote` - Encrypted vote (ElGamal ciphertext)
- `vote_hash` - SHA-256 ballot tracker
- `vote_tinyhash` - Shortened hash for URLs
- `cast_at` - Submission timestamp
- `verified_at` - When cryptographic verification completed
- `invalidated_at` - Set if vote failed verification
- `quarantined_p` - Flag for contested ballots
- `released_from_quarantine_at` - Resolution timestamp
- `cast_ip` - IP address (for abuse prevention)

**Purpose**: Maintains complete audit trail; verification happens asynchronously.

#### Trustee
Holds decryption key shares.

**Key Fields:**
- `election` - Foreign key to Election
- `email`, `name` - Trustee identity
- `public_key` - ElGamal public key
- `public_key_hash` - Hash for verification
- `secret_key` - Private key (only if Helios-managed)
- `pok` - Proof of knowledge of secret key
- `decryption_factors` - Partial decryptions of tally
- `decryption_proofs` - Zero-knowledge proofs of correct decryption

**Threshold Decryption**: All trustees must participate to decrypt results.

#### VoterFile
Tracks bulk voter uploads.

**Key Fields:**
- `election` - Foreign key to Election
- `voter_file` - CSV file upload
- `num_voters` - Expected voter count
- `processing_started_at`, `processing_finished_at` - Processing timestamps
- `voter_file_content` - Cached file contents

**Processing**: Asynchronous task creates Voter objects from CSV.

#### ElectionLog
Audit trail of all election events.

**Key Fields:**
- `election` - Foreign key to Election
- `log` - JSON object describing event
- `at` - Timestamp

**Events Logged**:
- Voter files uploaded
- Trustees added
- Election frozen
- Tallying started
- Decryptions combined
- Results released

### Supporting Models

- **AuditedBallot**: Ballots submitted for special audit
- **EmailOptOut**: Voters who've unsubscribed (stores hashed email)

## Cryptographic Architecture

### ElGamal Cryptosystem

Helios uses ElGamal encryption for its homomorphic properties.

**Parameters** (system-wide constants):
- `p` - Large prime (2048-bit)
- `q` - Prime order of subgroup
- `g` - Generator

**Key Generation**:
```
Trustee i:
  - Generate random secret key: x_i (in range [1, q-1])
  - Compute public key: y_i = g^x_i mod p
  - Generate proof of knowledge of x_i

Election:
  - Combined public key: Y = y_1 * y_2 * ... * y_n mod p
```

**Encryption** (in voter's browser):
```
To encrypt message m:
  - Choose random r
  - Compute alpha = g^r mod p
  - Compute beta = Y^r * g^m mod p
  - Ciphertext = (alpha, beta)
```

**Homomorphic Property**:
```
E(m1) * E(m2) = E(m1 + m2)

(alpha1, beta1) * (alpha2, beta2) = (alpha1 * alpha2, beta1 * beta2)
```

This allows tallying encrypted votes without decryption.

**Decryption** (threshold decryption):
```
Trustee i computes:
  - Decryption factor: f_i = alpha^x_i mod p
  - Proof: Prove (g, alpha, y_i, f_i) is valid DH-tuple

Server combines:
  - Combined factor: F = f_1 * f_2 * ... * f_n mod p
  - Plaintext: m = F^-1 * beta mod p
  - Discrete log: Find m such that g^m = plaintext
```

### Zero-Knowledge Proofs

Voters prove their encrypted votes are valid without revealing content.

**Disjunctive Proof** (proof of 0 or 1):
For each answer option, prove: "This is an encryption of 0 OR encryption of 1"
- Allows verification without revealing which
- Standard Sigma protocol construction
- Non-interactive using Fiat-Shamir heuristic

**Overall Ballot Proof**:
Prove: "Sum of selections is within allowed range [min, max]"
- Uses homomorphic property
- Verifies voter didn't overvote

**Trustee Decryption Proof**:
Prove: "Decryption factor computed correctly from my secret key"
- Chaum-Pedersen protocol
- Allows verification without revealing secret key

### Vote Verification Workflow

**Submission**:
1. Voter submits encrypted vote + proofs
2. Server stores in `CastVote` with `verified_at=None`
3. Returns immediately to voter

**Background Verification** (Celery task):
1. Check correct number of answers
2. Verify election UUID and hash
3. Verify each answer's encryption proof
4. Verify overall ballot proof
5. Set `verified_at` if valid, `invalidated_at` if invalid

**Tallying**:
Only votes with `verified_at` set and `invalidated_at` null are included.

## Workflows

### Election Creation Workflow

1. **Create Election** (`election_new` view)
   - Admin provides basic info: name, description, dates
   - System generates UUID and default Helios trustee
   - Election saved in "unfrozen" state

2. **Configure Questions** (`election_edit` view)
   - Admin adds questions
   - For each question: text, answer options, min/max selections
   - Stored as JSON in `Election.questions`

3. **Add Trustees** (`new_trustee*` views)
   - Option 1: Helios generates keypair
   - Option 2: External trustee generates own keypair
   - Each trustee added to `Trustee` table

4. **Add Voters** (`add_voters_file` view)
   - Upload CSV with columns: voter_id, email, name
   - Creates `VoterFile` object
   - Asynchronous task processes CSV
   - For password auth: generate random password per voter
   - Voters created in `Voter` table

5. **Freeze Election** (`freeze` view)
   - Validation: Has questions? Has trustees? Has voters?
   - Combine trustee public keys into election public key
   - Set eligibility rules
   - Set `frozen_at` timestamp
   - Election now immutable; voting can begin

### Voting Workflow

1. **Access Election** (`one_election_view`)
   - Public or private link
   - Private requires authentication

2. **Authenticate Voter**
   - Password: `password_voter_login` view
   - OAuth: Redirect to provider, callback handles token
   - CAS/LDAP: Server-side verification
   - Session stores `CURRENT_VOTER_ID`

3. **Load Booth** (`heliosbooth/vote.html`)
   - JavaScript fetches election data via API
   - Loads: questions, answers, public key, election hash

4. **Fill Ballot**
   - Voter selects answers
   - Client-side validation (min/max selections)

5. **Encrypt** (JavaScript)
   - For each answer: encrypt 0 or 1
   - Generate disjunctive proof for each
   - Generate overall proof
   - Compute ballot hash (tracking number)

6. **Cast** (`one_election_cast` view)
   - Voter confirms ballot
   - Encrypted vote submitted
   - Stored in session temporarily
   - Redirect to confirmation page

7. **Confirm** (`one_election_cast_confirm` view)
   - Display ballot tracker
   - Trigger background verification task
   - Allow voter to verify

8. **Background Verification** (Celery task: `cast_vote_verify_and_store`)
   - Verify all proofs
   - If valid: store in `Voter.vote` and `CastVote` with `verified_at`
   - If invalid: set `invalidated_at`
   - Emit `vote_cast` signal

### Tallying Workflow

1. **Initiate Tally** (`one_election_compute_tally` view)
   - Admin triggers after voting closes
   - Check: All cast votes verified?
   - Set `voting_ended_at`
   - Trigger Celery task: `election_compute_tally`

2. **Compute Encrypted Tally** (Celery task)
   - For each question, each answer:
     - Homomorphically multiply all encrypted votes
     - Result: `encrypted_tally[q][a] = E(total_votes_for_a)`
   - Store in `Election.encrypted_tally`
   - If Helios trustee exists, trigger auto-decryption

3. **Trustee Decryption** (`trustee_decrypt_and_prove` view)
   - Each trustee downloads encrypted tally
   - Locally: compute decryption factors and proofs
   - Upload to server
   - Server verifies proofs
   - Store in `Trustee.decryption_factors` and `Trustee.decryption_proofs`

4. **Combine Decryptions** (`combine_decryptions` view)
   - Check: All trustees submitted decryptions?
   - Multiply all decryption factors
   - Recover plaintext for each answer
   - Discrete log table lookup to find vote counts
   - Store in `Election.result`
   - Set `tallying_finished_at`

5. **Release Results** (`release_result` view)
   - Admin reviews results
   - Sets `result_released_at`
   - Optionally email all voters
   - Results now public

### Voter Management Workflow

**Bulk Upload**:
1. Admin uploads CSV (`add_voters_file`)
2. `VoterFile` created, task queued
3. Task (`voter_file_process`): Parse CSV, create `Voter` objects
4. For password voters: generate passwords
5. Check email opt-outs, notify admin if any

**Individual Voter**:
- Add via web form
- Email invitation automatically sent

**Email Notifications**:
- Invitation to vote
- Reminder to vote
- Results announcement
- Respects `EmailOptOut` table

## API and Views Architecture

### View Decorators (Security)

**`@election_view(frozen=False, frozen_check_needed=True)`**
- Loads election from URL parameter
- Checks if user has access (public vs private)
- Optionally enforces frozen state
- Passes `election` object to view function

**`@election_admin(frozen=False)`**
- Requires user is election admin
- User must be: creator, or in admins list, or staff
- Commonly used for configuration and tallying views

**`@trustee_check`**
- Requires valid trustee session
- Trustee authenticated via secret URL
- Used for decryption operations

### API Endpoints

Helios provides JSON APIs for election data:

- `/helios/elections/<uuid>` - Election metadata
- `/helios/elections/<uuid>/voters` - Voter list
- `/helios/elections/<uuid>/ballots` - Cast votes
- `/helios/elections/<uuid>/result` - Tally results

All JSON endpoints use `render_json()` helper, which:
- Serializes objects to JSON
- Handles datetime and custom types
- Sets appropriate content-type headers

### Templates

Django templates with custom tags:
- `server_ui/templates/` - Admin interface
- `helios/templates/` - Voter-facing views
- Custom template tags in `helios/templatetags/`

## Background Tasks (Celery)

### Task Queue Architecture

- **Broker**: RabbitMQ
- **Worker**: Celery worker process
- **Beat**: Celery beat for scheduled tasks
- **Concurrency**: Typically 1 worker (elections are rarely concurrent)

### Key Tasks

**`cast_vote_verify_and_store(voter_uuid, cast_vote_uuid)`**
- Triggered on vote submission
- Verifies cryptographic proofs
- Updates database with verification result
- Emits signals for observers

**`election_compute_tally(election_uuid)`**
- Triggered by admin
- Homomorphically combines all encrypted votes
- Can take minutes for large elections
- Chains to `tally_helios_decrypt` if Helios trustee present

**`tally_helios_decrypt(election_uuid)`**
- Helios trustee auto-decryption
- Computes decryption factors
- Stores in database

**`voters_email(election_uuid, subject, body, template_vars)`**
- Bulk email to all voters
- Respects opt-outs
- Used for: invitations, reminders, results

**`single_voter_email(voter_uuid, subject, body, template_vars)`**
- Single voter email
- Includes unsubscribe link

**`voter_file_process(voter_file_uuid)`**
- Process uploaded CSV
- Create voter accounts
- Generate passwords
- Handle errors gracefully

### Task Monitoring

- Celery Flower (optional) for task monitoring
- Django admin interface shows task status
- Logs capture task execution

## Database Schema

### Key Relationships

```
Election
  ├── Trustee (one-to-many)
  ├── Voter (one-to-many)
  │   └── CastVote (one-to-many)
  ├── VoterFile (one-to-many)
  ├── ElectionLog (one-to-many)
  └── AuditedBallot (one-to-many)

User
  └── Voter (one-to-many, nullable)
```

### JSONField Usage

Several models use `JSONField` for flexible data:
- `Election.questions` - Array of question objects
- `Election.encrypted_tally` - Encrypted vote totals
- `Election.result` - Final decrypted counts
- `Voter.vote` - Most recent encrypted vote
- `CastVote.vote` - Encrypted vote data
- `Trustee.decryption_factors` - Partial decryptions
- `User.info` - Auth provider metadata

This allows storing complex cryptographic structures without rigid schemas.

### Indexes

Key indexes for performance:
- `Election.uuid` - Primary lookup
- `Election.short_name` - URL routing
- `Voter.election + voter_login_id` - Login lookup
- `CastVote.vote_hash` - Ballot tracking
- `CastVote.vote_tinyhash` - Short URL tracking

## Configuration

### Environment Variables

**Required**:
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string
- `CELERY_BROKER_URL` - RabbitMQ connection

**Optional**:
- `DEBUG` - Enable debug mode (default: False)
- `ALLOWED_HOSTS` - Comma-separated hostnames
- `AUTH_ENABLED_AUTH_SYSTEMS` - Which auth backends to enable
- `DEFAULT_FROM_EMAIL` - Sender for emails
- `DEFAULT_FROM_NAME` - Sender name

**Auth-Specific** (e.g., for Google OAuth):
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

### Settings Structure

`settings.py` uses helper functions:
- `get_from_env(key, default)` - Environment with fallback
- Auth system configuration based on `AUTH_ENABLED_AUTH_SYSTEMS`

## Security Considerations

### Cryptographic Security

- **ElGamal**: 2048-bit keys (standard security level)
- **Random Number Generation**: Uses secure browser APIs and server entropy
- **Hash Function**: SHA-256 for ballot tracking
- **Proof System**: Standard zero-knowledge protocols

### Application Security

**Authentication**:
- CSRF protection on all POST endpoints (`check_csrf()`)
- Session-based authentication
- Password hashing with Django's default (PBKDF2)

**Authorization**:
- Decorators enforce access control
- Private elections restrict voter list visibility
- Admin actions require admin role

**Input Validation**:
- All user inputs validated
- HTML sanitized with `bleach.clean()`
- SQL injection prevented by ORM

**Email Privacy**:
- Opt-outs stored as hashed emails (not plaintext)
- Voters can unsubscribe from all election emails

**Audit Trail**:
- All admin actions logged in `ElectionLog`
- All votes stored in `CastVote` (immutable)
- IP addresses logged for abuse detection

### Deployment Security

**Recommendations**:
- HTTPS required (vote encryption assumes secure channel)
- Secure database access
- Firewall RabbitMQ (internal only)
- Regular security updates
- Monitor logs for suspicious activity

## Scalability Considerations

### Performance Characteristics

**Read-Heavy Operations**:
- Election viewing
- Voter authentication
- Ballot verification

**Write-Heavy Operations**:
- Vote casting (especially near deadline)
- Tallying (computation-intensive)

**Optimization Strategies**:
- Database indexes on lookup fields
- Caching election metadata
- Asynchronous task processing
- Web worker for client-side crypto

### Bottlenecks

**Tallying**:
- Homomorphic multiplication grows with vote count
- Mitigated by batch processing
- Typically completes in seconds to minutes

**Verification**:
- Proof verification per vote
- Asynchronous processing prevents blocking
- Can queue during high traffic

**Scaling Horizontally**:
- Django app servers: Scale with load balancer
- Celery workers: Add workers for task parallelism
- Database: PostgreSQL replication for read scaling

## Testing Architecture

### Test Organization

- `helios/tests.py` - Core election tests
- `helios_auth/tests.py` - Authentication tests
- `server_ui/tests.py` - Admin interface tests

### Test Tools

- `django.test.TestCase` - Django's test framework
- `django_webtest` - Functional testing with form interaction
- Fixtures in `helios/fixtures/` - Test data

### Running Tests

```bash
# All tests
python manage.py test -v 2

# Specific app
python manage.py test helios -v 2
python manage.py test helios_auth -v 2

# Specific test class
python manage.py test helios.tests.ElectionModelTests -v 2
```

### Test Coverage

Tests cover:
- Election lifecycle
- Vote casting and verification
- Cryptographic operations
- Tallying and decryption
- Authentication flows
- Access control

## Deployment Architecture

### Typical Deployment

```
Internet
  ↓
Load Balancer (HTTPS)
  ↓
Web Servers (Django + Gunicorn)
  ↓
Database (PostgreSQL)

Message Broker (RabbitMQ)
  ↓
Celery Workers
```

### Heroku Deployment

Helios includes Heroku-specific files:
- `Procfile` - Process types (web, worker)
- `runtime.txt` - Python version
- `requirements.txt` - Dependencies

### Docker Deployment

Can be containerized:
- Web container: Django app
- Worker container: Celery worker
- Database container: PostgreSQL
- Broker container: RabbitMQ

### Environment-Specific Configuration

- Development: `DEBUG=True`, local database, synchronous tasks
- Production: `DEBUG=False`, managed database, Celery workers

## Monitoring and Logging

### Application Logs

Django logging configuration:
- Console logging in development
- File/syslog logging in production
- Separate logs for: app, database, celery

### Metrics to Monitor

**Application**:
- Request rate and latency
- Error rate (500s)
- Database query performance

**Election-Specific**:
- Vote submission rate
- Verification queue length
- Tally computation time

**Infrastructure**:
- Database connections
- RabbitMQ queue depth
- Celery worker health

## Extending Helios

### Adding Authentication Systems

1. Create new module in `helios_auth/auth_systems/`
2. Inherit from `AuthenticationExpired`
3. Implement required methods: `do_auth`, `get_user_info_after_auth`, etc.
4. Add configuration in `settings.py`
5. Add to `AUTH_ENABLED_AUTH_SYSTEMS`

### Custom Election Types

Modify `Election.questions` JSON structure:
- Add new question types
- Update `heliosbooth` JavaScript to render
- Update tallying logic if needed

### Alternative Crypto Systems

Helios architecture allows swapping crypto:
- Replace `crypto/elgamal.py` with alternative
- Update proof generation in booth
- Update tallying workflow
- Ensure homomorphic property maintained

## Code Conventions

### Python Style

- **Indentation**: 2 spaces (not PEP 8's 4 spaces)
- **Naming**:
  - Boolean fields: `_p` suffix (`private_p`, `frozen_p`)
  - Datetime fields: `_at` suffix (`created_at`, `frozen_at`)
  - Functions: snake_case
  - Classes: PascalCase

### Import Organization

```python
# Standard library
import copy, csv, datetime

# Third-party
from django.db import models
import bleach

# Local
from helios import datatypes
from helios_auth.jsonfield import JSONField
```

### Model Conventions

All Helios models inherit from `HeliosModel`:
```python
class MyModel(HeliosModel):
  class Meta:
    app_label = 'helios'
```

### View Patterns

**JSON Response**:
```python
from helios.views import render_json
return render_json({'status': 'success'})
```

**Template Response**:
```python
from helios.views import render_template
return render_template(request, 'template.html', {'var': value})
```

## Summary

Helios is a sophisticated voting system built on:
- **Django** for web application structure
- **ElGamal cryptography** for homomorphic tallying
- **JavaScript** for client-side encryption
- **Celery** for asynchronous processing
- **PostgreSQL** for reliable data storage

The architecture prioritizes:
- **Security**: Cryptographic verification at every step
- **Transparency**: Complete audit trail and public verifiability
- **Usability**: Simple voter experience despite complex crypto
- **Flexibility**: Multiple auth systems, customizable elections
- **Scalability**: Asynchronous processing, horizontal scaling

This combination makes Helios suitable for a wide range of online voting needs, from small organization elections to large-scale academic governance.
