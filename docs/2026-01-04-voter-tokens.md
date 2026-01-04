# Token-Based Voter Authentication
**Date:** 2026-01-04
**Status:** Implemented

## Overview

This document describes the implementation of single-token voter authentication as an alternative to the traditional voter ID + password two-field authentication system in Helios.

## Motivation

The original authentication system requires voters to enter two separate credentials:
- `voter_login_id`: A voter identifier
- `voter_password`: A 10-character password

This creates friction for voters, especially on mobile devices where copy-pasting two separate fields can be cumbersome. The token-based system simplifies this to a single 20-character token that can be copied and pasted in one action.

## Design Goals

1. **Simplicity**: Single field authentication reduces voter confusion and errors
2. **Security**: Longer tokens (20 chars vs 10) provide better entropy
3. **Backward Compatibility**: Existing elections continue to work without modification
4. **Gradual Migration**: Election administrators can choose when to adopt token-based auth
5. **No Breaking Changes**: Both authentication methods coexist peacefully

## Architecture

### Database Schema

Two new fields were added:

**Election Model:**
- `use_token_auth` (Boolean, default=False): Controls which authentication method the election uses

**Voter Model:**
- `voting_token` (String, nullable): Stores the 20-character authentication token
- Unique constraint: `(election, voting_token)` ensures tokens are unique per election
- Original fields (`voter_login_id`, `voter_password`) remain unchanged

### Token Specification

**Properties:**
- Length: 20 characters
- Character set: `abcdefghjkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789`
  - Excludes ambiguous characters (i, l, o, I, O, 0, 1)
- Format: Plain string without dashes for easy mobile copy-paste
- Entropy: ~117 bits (vs ~59 bits for 10-character passwords)

### Authentication Flow

The system supports two authentication flows based on the `Election.use_token_auth` setting:

**Token-Based Flow (use_token_auth=True):**
1. Voter receives email containing single voting token
2. Voter visits election URL and enters token in single field
3. System validates token against `Voter.voting_token`
4. On success, voter session is established

**Password-Based Flow (use_token_auth=False - Legacy):**
1. Voter receives email containing voter_login_id and voter_password
2. Voter visits election URL and enters both credentials
3. System validates both fields against database
4. On success, voter session is established

### Component Updates

**Models (`helios/models.py`):**
- `Voter.generate_voting_token()`: New method to generate 20-character tokens
- `VoterFile.process()`: Conditionally generates token or password based on election setting

**Views (`helios/views.py`):**
- `password_voter_login()`: Updated to handle both authentication methods
- Authentication logic branches based on `election.use_token_auth`

**Forms (`helios/forms.py`):**
- `VoterPasswordForm`: Now contains fields for both auth methods
- All fields are optional; which fields are required depends on election type

**Templates:**
- Login form (`_castconfirm_password.html`): Conditionally renders single token field OR dual ID/password fields
- Email templates: Show token OR voter ID + password based on election setting
- Password resend templates: Adapted messaging for token-based elections

### Migration Strategy

**Default Behavior:**
- New elections: Can opt into `use_token_auth=True` via admin interface
- Existing elections: Continue using `use_token_auth=False` (password-based)
- In-progress elections: Completely unaffected

**Migration Path:**
Election administrators have two options:
1. Keep existing elections on password-based auth indefinitely
2. Manually enable token auth and re-send credentials to voters with new tokens

No automatic migration is performed to prevent disruption.

## Security Analysis

### Improved Security
- **Longer tokens**: 20 chars vs 10 chars provides 2× more entropy
- **Unique constraints**: Database enforces token uniqueness per election
- **Same security model**: Tokens use same plaintext storage as passwords (maintains existing security posture)

### Threat Model
The security model remains unchanged from the original system:
- Credentials stored as plaintext in database
- Credentials sent via unencrypted email
- No rate limiting on authentication attempts
- No expiration mechanism

Token-based auth does not introduce new vulnerabilities; it simply provides a better user experience with marginally improved entropy.

### Future Improvements (Out of Scope)
- Token expiration after election closes
- Rate limiting on login attempts
- One-time use tokens
- Encrypted storage

## Testing

**Test Coverage:**
- `test_create_token_voter`: Validates token generation
- `test_token_uniqueness_per_election`: Ensures tokens are unique per election
- Existing password-based tests continue to pass without modification

## Deployment Considerations

**Database Migration:**
- Single migration adds two fields (nullable)
- No data migration required
- Zero downtime deployment

**User Impact:**
- Existing voters: No changes to workflow
- New voters (token-based): Simplified single-field login
- Election administrators: Can choose auth method per election

## Usage

**For Election Administrators:**

To enable token-based authentication for a new election:
1. Create election via admin interface
2. Set `use_token_auth = True` on the Election object
3. Upload voter list as usual
4. System automatically generates 20-character tokens instead of passwords

Voters will receive emails with a single token field and instructions to copy-paste it.

## Backward Compatibility

Full backward compatibility is maintained:
- All existing elections continue using password-based auth
- All existing voter credentials remain valid
- No changes required to existing voter workflows
- Both authentication systems operate independently

## Summary

Token-based authentication provides a simpler, more secure alternative to the traditional two-field voter authentication system. The implementation maintains full backward compatibility while enabling election administrators to gradually adopt the improved authentication method for new elections.
