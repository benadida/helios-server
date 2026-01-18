# Enhanced NIZK Proof Context Binding

## Overview

Starting with datatype version `2026/01/Election`, Helios uses enhanced Non-Interactive Zero-Knowledge (NIZK) proofs that cryptographically bind each proof to its specific context within an election. This prevents proof transplantation attacks where proofs could theoretically be reused across different elections, questions, or voters.

## Security Enhancement

### Previous Behavior (legacy, 2011/01)

In earlier versions, the Fiat-Shamir challenge generation only hashed the commitment values:

```
challenge = SHA1(commitment.A + "," + commitment.B)
```

This created a potential vulnerability where proofs generated for one context could theoretically be verified in a different context.

### New Behavior (2026/01+)

The enhanced proof system includes context information in the challenge hash:

```
challenge = SHA256(
    "election:{election_hash}|question:{question_index}|answer:{answer_index}|voter:{voter_alias}" +
    "," + commitment.A + "," + commitment.B
) mod q
```

**Important**: The SHA-256 hash result is reduced modulo `q` (the subgroup order). This is necessary because SHA-256 produces 256-bit output which can exceed `q`, unlike SHA-1's 160-bit output which is always less than the typical 256-bit `q`.

## Key Changes

### 1. Hash Algorithm Upgrade
- **From**: SHA-1 (160-bit)
- **To**: SHA-256 (256-bit), reduced mod q

SHA-256 provides stronger collision resistance and is the current industry standard for cryptographic hashing.

### 2. Context Binding

Each proof is bound to:

| Field | Purpose |
|-------|---------|
| `election_hash` | Binds proof to the specific election definition (all questions, answers, crypto params) |
| `question_index` | Binds proof to the specific question within the election |
| `answer_index` | Binds individual proofs to specific answer options |
| `voter_alias` | Binds proofs to the specific voter's ballot (prevents cross-voter proof reuse) |

## Implementation Details

### Context String Format

The context is serialized as a deterministic string:

```
election:{hash}|question:{index}|answer:{index}|voter:{alias}
```

Example:
```
election:abc123def456|question:0|answer:1|voter:v42
```

For overall (sum) proofs, the answer index is set to "overall":
```
election:abc123def456|question:0|answer:overall|voter:v42
```

### Python Usage

```python
from helios.crypto.algs import ProofContext, make_context_bound_challenge_generator

# Create context for an individual proof
context = ProofContext(
    election_hash=election.hash,
    question_index=0,
    answer_index=1,
    voter_alias="voter42"
)

# Get a challenge generator bound to this context
# Note: q must be passed to reduce the SHA-256 hash mod q
challenge_gen = make_context_bound_challenge_generator(context, q=pk.q)

# Use in proof generation
proof = ciphertext.generate_disjunctive_encryption_proof(
    plaintexts, index, randomness, challenge_gen
)
```

### JavaScript Usage

```javascript
// Create context
var context = new ElGamal.ProofContext(
    election.get_hash(),  // election_hash
    0,                    // question_index
    1,                    // answer_index
    "voter42"            // voter_alias
);

// Get a challenge generator bound to this context
// Note: pk.q must be passed to reduce the SHA-256 hash mod q
var challengeGen = ElGamal.make_context_bound_challenge_generator(context, pk.q);

// Use in proof generation
var proof = ciphertext.generateDisjunctiveProof(
    plaintexts, index, randomness, challengeGen
);
```

## Backward Compatibility

The system maintains full backward compatibility:

1. **Existing Elections**: Elections with `datatype="legacy/Election"` or `datatype="2011/01/Election"` continue to use SHA-1 proofs without context binding.

2. **Version Detection**: The system checks `election.datatype.startswith('2026/')` to determine which proof algorithm to use.

3. **Verification**: When verifying proofs, the same datatype check determines which challenge generator to use.

## Configuration

### Default Datatype for New Elections

Set in `settings.py`:

```python
# Use enhanced proofs for new elections
HELIOS_DEFAULT_ELECTION_DATATYPE = '2026/01/Election'

# Or use legacy for compatibility
HELIOS_DEFAULT_ELECTION_DATATYPE = 'legacy/Election'
```

Environment variable:
```bash
export HELIOS_DEFAULT_ELECTION_DATATYPE='2026/01/Election'
```

## Migration

### No Migration Required

Existing elections maintain their original `datatype` and continue to work with the legacy verification algorithm. There is no need to migrate existing elections.

### New Elections

All newly created elections will automatically use the `2026/01/Election` datatype and enhanced proofs (unless configured otherwise).

## Testing

Run the context binding tests:

```bash
uv run python manage.py test helios.tests.ContextBoundProofTests -v 2
```

## Security Considerations

### Attack Prevention

The context binding prevents:

1. **Cross-election proof reuse**: A proof from election A cannot verify in election B
2. **Cross-question proof reuse**: A proof for question 0 cannot verify for question 1
3. **Cross-answer proof reuse**: A proof for answer 0 cannot verify for answer 1
4. **Cross-voter proof reuse**: A proof from voter A cannot verify for voter B

### Cryptographic Strength

- SHA-256 provides 256 bits of output (128-bit security against collision attacks)
- Context prefix ensures domain separation between different proof contexts
- Deterministic context serialization ensures consistent verification

## File Reference

| File | Description |
|------|-------------|
| `helios/crypto/algs.py` | `ProofContext` class and SHA-256 challenge generators |
| `helios/crypto/elgamal.py` | SHA-256 challenge generators |
| `helios/workflows/homomorphic.py` | Context-aware proof generation and verification |
| `helios/datatypes/2026/01.py` | 2026/01 datatype definitions |
| `helios/media/helios/jscrypto/elgamal.js` | JavaScript SHA-256 generators and ProofContext |
| `helios/media/helios/jscrypto/helios.js` | JavaScript context-aware encryption |
| `settings.py` | `HELIOS_DEFAULT_ELECTION_DATATYPE` configuration |
