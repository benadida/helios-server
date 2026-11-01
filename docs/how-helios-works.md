# How Helios Works

Helios is an online voting system in which ballots are encrypted on the
voter's own device, and in which anyone allowed to see an election can check
that it was counted correctly. This page explains the process for election
administrators, voters and trustees. For the technical design, see
[Architecture](architecture.md).

## Who is involved

- **Administrators** create the election, write the questions, provide the
  voter list, and run the tally. An election can have more than one
  administrator.
- **Voters** cast encrypted ballots.
- **Trustees** hold the keys needed to decrypt the final tally. By default
  Helios itself is the only trustee. Administrators can add other people as
  trustees.
- **Anyone who can see the election** can check that each ballot is well
  formed and that the result matches the ballots. For a public election that
  means anyone; for a private election, its voters, administrators and
  trustees.

## The steps of an election

1. **Set up.** The administrator creates the election, writes the questions
   and answers, adds any trustees, and uploads the voter list. Questions can
   allow one choice or several, with a minimum and maximum.
2. **Trustee keys.** Each added trustee generates a key pair in their browser
   and keeps the secret part. Only the public part is sent to Helios. These
   public keys are combined into the election's encryption key.
3. **Freeze.** The administrator freezes the election. From then on the
   questions, trustees and encryption key can't change. Voters can still be
   added or removed until the tally starts. Voting opens at the scheduled
   time, or right away if none was set.
4. **Voting.** Voters fill in and cast their ballots (see below).
5. **Tally.** When voting ends, the administrator starts the tally. Helios
   adds up all the encrypted ballots without decrypting any of them, giving
   an encrypted total for each answer.
6. **Decryption.** Each trustee decrypts their share of the encrypted totals,
   together with a proof that they did it correctly. The Helios trustee does
   this automatically; other trustees use their secret key in their browser.
   Every trustee must take part; the totals can't be decrypted otherwise.
7. **Results.** The administrator combines the trustees' shares to get the
   counts, then releases them. The administrator can email voters when the
   results are out.

## Voting

1. The voter opens the voting booth from the election page and makes their
   choices.
2. The booth encrypts the ballot on the voter's device and shows a **ballot
   tracker**, a fingerprint of the encrypted ballot.
3. The voter can **audit** the ballot instead of casting it. The booth then
   reveals how the ballot was encrypted, so the voter (or anyone they give it
   to) can check that it really contains their choices. An audited ballot is
   never counted, and the voter then makes a fresh ballot to cast. This is
   how voters can check that the booth is not changing their vote: since it
   can't know in advance which ballots will be audited, any cheating risks
   being caught.
4. The voter **casts** the ballot and logs in: with the voter ID and password
   Helios emailed them, or with the account they were invited with (for
   example Google or GitHub).
5. Helios checks the ballot's proofs, records it, and emails the voter their
   ballot tracker. The tracker appears next to the voter's entry in the
   election's ballot tracking center, so the voter can check their ballot
   was recorded.
6. **Voting again.** A voter can cast a new ballot at any time while voting
   is open. Only their most recent ballot is counted.

## Privacy

- Helios receives only the encrypted ballot, never the voter's choices.
- Ballots are never decrypted one by one. Only the combined totals are
  decrypted.
- Decrypting anything needs every trustee. Who can decrypt therefore depends
  on who the trustees are:
  - If Helios is the only trustee (the default), the Helios server holds the
    whole key, so the server operator could in principle decrypt individual
    ballots.
  - Adding independent trustees removes that: no single party, including
    Helios, can decrypt without the others.
- Elections can use **voter aliases**, so the public voter list shows
  `V1`, `V2`, ... instead of names.
- A **private** election is visible only to its voters, administrators and
  trustees.

## Verifying an election

Anyone who can see the election can check:

- that their ballot tracker appears on the ballot list;
- that every ballot on the list is well formed: it encrypts a valid choice
  for each question, which the proofs inside each ballot show without
  revealing the choice;
- that each trustee's key is genuine, and that the election key was built
  from them;
- that the encrypted totals are the product of the ballots on the list;
- that each trustee decrypted the totals correctly, and that the published
  counts follow.

Helios includes a verifier page that runs all of these checks in the
browser. There is also a single-ballot verifier for audited ballots. Because
everything checked is published, other people's software can do the same
checks independently.

## What you still have to trust

The checks above show that the published ballots were counted correctly.
They don't cover everything:

- **The voter list and logins.** Helios decides who may vote: the uploaded
  list, plus whoever can register if registration is open. It also checks
  that each ballot comes from a logged-in voter. The voter list is
  published, but the published data alone can't prove that each ballot was
  cast by the voter it is listed under.
- **The voting device and booth.** Encryption happens in the voter's
  browser. Auditing ballots is the protection against a booth or device
  that changes votes.
- **The trustees.** Secrecy relies on the trustees not all working together
  to decrypt individual ballots. That includes Helios when it is a trustee.
- **Coercion.** Voters can see and show their own ballot tracker, and can
  vote again, but Helios has no other protection against voters being
  pressured or paid to vote a certain way.

## Results

For each question, the answers with the most votes win, as many as the
question allows. If answers tie for the last winning place, none of them
takes it: the place is left unfilled and the tied answers are marked, and
the administrator decides what to do. A single-choice question can instead
require an absolute majority: the winner needs more than half of the
ballots cast, otherwise there is no winner.
