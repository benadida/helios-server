# Token-Based Voter Authentication
**Date:** 2026-01-04
**Status:** Implemented

## Overview

Single-token voter authentication replaces the traditional two-field system (voter ID + password) with a single 20-character token, simplifying the voting experience especially on mobile devices.

## Motivation

The original system requires voters to copy-paste two separate fields from their email:
- `voter_login_id`: A voter identifier
- `voter_password`: A 10-character password

Token-based auth consolidates this into one field with improved security (20 chars = ~117 bits of entropy vs 10 chars = ~59 bits).

## Architecture

### Database Schema

**Election Model:**
- `use_token_auth` (Boolean, default=False): Controls authentication method per election

**Voter Model:**
- `voting_token` (String, nullable): 20-character authentication token
- Unique constraint: `(election, voting_token)` ensures per-election uniqueness
- Original fields (`voter_login_id`, `voter_password`) remain for backward compatibility

### Token Specification

- **Length:** 20 characters
- **Character set:** `abcdefghjkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789`
- **Format:** Plain string (no dashes) for easy mobile copy-paste
- **Excludes:** Ambiguous characters (i, l, o, I, O, 0, 1)

### Authentication Flow

The system branches based on `Election.use_token_auth`:

**Token-Based (use_token_auth=True):**
1. Email contains single voting token
2. Voter enters token in one field
3. System validates against `Voter.voting_token`

**Password-Based (use_token_auth=False):**
1. Email contains voter_login_id and voter_password
2. Voter enters both credentials
3. System validates against both fields

### Implementation

**Models:**
- `Voter.generate_voting_token()`: Generates 20-character tokens
- `VoterFile.process()`: Conditional generation based on election setting

**Views:**
- `password_voter_login()`: Branches authentication logic based on `election.use_token_auth`

**Forms:**
- `VoterPasswordForm`: Contains fields for both methods (all optional)

**Templates:**
- Login form conditionally renders single token field OR dual ID/password fields
- Email templates show appropriate credentials based on election type

## Migration & Compatibility

**Default Behavior:**
- Existing elections: Continue using password-based auth (`use_token_auth=False`)
- New elections: Can opt into token-based auth via admin interface
- No automatic migration occurs

**Migration Path:**
Election administrators can either:
1. Keep existing elections on password-based auth indefinitely
2. Enable `use_token_auth=True` and re-send credentials with new tokens

**Deployment:**
- Single database migration adds two nullable fields
- Zero downtime, no data migration required
- All existing voter credentials remain valid

## Security

**Improvements:**
- 2× more entropy (20 chars vs 10)
- Database-enforced uniqueness per election

**Unchanged Security Model:**
- Plaintext storage in database
- Unencrypted email delivery
- No rate limiting or token expiration

Token-based auth maintains the existing security posture while improving entropy and user experience.

## Testing

- `test_create_token_voter`: Validates 20-character token generation
- `test_token_uniqueness_per_election`: Ensures per-election uniqueness
- Existing password tests continue passing without modification

## Usage

To enable for a new election:
1. Create election in admin interface
2. Set `use_token_auth = True`
3. Upload voter list
4. Voters receive email with single token and copy-paste instructions
