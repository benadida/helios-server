# Helios Election Protocol v4

## Introduction

Helios is a truly verifiable voting system, which means that:

* Alice can verify that her vote was correctly captured,
* all captured votes are displayed (in encrypted form) for all to see.
* anyone can verify that the captured votes were correctly tallied.

This document specifies data formats and verification protocols. Using
this document, it should be possible to build a complete verification
program in any modern programming language. For the sake of
concreteness, instead of pseudo-code, we use Python.

## Audit Data

Election data is accessible using an HTTP API. Consider an election
with election id `<ELECTION_ID>`. Given a web origin `{HELIOS_HOST}`,
the election core data structure can be retrieved at:

    {HELIOS_HOST}/elections/<ELECTION_ID>

The list of voters, denoted `<VOTER_LIST>`, is available at:

    {HELIOS_HOST}/elections/<ELECTION_ID>/voters/

Given this list, it is possible to extract individual voter
identifiers, denoted `<VOTER_ID>`.

The list of cast ballots is available at, with each ballot including
the <VOTER_ID> that it corresponds to:

    {HELIOS_HOST}/elections/<ELECTION_ID>/ballots/

Ballots are provided in chronological (oldest to newest)
order, and takes optional parameters limit and after.

The list of all ballots cast by a voter is:

    {HELIOS_HOST}/elections/<ELECTION_ID>/ballots/<VOTER_ID>/all

For convenience, the last cast ballot is:

    {HELIOS_HOST}/elections/<ELECTION_ID>/ballots/<VOTER_ID>/last

The result of an election is available at:

    {HELIOS_HOST}/elections/<ELECTION_ID>/result

Every election has trustees (sometimes just one), and the list of trustees, including each trustee's public key and key validity proof:

    {HELIOS_HOST}/elections/<ELECTION_ID>/trustees/

NOT YET IMPLEMENTED:

The trustee's robustness information (e.g. Lagrange coeff) is at:

    {HELIOS_HOST}/elections/<ELECTION_ID>/trustees/<TRUSTEE_ID>/robustness_factor

## Data Formats

All data made available by Helios is in JavaScript Object Notation
(JSON) format. Where previous versions of Helios assumed the ability
to canonicalize JSON with alphabetically ordered keys, Helios v4 does
not: when a data structure is intended to be hashed for inclusion in
cryptographic protocols, that data structure must be serialized as a
string and provided to the other party as is. For example, a cast
ballot is one possible JSON serialization of its abstract data
structure, not a canonical one.

### Basic Cryptographic Datatypes

All large integers are represented as base64 strings. An El-Gamal
public-key is then a dictionary of expected big-integer values:

```
<ELGAMAL_PUBLIC_KEY>
{"p": "mN3xc34", "q": "J3sRtxcwqlert", "g": "Hbb3mx34sd", "y": "U8cnsvn45234wsdf"}
```

An El-Gamal ciphertext is then:

```
<ELGAMAL_CIPHERTEXT>
{"alpha": "6BtdxuEwbcs+dfs3", "beta": "nC345Xbadw3235SD" }
```

All ciphertexts are Exponential ElGamal, so `alpha = g^r mod
p`, and `beta = g^m y^r mod p`.

All hash values are base-64 encoded, and the hashing
algorithm is always SHA256:

`{"election_hash": "c0D1TVR7vcIvQxuwfLXJHa5EtTHZGHpDKdulKdE1oxw"}`

### Voter

A single voter in Helios is represented using a few fields that
identify the voter.

```
<VOTER>
{"uuid": "60435862-65e3-11de-8c90-001b63948875", "name": "Ben Adida", "voter_id": "benadida@gmail.com", "voter_type": "email"}
```

Together, the type and id identify the voter via some external
authentication mechanism. In the example above, this is a user whose
email address is `benadida@gmail.com`. Another example might be:

```
<VOTER>
{"uuid": "4e8674e2-65e3-11de-8c90-001b63948875", "name": "Ben Adida", "voter_id": "ben@adida.net", "voter_type": "email"}
```

where this is a voter identified by the email address `ben@adida.net`.

The `uuid` field is used as a reference key within Helios.

Voters may be identified by OpenID URL rather than email address, in which case their JSON representation is:

