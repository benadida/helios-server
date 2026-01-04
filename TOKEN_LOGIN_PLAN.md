# Plan: Replace Voter ID + Password with Single Token Login

## Executive Summary

Replace the current two-field authentication (voter_login_id + voter_password) with a single secure token that voters can easily copy-paste from their email to cast votes.

## Current State Analysis

### Authentication Flow
- **Current:** Voters receive voter_login_id + voter_password (10 chars) via email
- **Login:** Must enter both fields in separate form inputs
- **Storage:** Both stored as plaintext in Voter model
- **Uniqueness:** `unique_together = (('election', 'voter_login_id'))`
- **Session:** After login, `CURRENT_VOTER_ID` stored in session

### Key Files Affected
| Component | File | Current Behavior |
|-----------|------|------------------|
| Voter Model | `helios/models.py:872-935` | Fields: voter_login_id, voter_password |
| Password Generation | `helios/models.py:1058-1062` | `generate_password(length=10)` |
| Login View | `helios/views.py:666-734` | `password_voter_login()` - queries both fields |
| Login Form | `helios/forms.py:46-48` | `VoterPasswordForm` - two fields |
| Login Template | `helios/templates/_castconfirm_password.html` | Two input fields |
| Email Templates | `helios/templates/email/vote_body.txt` | Shows voter_login_id + voter_password |
| Email Templates | `helios/templates/email/password_resend_body.txt` | Shows voter_login_id + voter_password |
| Resend View | `helios/views.py:737-794` | `password_voter_resend()` - requires voter_id |

---

## Proposed Solution

### Design Goals
1. **Single token authentication** - one field to copy-paste
2. **Maintain security** - token length ensures sufficient entropy
3. **Backward compatible** - support existing voters OR migration path
4. **Easy to use** - simple copy-paste from email
5. **Unique per voter** - one token per voter per election

### Token Specification
- **Length:** 32 characters (vs current 10 for password)
- **Format:** `xxxx-xxxx-xxxx-xxxx-xxxx-xxxx-xxxx-xxxx` (with dashes for readability)
- **Character set:** Same as current (no ambiguous chars: i, l, o, I, O, 0, 1)
- **Uniqueness:** Unique per election (database constraint)
- **Storage:** Plaintext in database (same security model as current)

### Database Schema Changes

#### Option A: Add New Field, Deprecate Old Fields (Recommended)
```python
class Voter(HeliosModel):
  # ... existing fields ...

  # NEW FIELD
  voting_token = models.CharField(max_length=100, null=True, unique=False)

  # DEPRECATED (kept for backward compatibility)
  voter_login_id = models.CharField(max_length=100, null=True)
  voter_password = models.CharField(max_length=100, null=True)

  class Meta:
    unique_together = (('election', 'voter_login_id'), ('election', 'voting_token'))
```

**Benefits:**
- Backward compatible with existing voters
- Gradual migration possible
- Can support both auth methods during transition

#### Option B: Replace Fields (Breaking Change)
```python
class Voter(HeliosModel):
  # ... existing fields ...

  # REPLACE voter_login_id and voter_password with:
  voting_token = models.CharField(max_length=100, null=True)

  class Meta:
    unique_together = (('election', 'voting_token'))
```

**Benefits:**
- Cleaner schema
- Forces migration
- No legacy code paths

**Recommendation:** Use Option A for safer deployment

---

## Implementation Plan

### Phase 1: Database & Model Changes

#### Task 1.1: Create Database Migration
**File:** New migration in `helios/migrations/`

**Changes:**
1. Add `voting_token` field to Voter model (nullable, max_length=100)
2. Add unique constraint: `('election', 'voting_token')`
3. Keep existing `voter_login_id` and `voter_password` fields for backward compatibility

**Migration Script:**
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('helios', 'XXXX_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='voter',
            name='voting_token',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='voter',
            unique_together={('election', 'voter_login_id'), ('election', 'voting_token')},
        ),
    ]
