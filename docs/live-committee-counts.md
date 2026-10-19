# Live committee counts

The authorized management `stats` response can now include `counts_status: live`, an aggregate per position/candidate, the number of verified ballots included and a UTC snapshot timestamp. The dashboard polls every five seconds while visible. These are preliminary counts, not published results.

Only ballots already verified and stored as the voter's counted vote contribute. Pending, invalid and unreleased quarantined submissions do not contribute. A temporary homomorphic aggregate is decrypted; individual voter ciphertexts are not decrypted separately. The native encrypted tally, trustee contributions, election status, final result and audit history are not modified by monitoring.

The existing fresh committee authorization runs before every management response, including cache hits. Public ballot/result endpoints and the student page do not expose these provisional counts. Any pending ballot policy review suppresses candidate counts. Final policy checks and the normal closing tally remain authoritative. Live snapshots do not independently repeat the entire remote eligibility check for every previously verified voter.

All frozen trustee keys must already be held by this server and match the complete election key. External trustee contributions are never bypassed or manufactured; elections with externally held keys show turnout and wait for their normal tally. A missing/mismatched key or failed aggregate proof does not produce invented zero counts.

The process cache stores only a snapshot, encrypted aggregate and internal vote-id/hash metadata for up to five minutes. Each refresh compares one small DB-computed revision digest. New verified ballots extend the encrypted aggregate; a changed/removed earlier counted ballot rebuilds it. A restart/cache miss rebuilds from stored ciphertext choices, excluding large proofs and identity details from the SQL projection. This requires no schema migration or separate cache service.

## Secrecy tradeoff

This intentionally changes the previous rule that candidate totals remain hidden until voting ends. A committee observer can compare successive snapshots; a change after a small number of arrivals may disclose the newly added preferences. It must not be described as preserving the same secrecy as withholding all totals until closing. No voter-to-choice list is returned, but exact live aggregates cannot guarantee that individual preferences are uninferable.

## Validation

Local real-crypto tests cover A=10/B=2, a blank position, pending verification, aggregate reuse, read-only election/trustee state, private endpoints, pending policy holds, missing external keys and crypto failure. Final tally/publication regression tests remain enabled. No production data was read or changed for this work, and nothing was deployed.
