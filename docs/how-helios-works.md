# How Helios Works: A Conceptual Guide

## Overview

Helios is an end-to-end verifiable online voting system that allows organizations to conduct secure, transparent elections over the internet. The key principle behind Helios is that voters can verify their votes were counted correctly, while maintaining the secrecy of individual ballots.

## Core Principles

### End-to-End Verifiability

Helios provides mathematical proof that:
1. **Your vote was recorded as cast** - You get a unique ballot tracker to confirm your encrypted vote is in the system
2. **Your vote was tallied as recorded** - You can verify your encrypted vote appears in the final tally
3. **The tally was correctly computed** - Anyone can verify the mathematical correctness of the final count

This is achieved without revealing how any individual voted.

### Vote Privacy

Even though votes are verifiable, individual votes remain secret:
- Votes are encrypted before leaving your computer
- The server never sees your plaintext vote
- Only aggregate totals are revealed, never individual choices
- Multiple independent trustees must collaborate to decrypt results

## The Voting Process

### 1. Election Setup

**Creating an Election**
An administrator creates an election and defines:
- The questions to be decided
- The possible answers for each question
- Rules about how many answers can be selected (minimum and maximum)
- Who is eligible to vote

**Adding Trustees**
The administrator appoints one or more trustees who will collectively hold the keys to decrypt the final results. No single trustee can decrypt votes alone - all trustees must participate. Trustees can be:
- External individuals (who generate their own encryption keys)
- The Helios system itself (for convenience)
- A combination of both

**Registering Voters**
Eligible voters are registered, either by:
- Uploading a list of voters with their email addresses
- Allowing voters to authenticate through external systems (Google, Facebook, GitHub, institutional systems like LDAP or CAS)
- Creating voter accounts with passwords

**Freezing the Election**
Once setup is complete, the election is "frozen" - the questions and eligible voters are locked in, and voting can begin.

### 2. Casting a Vote

**Authentication**
When you arrive at the voting booth, you first authenticate yourself to prove you're an eligible voter. This might be through:
- A password sent to your email
- Logging in with Google, Facebook, or another supported service
- Your institutional login credentials

**Filling Out Your Ballot**
You're presented with the election's questions and answer choices. You select your preferred answers, just like a paper ballot.

**Encryption in Your Browser**
Here's where Helios becomes unique. Before your vote leaves your computer:
1. Your browser encrypts each of your answers using advanced cryptography
2. For each answer choice, your vote is encrypted as either "selected" or "not selected"
3. Mathematical proofs are generated showing your encrypted vote is valid, without revealing what you chose
4. You receive a unique "ballot tracking number" - a hash that identifies your encrypted ballot

**Submitting Your Vote**
Your encrypted vote and its proofs are sent to the Helios server. The server:
- Verifies the mathematical proofs are valid
- Confirms you selected an allowed number of answers
- Records your encrypted vote
- Gives you a ballot tracking number for later verification

**Important**: The server never sees your actual choices, only the encrypted version.

**Updating Your Vote**
You can vote multiple times if needed. Only your most recent vote counts. This allows you to:
- Change your mind
- Replace a vote made under duress
- Re-vote if you suspect an issue

### 3. Verifying Your Vote

**Ballot Tracking**
After voting, you can use your ballot tracking number to verify your encrypted vote appears in the system. The verification tool shows you:
- Your encrypted ballot
- Confirmation it's included in the election
- Mathematical proof the encryption is valid

This verifies your vote was recorded, without revealing how you voted.

### 4. Tallying the Results

**Closing the Polls**
When the voting period ends, the administrator closes the election and begins the tallying process.

**Homomorphic Tallying**
Helios uses a special mathematical property called "homomorphic encryption" that allows counting encrypted votes without decrypting them:

1. All encrypted votes for each answer are combined mathematically
2. This produces an encrypted total for each answer
3. Individual votes remain encrypted and private throughout this process

Think of it like adding numbers in sealed envelopes - you can compute the sum without opening any individual envelope.

**Trustee Decryption**
The encrypted totals must now be decrypted to reveal the final counts:

1. Each trustee independently decrypts their portion of the results
2. Each trustee provides mathematical proof their decryption is correct
3. The server verifies each trustee's proof
4. Once all trustees have participated, their decryptions are combined
5. The final counts are revealed

**Threshold Security**: Since all trustees must participate, no single trustee can decrypt results alone. This prevents premature or unauthorized disclosure.

### 5. Publishing Results

**Releasing Results**
The administrator reviews the decrypted results and chooses when to publish them. Once released:
- Results become publicly visible
- Voters can be notified via email
- The complete election record (encrypted votes, proofs, decryptions) remains available for auditing