```

#### Task 1.2: Update Voter Model
**File:** `helios/models.py`

**Changes:**
1. Add `voting_token` field definition (line ~880)
2. Add method `generate_voting_token(length=32)` (similar to generate_password)
3. Update `unique_together` in Meta class
4. Optional: Add method `has_token_auth()` to check if voter uses token

**New Methods:**
```python
def generate_voting_token(self, length=32):
  """Generate a secure voting token (replaces voter_id + password)"""
  if self.voting_token:
    raise Exception("voting token already exists")

  # Generate 32-char token with dashes every 4 chars for readability
  raw_token = utils.random_string(
    length,
    alphabet='abcdefghjkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  )

  # Format: xxxx-xxxx-xxxx-xxxx-xxxx-xxxx-xxxx-xxxx
  self.voting_token = '-'.join([raw_token[i:i+4] for i in range(0, len(raw_token), 4)])

def has_token_auth(self):
  """Check if voter uses token authentication"""
  return self.voting_token is not None
```

---

### Phase 2: Voter Registration & Token Generation

#### Task 2.1: Update VoterFile Processing
**File:** `helios/models.py:811-870` (VoterFile.process method)

**Changes:**
1. Replace `voter.generate_password()` with `voter.generate_voting_token()`
2. Set `voter_login_id = None` and `voter_password = None` for new voters
3. Existing voters (with voter_login_id) remain unchanged

**Modified Code (line ~843):**
```python
# OLD:
voter.generate_password()

# NEW:
voter.generate_voting_token()  # Generate 32-char token instead
```

#### Task 2.2: Update Admin Voter Creation
**File:** Check if there are admin views for manually creating voters

**Changes:**
1. Ensure manual voter creation also uses token generation
2. Update any forms that create voters directly

---

### Phase 3: Authentication Views & Forms

#### Task 3.1: Create New Token Login View
**File:** `helios/views.py`

**New View (add after line 734):**
```python
@election_view(allow_logins=True)
def token_voter_login(request, election):
  """
  Login view for token-based voters (replaces password_voter_login)
  """
  user = get_user(request)

  if request.method == "GET":
    return render_template(request, 'castconfirm', {
      'election': election,
      'user': user
    })

  check_csrf(request)

  # Get token from form (strip whitespace and dashes for flexibility)
  token_form = VoterTokenForm(request.POST)

  if token_form.is_valid():
    voting_token = token_form.cleaned_data['voting_token'].strip().replace('-', '')

    # Query voter by token (with or without dashes)
    try:
      # Try exact match first
      voter = election.voter_set.get(voting_token=token_form.cleaned_data['voting_token'].strip())
    except Voter.DoesNotExist:
      # Try without dashes
      formatted_token = '-'.join([voting_token[i:i+4] for i in range(0, len(voting_token), 4)])
      try:
        voter = election.voter_set.get(voting_token=formatted_token)
      except Voter.DoesNotExist:
        return render_template(request, 'castconfirm', {
          'election': election,
          'user': user,
          'error': 'Invalid voting token'
        })

    # Set session
    request.session['CURRENT_VOTER_ID'] = voter.id

    # Redirect to vote confirmation
    return HttpResponseRedirect(reverse('election@one-election-cast-confirm', args=[election.uuid]))

  return render_template(request, 'castconfirm', {
    'election': election,
    'user': user,
    'error': 'Please enter a valid voting token'
  })
```

#### Task 3.2: Update password_voter_login View (Backward Compatibility)
**File:** `helios/views.py:666-734`

**Changes:**
1. Keep existing view for backward compatibility
2. Add fallback: if voter_login_id lookup fails, suggest token login
3. Update error messages

**Optional Enhancement:**
```python
# After line 710 (voter lookup fails)
except Voter.DoesNotExist:
  # Check if this election uses token-based voting
  if election.voter_set.filter(voting_token__isnull=False).exists():
    return render_template(request, '_castconfirm_password', {
      'election': election,
      'error': 'This election uses token-based voting. Please use your voting token instead.',
      'show_token_login': True
    })
  else:
    return render_template(request, '_castconfirm_password', {
      'election': election,
      'error': 'Invalid voter ID or password'
    })
```

#### Task 3.3: Create Token Login Form
**File:** `helios/forms.py`

**New Form (add after line 48):**
```python
class VoterTokenForm(forms.Form):
  voting_token = forms.CharField(
    max_length=100,
    label="Voting Token",
    widget=forms.TextInput(attrs={
      'placeholder': 'Enter your voting token',
      'autocomplete': 'off',
      'size': 40
    })
  )
```

#### Task 3.4: Update URL Routing
**File:** `helios/urls.py`

**Changes:**
1. Add route for token_voter_login
2. Keep password_voter_login for backward compatibility

**New Route:**
```python
path('elections/<uuid:election_uuid>/token-login', views.token_voter_login, name='election@token-voter-login'),
```

---

### Phase 4: Templates & UI

#### Task 4.1: Create Token Login Template
**File:** New file `helios/templates/_castconfirm_token.html`

**Content:**
```html
<div class="token-login-form">
  <h3>Enter Your Voting Token</h3>
  <p>Please enter the voting token from your email:</p>

  <form method="POST" action="{% url 'election@token-voter-login' election.uuid %}">
    {% csrf_token %}

    {% if error %}
    <div class="alert alert-danger">{{ error }}</div>
    {% endif %}

    <div class="form-group">
      <label for="voting_token">Voting Token:</label>
      <input
        type="text"
        name="voting_token"
        id="voting_token"
        class="form-control"
        placeholder="xxxx-xxxx-xxxx-xxxx-xxxx-xxxx-xxxx-xxxx"
        autocomplete="off"
        required
      />
      <small class="form-text text-muted">
        Copy and paste the token from your email. Dashes are optional.
      </small>
    </div>

    <button type="submit" class="btn btn-primary">Log In to Vote</button>
  </form>

  <p class="mt-3">
    <a href="{% url 'election@token-resend' election.uuid %}">Didn't receive your token?</a>
  </p>
</div>
```

#### Task 4.2: Update Main Cast Confirm Template
**File:** `helios/templates/castconfirm.html`

**Changes:**
1. Detect if election uses token auth or password auth
2. Include appropriate login template
3. Show both options during transition period (optional)

**Modified Logic:**
```django
{% if election.voter_set.filter(voting_token__isnull=False).exists %}
  {% include "_castconfirm_token.html" %}
{% else %}
  {% include "_castconfirm_password.html" %}
{% endif %}
```

#### Task 4.3: Update Password Login Template (Backward Compatibility)
**File:** `helios/templates/_castconfirm_password.html`

**Changes:**
1. Add link to token login if available
2. Update help text

---

### Phase 5: Email Templates

#### Task 5.1: Update Vote Notification Email
**File:** `helios/templates/email/vote_body.txt`

**Changes:**
Replace voter_login_id + voter_password section with single token

**Modified Section (lines 10-18):**
```django
{% if voter.voting_token %}
Your voting token:
  {{voter.voting_token}}

Copy and paste this token when prompted to log in.
{% elif voter.voter_type == "password" %}
Your voter ID: {{voter.voter_login_id}}
Your password: {{voter.voter_password}}
{% else %}
Log in with your {{voter.voter_type}} account.
{% endif %}
```

#### Task 5.2: Create Token Resend Email Template
**File:** New file `helios/templates/email/token_resend_subject.txt`
```
Your voting token for {{election.name}}
```

**File:** New file `helios/templates/email/token_resend_body.txt`
```django
Dear {{voter.name}},

You requested your voting token for the election "{{election.name}}".

Your voting token:
  {{voter.voting_token}}

Copy and paste this token when you visit the election URL:
{{election_vote_url}}

--
Helios

{% if unsubscribe_url %}
To stop receiving all emails from Helios, click here:
{{ unsubscribe_url }}
{% endif %}
```

#### Task 5.3: Update Password Resend Email (Backward Compatibility)
**File:** `helios/templates/email/password_resend_body.txt`

**Changes:**
1. Keep existing template
2. Add conditional for token-based voters

**Modified Content:**
```django
Dear {{voter.name}},

You requested your voting credentials for the election "{{election.name}}".

{% if voter.voting_token %}
Your voting token:
  {{voter.voting_token}}

Copy and paste this token when you visit the election URL:
{% else %}
Your voter ID: {{voter.voter_login_id}}
Your password: {{voter.voter_password}}

Use this election URL to prepare a new ballot if needed:
{% endif %}
{{election_vote_url}}

--
Helios

{% if unsubscribe_url %}
To stop receiving all emails from Helios, click here:
{{ unsubscribe_url }}
{% endif %}
```

---

### Phase 6: Token Resend Functionality

#### Task 6.1: Create Token Resend View
**File:** `helios/views.py`

**New View (add after password_voter_resend, line ~794):**
```python
@election_view(allow_logins=True)
def token_voter_resend(request, election):
  """
  Resend voting token to voter's email
  """
  if request.method == "GET":
    return render_template(request, 'token_resend', {'election': election})

  check_csrf(request)

  # Get voter email from form
  voter_email = request.POST.get('email', '').strip()

  if not voter_email:
    return render_template(request, 'token_resend', {
      'election': election,
      'error': 'Please enter your email address'
    })

  # Find voter by email and election
  try:
    voter = election.voter_set.get(voter_email=voter_email, voting_token__isnull=False)
  except Voter.DoesNotExist:
    # Don't reveal if email exists or not (security)
    return render_template(request, 'token_resend', {
      'election': election,
      'success': 'If your email is registered, you will receive your voting token shortly.'
    })
  except Voter.MultipleObjectsReturned:
    # Multiple voters with same email (shouldn't happen, but handle gracefully)
    return render_template(request, 'token_resend', {
      'election': election,
      'error': 'Multiple voters found with this email. Please contact the election administrator.'
    })

  # Send token via email
  election_vote_url = get_election_url(election)

  tasks.single_voter_email.delay(
    voter_uuid=voter.uuid,
    subject_template='email/token_resend_subject.txt',
    body_template='email/token_resend_body.txt',
    extra_vars={'election_vote_url': election_vote_url},
  )

  return render_template(request, 'token_resend', {
    'election': election,
    'success': 'If your email is registered, you will receive your voting token shortly.'
  })
```

#### Task 6.2: Create Token Resend Template
**File:** New file `helios/templates/token_resend.html`

**Content:**
```django
{% extends "base.html" %}

{% block content %}
<h2>Resend Voting Token</h2>
<p>Enter your email address to receive your voting token for <strong>{{election.name}}</strong>.</p>

{% if error %}
<div class="alert alert-danger">{{ error }}</div>
{% endif %}

{% if success %}
<div class="alert alert-success">{{ success }}</div>
{% else %}
<form method="POST">
  {% csrf_token %}
  <div class="form-group">
    <label for="email">Email Address:</label>
    <input
      type="email"
      name="email"
      id="email"
      class="form-control"
      placeholder="your.email@example.com"
      required
    />
  </div>
  <button type="submit" class="btn btn-primary">Send Token</button>
</form>
{% endif %}

<p class="mt-3">
  <a href="{% url 'election@one-election-view' election.uuid %}">Back to Election</a>
</p>
{% endblock %}
```

#### Task 6.3: Add Token Resend URL Route
**File:** `helios/urls.py`

**New Route:**
```python
path('elections/<uuid:election_uuid>/token-resend', views.token_voter_resend, name='election@token-resend'),
```

---

### Phase 7: Data Migration (Optional)

#### Task 7.1: Create Data Migration Script
**Purpose:** Migrate existing voters from password auth to token auth

**File:** New management command `helios/management/commands/migrate_to_tokens.py`

**Command:**
```python
from django.core.management.base import BaseCommand
from helios.models import Voter

class Command(BaseCommand):
  help = 'Migrate existing password voters to token-based authentication'

  def add_arguments(self, parser):
    parser.add_argument('--election-uuid', type=str, help='Migrate specific election only')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated')

  def handle(self, *args, **options):
    voters = Voter.objects.filter(voter_password__isnull=False, voting_token__isnull=True)

    if options['election_uuid']:
      voters = voters.filter(election__uuid=options['election_uuid'])

    self.stdout.write(f"Found {voters.count()} voters to migrate")

    if options['dry_run']:
      for voter in voters[:10]:
        self.stdout.write(f"  Would migrate: {voter.voter_login_id} ({voter.voter_email})")
      return

    migrated = 0
    for voter in voters:
      voter.generate_voting_token()
      voter.save()
      migrated += 1

      if migrated % 100 == 0:
        self.stdout.write(f"  Migrated {migrated} voters...")

    self.stdout.write(self.style.SUCCESS(f"Successfully migrated {migrated} voters"))
```

**Usage:**
```bash
# Dry run
python manage.py migrate_to_tokens --dry-run

# Migrate all voters
python manage.py migrate_to_tokens

# Migrate specific election
python manage.py migrate_to_tokens --election-uuid <uuid>
```

---

### Phase 8: Testing

#### Task 8.1: Update Existing Tests
**File:** `helios/tests.py`

**Tests to Update:**
1. `test_password_voter_login` - update to use token
2. `test_voter_creation` - verify token generation
3. `test_voter_email` - verify token in email content
4. Any tests that create voters with passwords

**Example Test Update:**
```python
# OLD
voter = Voter.objects.create(
  election=election,
  voter_login_id='voter123',
  voter_password='testpass',
  voter_email='test@example.com'
)

# NEW
voter = Voter.objects.create(
  election=election,
  voter_email='test@example.com'
)
voter.generate_voting_token()
voter.save()
```

#### Task 8.2: Add New Tests for Token Auth
**File:** `helios/tests.py`

**New Tests:**
```python
def test_token_generation(self):
  """Test voting token generation"""
  voter = self.create_test_voter()
  voter.generate_voting_token()

  # Check token format
  self.assertIsNotNone(voter.voting_token)
  self.assertEqual(len(voter.voting_token.replace('-', '')), 32)

  # Check uniqueness
  with self.assertRaises(Exception):
    voter.generate_voting_token()  # Should fail, token already exists

def test_token_voter_login(self):
  """Test voter login with token"""
  voter = self.create_test_voter()
  voter.generate_voting_token()
  voter.save()

  # Login with token
  response = self.client.post(
    reverse('election@token-voter-login', args=[self.election.uuid]),
    {'voting_token': voter.voting_token}
  )

  # Check session
  self.assertEqual(self.client.session.get('CURRENT_VOTER_ID'), voter.id)

def test_token_resend(self):
  """Test token resend functionality"""
  voter = self.create_test_voter()
  voter.generate_voting_token()
  voter.save()

  # Request token resend
  response = self.client.post(
    reverse('election@token-resend', args=[self.election.uuid]),
    {'email': voter.voter_email}
  )

  # Check email sent
  self.assertEqual(len(mail.outbox), 1)
  self.assertIn(voter.voting_token, mail.outbox[0].body)
```

#### Task 8.3: Manual Testing Checklist
- [ ] Create new election with token-based voters
- [ ] Upload voter CSV, verify tokens generated
- [ ] Send voter notification email, verify token displayed
- [ ] Login with token (with and without dashes)
- [ ] Cast vote successfully
- [ ] Request token resend, verify email received
- [ ] Test backward compatibility with existing password voters
- [ ] Test migration script on test database
- [ ] Verify email templates render correctly
- [ ] Test error messages (invalid token, etc.)

---

## Deployment Strategy

### Strategy A: Gradual Rollout (Recommended)

**Phase 1: Deploy Code (Backward Compatible)**
1. Deploy all changes with both auth methods enabled
2. Existing elections continue using password auth
3. New elections can choose token auth

**Phase 2: Migrate Existing Elections**
1. Run migration script on non-critical elections
2. Send new emails to voters with tokens
3. Monitor for issues

**Phase 3: Default to Token Auth**
1. Make token auth the default for new elections
2. Deprecate password auth (but keep code for legacy)

**Phase 4: Full Migration**
1. Migrate all remaining elections
2. Remove password auth code (optional, breaking change)

### Strategy B: Big Bang (Riskier)

**Phase 1: Deploy with Migration**
1. Deploy all changes
2. Run migration script immediately
3. Send emails to all voters with new tokens

**Risks:**
- Voters confused by credential change
- Email delivery issues affect all voters
- No rollback path

**Recommendation:** Use Strategy A for safer deployment

---

## Rollback Plan

If issues arise after deployment:

1. **Quick Fix:** Revert token login view, restore password login as default
2. **Database:** Keep both fields, so rollback doesn't lose data
3. **Email:** Password credentials still in database, can resend
4. **Code:** Use feature flag to toggle between auth methods

**Feature Flag Example:**
```python
# settings.py
USE_TOKEN_AUTH = get_from_env('USE_TOKEN_AUTH', 'False') == 'True'

# views.py
if USE_TOKEN_AUTH:
  return token_voter_login(request, election)
else:
  return password_voter_login(request, election)
```

---

## Security Considerations

### Token Length & Entropy
- **32 characters** with 57-character alphabet = ~188 bits of entropy
- **Current:** 10 characters = ~59 bits of entropy
- **Improvement:** 3x more secure against brute force

### Token Format Benefits
- **Dashes:** Improve readability, reduce copy-paste errors
- **No ambiguous chars:** Prevent confusion (i/I/l/1, o/O/0)
- **Case-sensitive:** Increases entropy

### Potential Vulnerabilities
- **Email interception:** Same risk as current system (plaintext credentials in email)
- **Token replay:** No expiration on tokens (same as current passwords)
- **Brute force:** Database-level rate limiting needed (not in current system)

### Future Enhancements (Out of Scope)
- Token expiration (e.g., 24 hours after election starts)
- One-time use tokens (revoke after first vote)
- Rate limiting on login attempts
- HTTPS enforcement for voting URLs

---

## Migration Impact Assessment

### Database
- **Change:** Add 1 field, modify 1 constraint
- **Downtime:** Zero (nullable field, no data migration required immediately)
- **Size:** Minimal (~100 bytes per voter)

### Code
- **Files Modified:** ~10 files
- **Lines Changed:** ~500 lines (mostly new code, minimal deletions)
- **Breaking Changes:** None if backward compatibility maintained

### User Experience
- **Voters:** Simpler login (1 field instead of 2)
- **Admins:** No changes to workflow
- **Email:** Slightly shorter, clearer

### Performance
- **Login Query:** Same complexity (indexed field lookup)
- **Token Generation:** Slightly slower (longer string), negligible impact
- **Email Rendering:** No change

---

## Open Questions & Decisions Needed

1. **Migration Timing:** When should existing voters be migrated?
   - Option A: Automatically on next voter file upload
   - Option B: Manual admin action per election
   - Option C: Background job over time

2. **Token Format:** Keep dashes or remove?
   - **Pros (keep):** Readability, less error-prone
   - **Cons:** Extra characters, potential paste issues

3. **Backward Compatibility Duration:** How long to support password auth?
   - Option A: Forever (minimal cost)
   - Option B: 1 release cycle, then deprecate
   - Option C: Immediate removal (breaking)

4. **Token Resend:** Require email or allow voter_id lookup?
   - **Current Plan:** Email only (more private)
   - **Alternative:** Show voter_id in UI, allow lookup

5. **Email Subject Line:** Change to mention "token" instead of "password"?
   - Current: "Your voting credentials for {{election.name}}"
   - Proposed: "Your voting token for {{election.name}}"

6. **Token Display:** Show in admin UI for debugging?
   - **Pro:** Easier voter support
   - **Con:** Security risk if admin account compromised

---

## Success Metrics

How to measure if the change is successful:

1. **User Experience:**
   - Reduced login errors (target: 50% reduction)
   - Faster login time (target: 30% faster)
   - Fewer "forgot credentials" requests (target: 25% reduction)

2. **Technical:**
   - Zero increase in login failures
   - No database performance degradation
   - Successful migration of 100% of voters

3. **Support:**
   - Reduced voter support tickets related to login
   - Positive feedback from election administrators

---

## Timeline Estimate (If Approved)

**Implementation:** ~2-3 days of focused development

- Phase 1 (Database): 2 hours
- Phase 2 (Models): 2 hours
- Phase 3 (Views): 4 hours
- Phase 4 (Templates): 3 hours
- Phase 5 (Emails): 2 hours
- Phase 6 (Resend): 2 hours
- Phase 7 (Migration): 2 hours
- Phase 8 (Testing): 8 hours

**Total:** ~25 hours of development + testing

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Make decisions** on open questions above
3. **Approve implementation** approach (Strategy A vs B)
4. **Begin Phase 1** (database migration creation)
5. **Iterative testing** after each phase

---

## Summary

This plan provides a comprehensive, backward-compatible approach to replacing voter ID + password authentication with a single token system. The design prioritizes:

- **Usability:** Single copy-paste field
- **Security:** Longer tokens with better entropy
- **Safety:** Backward compatible, gradual rollout
- **Maintainability:** Clean code, clear migration path

**Recommendation:** Proceed with Strategy A (gradual rollout) to minimize risk while modernizing the authentication system.