```
<VOTER>
{"uuid": "4e8674e2-65e3-11de-8c90-001b63948875", "name": "Ben Adida", 
 "voter_id": "http://benadida.myopenid.com", "voter_type": "openid"}
```

Other fields may be present in a <VOTER> data structure,
e.g. category. These do not affect the cryptographic processing, but
if present, they become part of the hash of the voter list.

#### Protecting Voter Privacy

In order to protect voter privacy, Helios can obfuscate the
`voter_id`, especially when that `voter_id` is an email address. This
protection is not meant to resist a powerful attacker with other
knowledge about the voter, but mostly to prevent email-address
crawlers. In this case, a voter can be represented with the field
`voter_id_hash` replacing `voter_id`. The hash is SHA256.

```
<VOTER>
{"uuid": "60435862-65e3-11de-8c90-001b63948875", "name": "Ben Adida", "voter_id_hash": "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU", "voter_type": "email"}
```

### Voter Aliases

In some elections, it may be preferable to never reveal the identity
of the voters. This is particularly applicable when organizers are
worried about votes being decryptable in 30+ years, when cryptographic
advances make today's algorithms weaker. An election may thus publish
only:

```
<ALIASED_VOTER>
{"uuid": "b7dbd90a-65e3-11de-8c90-001b63948875", "alias": "voter_123"}
```

An aliased voter still has a UUID, so it can still be referred appropriately in the rest of the system.

### Casting a Vote

Once a voter has cast a ballot, the encrypted vote representation is then:

```
<CAST_VOTE>
{"voter_uuid": "b7dbd90a-65e3-11de-8c90-001b63948875", "voter_hash": "2bxksdlkxnsdf", 
 "cast_at": "2009-07-15 12:23:46", "vote": <VOTE>, "vote_hash": "8bncn23nsfsdk234234"}

`cast_at` is the timestamp of the cast vote in UTC.

We describe the details of the `<VOTE>` data structure later in this document, once we have described all of the required components.

`vote_hash` is available to enable a shorter version of this data structure:

```
<SHORT_CAST_VOTE>
{"voter_uuid": "b7dbd90a-65e3-11de-8c90-001b63948875", "vote_hash": "c0D1TVR7vcIvQxuwfLXJHa5EtTHZGHpDKdulKdE1oxw",
 "cast_at": "2009-07-15 12:23:46", "voter_hash": "2bxksdlkxnsdf", }
```

where only the hash and not the full vote is listed.

### Election

An election is represented as:

```
<ELECTION>
{"cast_url": "https://heliosvoting.org/cast/",
 "description": "... blah blah blah ... info about the election",
 "frozen_at": null,
 "name": "Student President Election at Foo University 2010",
 "openreg": false, "public_key": <ELGAMAL_PUBLIC_KEY>,
 "questions": <QUESTION_LIST>,
 "short_name": "fooprez2010",
 "use_voter_aliases": false,
 "uuid": "1882f79c-65e5-11de-8c90-001b63948875",
 "voters_hash": "G6yS/dAZm5hKnCn5cRgBGdw3yGo"}
``

`short_name`, `name`, and `description` describe the election. The
short name must be a few characters without a space (almost like a
database key), the name can be a long string, and the description is
an even longer description of the election.

`cast_url` indicates the URL where ballots for this election should be
cast. `frozen_at` indicates the timestamp at which this election was
frozen. It remains null until the election is frozen.

`openreg` indicates whether voters can be added to the list after the
election has started.

`use_voter_aliases` indicates whether this election aliases its voters.

`uuid` is a unique identifier for the election, and name is the election's name.

`<ELGAMAL_PUBLIC_KEY>` is, as detailed earlier, the JSON data structure that represents an El-Gamal public key.

`<QUESTION_LIST>` is a data structure that represents the list of questions and available answers to those questions.

```
<QUESTION_LIST>
[<QUESTION>, <QUESTION>, ...]
```

and a single question is a JSON object:

```
<QUESTION>
{"answer_urls": ["http://example.com/alice", null], "answers": ["alice", "bob"], "choice_type": "approval", "max": 1, "min": 0,
 "result_type": "absolute", "question": "Who Should be President?", "short_name": "President", "tally_type": "homomorphic"}
```

