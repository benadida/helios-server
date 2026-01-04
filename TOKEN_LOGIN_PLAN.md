# Plan: Replace Voter ID + Password with Single Token Login

## Goal
Replace the current two-field authentication (voter_login_id + voter_password) with a single token that voters copy-paste from email. Support both methods to avoid breaking in-progress elections.

## Strategy
- Add `voting_token` field to Voter model (keep existing voter_login_id and voter_password)
- Add `use_token_auth` boolean field to Election model
- New elections default to token auth
- Existing elections continue using password auth
- Views/forms/templates adapt based on election setting

## Changes

### 1. Database - Add Fields

**Election Model** (`helios/models.py`, Election class, line ~300):
```python
use_token_auth = models.BooleanField(default=True)
```

**Voter Model** (`helios/models.py`, Voter class, line ~880):
```python
voting_token = models.CharField(max_length=100, null=True)
```

Update Voter Meta:
```python
class Meta:
  unique_together = (
    ('election', 'voter_login_id'),
    ('election', 'voting_token')
  )
```

Create migration to add both fields.

### 2. Model - Token Generation Method

**File:** `helios/models.py` (Voter class)

Add new method:
```python
def generate_voting_token(self, length=20):
  """Generate a 20-character voting token"""
  if self.voting_token:
    raise Exception("voting token already exists")

  self.voting_token = utils.random_string(
    length,
    alphabet='abcdefghjkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  )
```

Update `VoterFile.process()` (line ~843):
```python
# Change from:
voter.generate_password()

# To:
if voter.election.use_token_auth:
  voter.generate_voting_token()
else:
  voter.generate_password()
```

### 3. Login View - Support Both Auth Methods

**File:** `helios/views.py` (line ~666)

Update `password_voter_login()`:
```python
@election_view(allow_logins=True)
def password_voter_login(request, election):
  user = get_user(request)

  if request.method == "GET":
    return render_template(request, 'castconfirm', {
      'election': election,
      'user': user
    })

  check_csrf(request)

  # Token-based auth
  if election.use_token_auth:
    token_form = VoterPasswordForm(request.POST)
    if token_form.is_valid():
      try:
        voter = election.voter_set.get(
          voting_token=token_form.cleaned_data['voting_token'].strip()
        )
      except Voter.DoesNotExist:
        return render_template(request, 'castconfirm', {
          'election': election,
          'user': user,
          'error': 'Invalid voting token'
        })
  # Password-based auth (legacy)
  else:
    password_login_form = VoterPasswordForm(request.POST)
    if password_login_form.is_valid():
      try:
        voter = election.voter_set.get(
          voter_login_id=password_login_form.cleaned_data['voter_id'].strip(),
          voter_password=password_login_form.cleaned_data['password'].strip()
        )
      except Voter.DoesNotExist:
        return render_template(request, 'castconfirm', {
          'election': election,
          'user': user,
          'error': 'Invalid voter ID or password'
        })

  request.session['CURRENT_VOTER_ID'] = voter.id
  return HttpResponseRedirect(reverse('election@one-election-cast-confirm', args=[election.uuid]))
```

### 4. Login Form - Support Both Formats

**File:** `helios/forms.py` (line ~46)

Update to accept both formats:
```python
class VoterPasswordForm(forms.Form):
  # For token auth
  voting_token = forms.CharField(max_length=100, required=False, label="Voting Token")

  # For password auth (legacy)
  voter_id = forms.CharField(max_length=50, required=False, label="Voter ID")
  password = forms.CharField(max_length=100, required=False, label="Password")
```

### 5. Login Template - Dynamic Based on Election

**File:** `helios/templates/_castconfirm_password.html`

