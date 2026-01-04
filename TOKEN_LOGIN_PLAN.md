# Plan: Replace Voter ID + Password with Single Token Login

## Goal
Replace the current two-field authentication (voter_login_id + voter_password) with a single token that voters copy-paste from email.

## Changes

### 1. Database - Add Token Field
**File:** `helios/models.py` (Voter model, line ~880)

Add field:
```python
voting_token = models.CharField(max_length=100, null=True)
```

Update Meta:
```python
class Meta:
  unique_together = (('election', 'voting_token'))
```

Create migration to add the field.

### 2. Model - Generate Tokens Instead of Passwords
**File:** `helios/models.py`

Replace `generate_password()` usage with:
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
voter.generate_voting_token()
```

### 3. Login View - Accept Token Instead of ID + Password
**File:** `helios/views.py` (line ~666)

Update `password_voter_login()` to accept single token field:
```python
# Change voter lookup from:
voter = election.voter_set.get(
  voter_login_id=form.cleaned_data['voter_id'],
  voter_password=form.cleaned_data['password']
)

# To:
voter = election.voter_set.get(
  voting_token=form.cleaned_data['voting_token'].strip()
)
```

### 4. Login Form - Single Token Field
**File:** `helios/forms.py` (line ~46)

Replace `VoterPasswordForm` with:
```python
class VoterPasswordForm(forms.Form):
  voting_token = forms.CharField(max_length=100, label="Voting Token")
```

### 5. Login Template - Single Input Field
**File:** `helios/templates/_castconfirm_password.html`

Replace two input fields (voter_id, password) with single field:
```html
<input type="text" name="voting_token" placeholder="Enter your voting token" />
```

### 6. Email Templates - Show Token Only
**File:** `helios/templates/email/vote_body.txt` (lines ~10-18)

Replace:
```
Your voter ID: {{voter.voter_login_id}}
Your password: {{voter.voter_password}}
```

With:
```
Your voting token: {{voter.voting_token}}

Copy and paste this token when prompted to log in.
```

**File:** `helios/templates/email/password_resend_body.txt`

Same change - show token instead of ID + password.

### 7. Password Resend View
**File:** `helios/views.py` (line ~737)

Update `password_voter_resend()` to work with tokens:
- Keep email-based lookup
- Send token instead of voter_id + password

### 8. Tests
**File:** `helios/tests.py`

Update all tests that create voters:
```python
# Change from:
voter.voter_login_id = 'test123'
voter.voter_password = 'testpass'

# To:
voter.generate_voting_token()
```

Update login tests to use single token field.

## Implementation Order

1. Add `voting_token` field to model + create migration
2. Add `generate_voting_token()` method
3. Update `VoterFile.process()` to use new method
4. Update login view to query by token
5. Update login form to single field
6. Update login template
7. Update email templates
8. Update resend functionality
9. Update tests
10. Run tests

## What Gets Removed

- `voter_login_id` field (after migration)
- `voter_password` field (after migration)
- `generate_password()` method
- Two-field login form

## Notes

- Token is 20 chars (vs 10 for old password) = more secure
- Single copy-paste field = easier for voters
- No dashes in token = simpler (users can copy exact string)
- Same security model (plaintext in DB, sent via email)