which, in this case, contains two possible answers (alice and bob),
URLs that describe these answers in greater detail, the text of the
question, and a short name for the question. The parameter max
indicates the maximum number of options that a voter can select, most
often 1. The parameter min indicates the minimum number of options
that a voter must select, most often 0. Note how, given that max and
min should be small integers, they are in fact serialized as integers,
not as strings. choice_type indicates the kind of question, for now
just approval (possibly with a maximum number of choices). If max is
null, then it's approval voting for as many candidates as
desired. tally_type indicates how the question is tallied,
e.g. homomorphic or mixnet.

`voters_hash` is the hash of the list of voters for the election. The
list of voters is a JSON array of `<VOTER>` data structures. For
example, a list of voters might be:

```
<VOTER_LIST> (example)
[{"id": "benadida@gmail.com", "name": "Ben Adida", "type": "email", "uuid": "60435862-65e3-11de-8c90-001b63948875"}, {"id": "ben@adida.net", "name": "Ben2 Adida", "type": "email", "uuid": "4e8674e2-65e3-11de-8c90-001b63948875"}]
```

#### Open Registration

Helios supports "open registration elections", when the election
administrator so desires. In those elections, the voter list is not
set ahead of time. In that case, an election data structure contains a
null voters_hash, and sets openreg to true.

#### Election Fingerprint

Once an election is ready to be used for voting, the administrator
freezes the election, at which point Helios prevents changing any of
the question parameters and voter registration settings: an open
election remains an open election, and a closed election remains
closed with a fixed voter list. The frozen_at field then indicates the
timestamp at which the election was frozen.

Such a frozen election can be designated by its Helios Election
Fingerprint, which is the hash of the JSON election data structure
(with properly alphabetized field names, as always). Note how this
fingerprint depends on the list of voters if the election registration
status is closed, but not if it is open. In any case, this fingerprint
does not depend on any cast vote or cast-vote hash.

### Vote

A vote contains a list of encrypted answers, and a reference to the
election, both by ID (for convenience) and by hash (for integrity.)
The hash is the election fingerprint just described.

```
<VOTE>
{"answers": [<ENCRYPTED_ANSWER>, <ENCRYPTED_ANSWER>, ...], "election_hash": "Nz1fWLvVLH3eY3Ox7u5hxfLZPdw", "election_uuid": "1882f79c-65e5-11de-8c90-001b63948875"}
```

Each "encrypted answer" corresponds to one election question: it
contains a list of ciphertexts (one for each possible choice for that
question), a list of corresponding proofs that the ciphertext is
correctly formed, and an overall proof that all of the ciphertexts for
that election question, taken together, are correctly formed.

```
<ENCRYPTED_ANSWER>
{"choices": [<ELGAMAL_CIPHERTEXT>, <ELGAMAL_CIPHERTEXT>, ...], "individual_proofs": [<ZK_PROOF_0..1>, <ZK_PROOF_0..1>, ...], "overall_proof": <ZK_PROOF_0..max>}
```

The value of `max` in overall_proof matches the value of `max` in the
election's question definition.

For approval voting questions, the `overall_proof` is absent.

When a voter generates a ballot, Helios provides the ballot
fingerprint, which is the base64-encoding of the SHA256 hash of the
`<VOTE>` data structure defined above.

### Proofs

A zero-knowledge proof, denoted `<ZK_PROOF_0..max>`, is a transcript of
a non-interactive proof that the corresponding ciphertext encodes an
integer value between 0 and max. For the overall proof, the ciphertext
whose value is being proven to be between 0 and max is the homomorphic
sum (element-wise product) of the choices ciphertexts.

In Helios, all `0..max` proofs are disjunctive proofs (CDS & CP),
meaning that the transcript includes `max+1` proofs, one for each
possible value of the plaintext, `0` through `max`. The `max+1` individual
challenges must sum up to the single actual protocol challenge, which
ensures that one of the proofs is real (while the others are
simulated.)

```
<ZK_PROOF_0..max>
[<ZK_PROOF(0)>, <ZK_PROOF(1)>, ..., <ZK_PROOF(max)>]
```

A single ZK proof is then composed of three messages: the commitment,
the challenge, and the response. Since the proof is a Chaum-Pedersen
proof of a DDH tuple, the commitment is composed of two values, A and
B. Thus, a ZK proof is:

```
<ZK_PROOF(plaintext)>
{"challenge": "2342342", "commitment": {"A": "28838", "B": "9823723"}, "response": "970234234"}
```