Update to show appropriate fields:
```html
{% if election.use_token_auth %}
  <!-- Token-based login -->
  <div class="form-group">
    <label for="voting_token">Voting Token:</label>
    <input
      type="text"
      name="voting_token"
      id="voting_token"
      class="form-control"
      placeholder="Enter your voting token"
      required
    />
    <small class="form-text text-muted">
      Copy and paste the token from your email.
    </small>
  </div>
{% else %}
  <!-- Password-based login (legacy) -->
  <div class="form-group">
    <label for="voter_id">Voter ID:</label>
    <input type="text" name="voter_id" id="voter_id" class="form-control" required />
  </div>
  <div class="form-group">
    <label for="password">Password:</label>
    <input type="password" name="password" id="password" class="form-control" required />
  </div>
{% endif %}

<button type="submit" class="btn btn-primary">Log In to Vote</button>
```

### 6. Email Templates - Dynamic Content

**File:** `helios/templates/email/vote_body.txt` (lines ~10-18)

Update to show appropriate credentials:
```django
{% if voter.election.use_token_auth %}
Your voting token:
  {{voter.voting_token}}

Copy and paste this token when prompted to log in.
{% else %}
Your voter ID: {{voter.voter_login_id}}
Your password: {{voter.voter_password}}
{% endif %}
```

**File:** `helios/templates/email/password_resend_body.txt`

Same change - conditional based on election.use_token_auth.

### 7. Password Resend View - Support Both

**File:** `helios/views.py` (line ~737)

Update `password_voter_resend()`:
```python
# For token-based elections, query by token
if election.use_token_auth:
  # Can lookup by email instead of voter_id for token elections
  voter_email = request.POST.get('email', '').strip()
  if voter_email:
    voter = Voter.get_by_election_and_email(election, voter_email)
else:
  # Keep existing voter_id lookup for password elections
  voter = Voter.get_by_election_and_voter_id(election, voter_id)
```

Add helper method to Voter model if needed:
```python
@classmethod
def get_by_election_and_email(cls, election, email):
  return cls.objects.get(election=election, voter_email=email)
```

### 8. Tests

**File:** `helios/tests.py`

Add tests for token auth:
```python
def test_token_voter_login(self):
  """Test voter login with token"""
  election = self.create_election()
  election.use_token_auth = True
  election.save()

  voter = self.create_voter(election)
  voter.generate_voting_token()
  voter.save()

  # Login with token
  response = self.client.post(
    reverse('election@password-voter-login', args=[election.uuid]),
    {'voting_token': voter.voting_token}
  )

  self.assertEqual(self.client.session.get('CURRENT_VOTER_ID'), voter.id)

def test_password_voter_login_legacy(self):
  """Test voter login with password (legacy)"""
  election = self.create_election()
  election.use_token_auth = False
  election.save()

  voter = self.create_voter(election)
  voter.voter_login_id = 'test123'
  voter.generate_password()
  voter.save()

  # Login with voter_id + password
  response = self.client.post(
    reverse('election@password-voter-login', args=[election.uuid]),
    {'voter_id': voter.voter_login_id, 'password': voter.voter_password}
  )

  self.assertEqual(self.client.session.get('CURRENT_VOTER_ID'), voter.id)
```

Update existing tests to set `use_token_auth` appropriately.

## Implementation Order

1. Add `use_token_auth` field to Election model + `voting_token` field to Voter model
2. Create migration
3. Add `generate_voting_token()` method to Voter model
4. Update `VoterFile.process()` to use conditional generation
5. Update login view to support both auth methods
6. Update login form (make fields optional)
7. Update login template with conditional display
8. Update email templates with conditional content
9. Update resend functionality
10. Add/update tests
11. Run all tests

## Migration Safety

- Existing elections: `use_token_auth = False` (keep using passwords)
- New elections: `use_token_auth = True` (default to tokens)
- In-progress elections: Not affected (continue using their auth method)
- No data loss: Both auth fields coexist

## Notes

- Token is 20 chars (vs 10 for password) = more secure
- Single copy-paste field for new elections = easier for voters
- Old elections continue working unchanged
- No breaking changes
- Clean migration path: old elections can be switched to tokens later if desired