## How Helios Maintains Privacy and Security

### Privacy Protection

**During Voting:**
- Your vote is encrypted in your browser before transmission
- The server sees only encrypted data
- Not even the administrators can see individual votes

**During Tallying:**
- Only aggregate totals are computed
- Individual vote privacy is maintained through encryption
- Results show "X votes for Answer A" not "Voter Alice chose Answer A"

**Coercion Resistance:**
- You can vote multiple times (only the last vote counts)
- While not fully coercion-resistant, this provides some protection against vote selling or forced voting

### Security Guarantees

**Authentication:**
- Multiple authentication methods ensure only eligible voters can vote
- Each voter can vote only once (subsequent votes replace earlier ones)
- Voter identity is verified before ballot acceptance

**Integrity:**
- Mathematical proofs ensure votes are valid (e.g., you didn't vote for more candidates than allowed)
- Cryptographic signatures prevent vote tampering
- Ballot tracking lets you verify your vote wasn't changed or lost

**Verifiability:**
- **Individual Verifiability**: You can verify your own vote was recorded
- **Universal Verifiability**: Anyone can verify the tally was computed correctly
- **Eligibility Verifiability**: The list of who voted can be audited

### The Mathematics Behind It

While you don't need to understand the mathematics to use Helios, here's the basic idea:

**Encryption**: Helios uses a cryptosystem called ElGamal, which has special properties:
- It's secure (breaking it is as hard as solving certain difficult mathematical problems)
- It's "homomorphic" (you can add encrypted values without decrypting them)
- It supports "threshold decryption" (multiple parties must cooperate to decrypt)

**Zero-Knowledge Proofs**: When you vote, your browser generates proofs that:
- Each encrypted answer is either "selected" or "not selected"
- The total number of selections is within allowed limits
- These proofs reveal nothing about your actual choices

**Ballot Tracking**: Your ballot tracking number is a cryptographic hash - a unique fingerprint of your encrypted vote that anyone can verify matches your vote in the system.

## Election Lifecycle Summary

1. **Setup Phase**
   - Administrator creates election
   - Trustees are appointed and generate keys
   - Questions and answers are defined
   - Voters are registered
   - Election is frozen

2. **Voting Phase**
   - Voters authenticate
   - Voters encrypt and cast ballots
   - Voters can verify their ballots were recorded
   - Voters can update their votes if needed

3. **Tallying Phase**
   - Polls close
   - Encrypted votes are homomorphically combined
   - Trustees decrypt the aggregate totals
   - Final results are computed

4. **Results Phase**
   - Results are published
   - Full election data remains available for auditing
   - Anyone can verify the mathematical correctness

## What Makes Helios Different

**Compared to Traditional Online Voting:**
- Provides mathematical proof of correctness (not just "trust us")
- Encrypts votes in the voter's browser (server never sees plaintext)
- Allows public verification of results

**Compared to Paper Voting:**
- More convenient (vote from anywhere)
- Instantly verifiable (no need to attend counting)
- Immediate results (once decryption completes)
- Complete audit trail available electronically

**Trade-offs:**
- Requires voters to trust their devices (computer, browser)
- Requires some technical infrastructure (unlike paper ballots)
- Not suitable for high-stakes governmental elections (where paper audit trails are needed)
- Best suited for organizational, academic, and association elections

## Common Use Cases

Helios is ideal for:
- **Academic Organizations**: Faculty governance, student elections
- **Professional Associations**: Board elections, policy decisions
- **Corporate Governance**: Shareholder votes, board elections
- **Non-Profit Organizations**: Member elections, bylaw votes
- **Research Studies**: Preference elicitation, decision-making studies

It's used worldwide by universities, professional societies, open-source projects, and organizations that need verifiable online voting.

## Transparency and Auditability

One of Helios's greatest strengths is complete transparency:
- All encrypted votes are publicly available
- All cryptographic proofs can be independently verified
- Anyone can recompute the tally from the encrypted votes
- The complete election record is preserved

This means:
- Voters can verify their own votes
- Election observers can verify the entire process
- Security researchers can audit the cryptography
- Results can be proven correct mathematically, not just asserted

## Summary

Helios transforms online voting from a "trust the server" model to a "verify the mathematics" model. By encrypting votes in the browser, using homomorphic tallying, and providing cryptographic proofs at every step, Helios enables:

- **Secure** voting (only eligible voters can vote)
- **Private** voting (individual choices remain secret)
- **Verifiable** voting (anyone can confirm the tally is correct)

This combination of properties makes Helios a powerful tool for organizations that need trustworthy online elections.