The commitment is optional, since these types of proofs can be checked
with just the challenge and response, which cuts down the size of a
proof significantly. This is doable because the commitment values A
and B should be recoverable as:

```
A = g^response / alpha^challenge
B = y^response / (beta/g^m)^challenge
```

at which point those values can be used in the proof
verification. Effectively, we do more computation in exchange for a
much smaller proof, since A and B are in the full group, while
challenge and response are in the subgroup.

#### Proof Robustness

In prior versions of Helios, the proofs were generated using
Fiat-Shamir with very little context, which makes an individual proof
easily exchangeable with another. This is bad for security proofs (and
for actual security, not coincidentally). So, to generate a challenge
in a Fiat-Shamir'ized proof, we now include a lot more context.

First, to generate a challenge in general, we now create a JSON data
structure, with the same strictness as our other JSON data structures
(alphabetized keys, no extra spaces), that contains all the fields we
want for context.

In the Proof of Knowledge of a Secret Key, we include: `election_uuid`,
`trustee_email`.

In the single-choice proof inside a valid ballot, we include:
`election_hash`, `question_num`, `choice_num`, `ciphertext` (in JSON format).

In the overall proof inside a valid ballot, we include: `election_hash`,
`question_num`, `ciphertext`, where the ciphertext is the homomorphic
combination of all the choice ciphertexts.

In the proof of decryption, we include: `ciphertext`, `election_hash`, `trustee_email`.

For example, in a single-choice proof, this is the string we hash (extra spacing for readability only):

```
{"A": "3bZcd35GAS",
 "B": "7bXcd352sd",
 "choice_num": 0,
 "ciphertext": {"alpha": "6BtdxuEwbcs+dfs3", "beta": "nC345Xbadw3235SD"},
 "election_hash": "Nz1fWLvVLH3eY3Ox7u5hxfLZPdw",
 "question_num": 2}
```

to generate the challenge that the prover must respond to.

### Ballot Audit Trail

When a voter chooses to audit their ballot, each encrypted answer
contains additional information concerning the actual selected choice
and the randomness used to encrypt each choice's
ciphertext. Specifically, the JSON structure for
`<VOTE_WITH_PLAINTEXTS>` is as follows.

```
<VOTE_WITH_PLAINTEXTS>
{"answers": [<ENCRYPTED_ANSWER_WITH_PLAINTEXT>, <ENCRYPTED_ANSWER_WITH_PLAINTEXT>, ...], "election_hash": <B64_HASH>, "election_uuid": <ELECTION_UUID>}
```

And the contained `<ENCRYPTED_ANSWER_WITH_PLAINTEXT>` is as follows.

```
<ENCRYPTED_ANSWER_WITH_PLAINTEXT>
{"answer": 1, "choices": [<ELGAMAL_CIPHERTEXT>, <ELGAMAL_CIPHERTEXT>, ...], "individual_proofs": [<ZK_PROOF_0..1>, <ZK_PROOF_0..1>, ...], "overall_proof": <ZK_PROOF_0..max>, "randomness": [<BIGINT_B64>, <BIGINT_B64>, <BIGINT_B64>]}
```

### Result

The result of an election is represented using the `<RESULT>` data
structure. The proofs of the decryption are done at the Trustee
level. The result simply displays the count of votes for each
candidate within each question, in an array of arrays format.

```
<RESULT>
[[<QUESTION_1_CANDIDATE_1_COUNT>, <QUESTION_1_CANDIDATE_2_COUNT>, <QUESTION_1_CANDIDATE_3_COUNT>], [<QUESTION_2_CANDIDATE_1_COUNT>, <QUESTION_2_CANDIDATE_2_COUNT>]]
```

### Trustee

Even if there is only one keypair in the case of a simple election,
Helios v3 (in a departure from previous versions), represents every
election as having trustees. If there is only one trustee, that's
fine, but the data structure remains the same:

```
<TRUSTEE>
{"decryption_factors": <LIST_OF_LISTS_OF_DEC_FACTORS>,
 "decryption_proofs": <LIST_OF_LISTS_OF_DEC_PROOFS>,
 "pok": <POK_OF_SECRET_KEY>,
 "public_key": <PUBLIC_KEY>,
 "public_key_hash": <PUBLIC_KEY_HASH>,
 "uuid": <UUID_OF_TRUSTEE>}
```