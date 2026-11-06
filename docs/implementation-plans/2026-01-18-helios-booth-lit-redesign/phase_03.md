# Helios Booth Lit Redesign - Phase 3: Crypto & Submission

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Implement full voting flow including encryption and ballot submission

**Architecture:** Web Worker handles encryption in background thread. Booth-app orchestrates worker communication and tracks progress. Review screen shows encrypted ballot summary. Submit screen handles form POST to server.

**Tech Stack:** Lit 3.3.x, TypeScript 5.x, Web Workers

**Scope:** 4 phases from original design (this is phase 3 of 4)

**Codebase verified:** 2026-01-18

**Dependencies:** Phase 2 must be complete (question navigation, answer selection)

---

## Task 1: Create Encryption Worker

**Files:**
- Create: `heliosbooth2026/workers/encryption-worker.js`

**Step 1: Create the worker file**

Create `heliosbooth2026/workers/encryption-worker.js`:
```javascript
/**
 * Web Worker for encrypting ballots in background thread.
 * Adapted from heliosbooth/boothworker-single.js
 *
 * Message types:
 * - setup: Initialize with election JSON
 * - encrypt: Encrypt an answer for a specific question
 *
 * Response types:
 * - log: Logging message
 * - result: Encrypted answer result
 */

// Import crypto libraries - paths relative to worker location
importScripts(
  '../lib/underscore-min.js',
  '../lib/jscrypto/jsbn.js',
  '../lib/jscrypto/jsbn2.js',
  '../lib/jscrypto/sjcl.js',
  '../lib/jscrypto/class.js',
  '../lib/jscrypto/bigint.js',
  '../lib/jscrypto/random.js',
  '../lib/jscrypto/elgamal.js',
  '../lib/jscrypto/sha1.js',
  '../lib/jscrypto/sha2.js',
  '../lib/jscrypto/helios.js'
);

// Console shim - sends logs back to main thread
var console = {
  log: function(msg) {
    self.postMessage({ type: 'log', msg: msg });
  }
};

// Election object - set during setup
var ELECTION = null;

/**
 * Handle setup message - parse and store election.
 */
function do_setup(message) {
  console.log('Setting up encryption worker');
  ELECTION = HELIOS.Election.fromJSONString(message.election);
  console.log('Election loaded: ' + ELECTION.name);
}

/**
 * Handle encrypt message - encrypt answer for a question.
 */
function do_encrypt(message) {
  console.log('Encrypting answer for question ' + message.q_num);

  var encrypted_answer = new HELIOS.EncryptedAnswer(
    ELECTION.questions[message.q_num],
    message.answer,
    ELECTION.public_key
  );

  console.log('Done encrypting question ' + message.q_num);

  // Send result back to main thread
  self.postMessage({
    type: 'result',
    q_num: message.q_num,
    encrypted_answer: encrypted_answer.toJSONObject(true),
    id: message.id
  });
}

/**
 * Message handler - dispatch to appropriate function.
 */
self.onmessage = function(event) {
  if (event.data.type === 'setup') {
    do_setup(event.data);
  } else if (event.data.type === 'encrypt') {
    do_encrypt(event.data);
  }
};
```

**Step 2: Verify worker file is valid JavaScript**

Run:
```bash
node --check heliosbooth2026/workers/encryption-worker.js 2>&1 || echo "Note: importScripts is Web Worker API, not available in Node - syntax is OK"
```
Expected: May show importScripts error (that's OK - it's Web Worker API)

**Step 3: Commit**

```bash
git add heliosbooth2026/workers/encryption-worker.js
git commit -m "feat(booth2026): add encryption Web Worker"
```

---

## Task 2: Add Worker Types to Crypto Types

**Files:**
- Modify: `heliosbooth2026/src/crypto/types.ts`

**Step 1: Add worker message types**

At the end of `heliosbooth2026/src/crypto/types.ts`, add:

```typescript
// Worker message types
export interface WorkerSetupMessage {
  type: 'setup';
  election: string;
}

export interface WorkerEncryptMessage {
  type: 'encrypt';
  q_num: number;
  answer: number[];
  id: number;
}

export type WorkerInMessage = WorkerSetupMessage | WorkerEncryptMessage;

export interface WorkerLogMessage {
  type: 'log';
  msg: string;
}

export interface WorkerResultMessage {
  type: 'result';
  q_num: number;
  encrypted_answer: EncryptedAnswerJSON;
  id: number;
}

export type WorkerOutMessage = WorkerLogMessage | WorkerResultMessage;

// BALLOT helper (from helios.js)
export interface BALLOTType {
  pretty_choices(election: Election, ballot: { answers: number[][] }): string[][];
}

declare global {
  const BALLOT: BALLOTType;
}
```

**Step 2: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 3: Commit**

```bash
git add heliosbooth2026/src/crypto/types.ts
git commit -m "feat(booth2026): add worker message types to crypto declarations"
```

---

## Task 3: Create Review Screen Component

**Files:**
- Create: `heliosbooth2026/src/screens/review-screen.ts`

**Step 1: Create the review screen component**

Create `heliosbooth2026/src/screens/review-screen.ts`:
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { Election, ElectionMetadata, Question } from '../crypto/types.js';

/**
 * Events emitted by the review screen.
 */
export interface ReviewNavigationEvent {
  action: 'change-question' | 'cast' | 'audit';
  questionIndex?: number;
}

/**
 * Review screen component - shows ballot summary, hash, and submission options.
 */
@customElement('review-screen')
export class ReviewScreen extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    h2 {
      margin-top: 0;
    }

    .ballot-summary {
      background-color: var(--color-surface, #f5f5f5);
      border: 1px solid var(--color-border, #ddd);
      border-radius: var(--border-radius, 4px);
      padding: var(--spacing-md, 16px);
      margin-bottom: var(--spacing-lg, 24px);
    }

    .question-summary {
      margin-bottom: var(--spacing-md, 16px);
    }

    .question-summary:last-child {
      margin-bottom: 0;
    }

    .question-label {
      font-weight: 500;
      margin-bottom: var(--spacing-xs, 4px);
    }

    .choice {
      margin-left: var(--spacing-md, 16px);
      padding: var(--spacing-xs, 4px) 0;
    }

    .choice::before {
      content: '\\2713 ';
      color: var(--color-success, #28a745);
    }

    .no-choice {
      margin-left: var(--spacing-md, 16px);
      font-style: italic;
      color: var(--color-text-secondary, #666);
    }

    .no-choice::before {
      content: '\\2610 ';
    }

    .selection-info {
      font-size: var(--font-size-sm, 0.875rem);
      color: var(--color-text-secondary, #666);
      margin-left: var(--spacing-md, 16px);
    }

    .change-link {
      font-size: var(--font-size-sm, 0.875rem);
      margin-left: var(--spacing-sm, 8px);
    }

    .ballot-tracker {
      margin: var(--spacing-lg, 24px) 0;
    }

    .tracker-hash {
      font-family: monospace;
      font-size: var(--font-size-lg, 1.25rem);
      word-break: break-all;
      background-color: var(--color-surface, #f5f5f5);
      padding: var(--spacing-sm, 8px);
      border-radius: var(--border-radius, 4px);
    }

    .actions {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-md, 16px);
    }

    .primary-action {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm, 8px);
    }

    .loading-indicator {
      display: inline-block;
      width: 20px;
      height: 20px;
    }

    .audit-section {
      background-color: lightyellow;
      border: 1px solid var(--color-border, #ddd);
      padding: var(--spacing-md, 16px);
      border-radius: var(--border-radius, 4px);
      margin-top: var(--spacing-lg, 24px);
      max-width: 400px;
    }

    .audit-section h4 {
      margin: 0 0 var(--spacing-sm, 8px) 0;
      cursor: pointer;
    }

    .audit-section h4:hover {
      text-decoration: underline;
    }

    .audit-content {
      font-size: var(--font-size-sm, 0.875rem);
    }

    .audit-content p {
      margin: var(--spacing-sm, 8px) 0;
    }
  `;

  @property({ type: Object }) election: Election | null = null;
  @property({ type: Object }) electionMetadata: ElectionMetadata | null = null;
  @property({ type: Array }) questions: Question[] = [];
  @property({ type: Array }) choices: string[][] = [];
  @property({ type: String }) ballotHash: string = '';
  @property({ type: String }) encryptedVoteJson: string = '';
  @property({ type: Boolean }) isLoading: boolean = false;
  @property({ type: Boolean }) showAuditSection: boolean = false;

  private auditExpanded: boolean = false;

  /**
   * Handle change question link click.
   */
  private handleChangeQuestion(index: number, event: Event): void {
    event.preventDefault();
    this.dispatchEvent(new CustomEvent<ReviewNavigationEvent>('review-navigate', {
      detail: { action: 'change-question', questionIndex: index },
      bubbles: true,
      composed: true
    }));
  }

  /**
   * Handle cast ballot button click.
   */
  private handleCast(): void {
    this.dispatchEvent(new CustomEvent<ReviewNavigationEvent>('review-navigate', {
      detail: { action: 'cast' },
      bubbles: true,
      composed: true
    }));
  }

  /**
   * Handle audit ballot button click.
   */
  private handleAudit(): void {
    this.dispatchEvent(new CustomEvent<ReviewNavigationEvent>('review-navigate', {
      detail: { action: 'audit' },
      bubbles: true,
      composed: true
    }));
  }

  /**
   * Toggle audit section visibility.
   */
  private toggleAuditSection(): void {
    this.auditExpanded = !this.auditExpanded;
    this.requestUpdate();
  }

  render() {
    return html`
      <h2>Review your Ballot</h2>

      <div class="ballot-summary" role="region" aria-label="Ballot summary">
        ${this.questions.map((question, index) => html`
          <div class="question-summary">
            <div class="question-label">
              Question #${index + 1}: ${question.short_name}
              <a href="#" class="change-link" @click=${(e: Event) => this.handleChangeQuestion(index, e)}>
                [change]
              </a>
            </div>

            ${this.choices[index]?.length === 0 ? html`
              <div class="no-choice">No choice selected</div>
            ` : this.choices[index]?.map(choice => html`
              <div class="choice"><strong>${choice}</strong></div>
            `)}

            ${this.choices[index]?.length < question.max ? html`
              <div class="selection-info">
                [${this.choices[index]?.length || 0} selections out of possible ${question.min}-${question.max}]
              </div>
            ` : ''}
          </div>
        `)}
      </div>

      <div class="ballot-tracker">
        <p>Your ballot tracker is:</p>
        <div class="tracker-hash" aria-label="Ballot tracking number">
          <strong>${this.ballotHash || 'Calculating...'}</strong>
        </div>
      </div>

      <div class="actions">
        <div class="primary-action">
          <button
            @click=${this.handleCast}
            ?disabled=${this.isLoading || !this.ballotHash}
            aria-busy="${this.isLoading}"
          >
            Proceed to Login
          </button>
          ${this.isLoading ? html`
            <span class="loading-indicator" aria-hidden="true">
              <img src="/lib/../loading.gif" alt="" width="20" height="20" />
            </span>
          ` : ''}
        </div>
      </div>

      <!-- Hidden form for ballot submission -->
      <form
        method="POST"
        action="${this.election?.cast_url || ''}"
        id="send_ballot_form"
        style="display: none;"
      >
        <input type="hidden" name="election_uuid" value="${this.election?.uuid || ''}" />
        <input type="hidden" name="election_hash" value="${this.election?.election_hash || ''}" />
        <textarea name="encrypted_vote">${this.encryptedVoteJson}</textarea>
      </form>

      ${this.showAuditSection ? html`
        <div class="audit-section">
          <h4 @click=${this.toggleAuditSection}>
            Spoil & Audit
            <span style="font-size: 0.8em; color: #444;">[optional]</span>
          </h4>
          ${this.auditExpanded ? html`
            <div class="audit-content">
              <p>
                If you choose, you can spoil this ballot and reveal how your choices
                were encrypted. This is an optional auditing process.
              </p>
              <p>
                You will then be guided to re-encrypt your choices for final casting.
              </p>
              <button class="secondary" @click=${this.handleAudit}>
                Spoil & Audit
              </button>
            </div>
          ` : ''}
        </div>
      ` : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'review-screen': ReviewScreen;
  }
}
```

**Step 2: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 3: Commit**

```bash
git add heliosbooth2026/src/screens/review-screen.ts
git commit -m "feat(booth2026): add review-screen component with ballot summary"
```

---

## Task 4: Create Submit Screen Component

**Files:**
- Create: `heliosbooth2026/src/screens/submit-screen.ts`

**Step 1: Create the submit screen component**

Create `heliosbooth2026/src/screens/submit-screen.ts`:
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { Election } from '../crypto/types.js';

/**
 * Submit screen component - final confirmation before ballot submission.
 */
@customElement('submit-screen')
export class SubmitScreen extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    h2 {
      margin-top: 0;
    }

    .info-section {
      margin-bottom: var(--spacing-lg, 24px);
    }

    .info-section p {
      margin: var(--spacing-sm, 8px) 0;
    }

    .tracker-section {
      background-color: var(--color-surface, #f5f5f5);
      padding: var(--spacing-md, 16px);
      border-radius: var(--border-radius, 4px);
      margin-bottom: var(--spacing-lg, 24px);
    }

    .tracker-hash {
      font-family: monospace;
      font-size: 1.1rem;
      word-break: break-all;
    }

    .cast-url {
      font-family: monospace;
      font-size: 1.1rem;
      word-break: break-all;
      background-color: var(--color-surface, #f5f5f5);
      padding: var(--spacing-sm, 8px);
      border-radius: var(--border-radius, 4px);
    }

    .submit-form {
      margin-top: var(--spacing-lg, 24px);
    }
  `;

  @property({ type: Object }) election: Election | null = null;
  @property({ type: String }) ballotHash: string = '';
  @property({ type: String }) encryptedVoteJson: string = '';

  /**
   * Handle form submission - allow beforeunload to pass.
   */
  private handleSubmit(): void {
    // Dispatch event to let booth-app know we're submitting
    this.dispatchEvent(new CustomEvent('ballot-submit', {
      bubbles: true,
      composed: true
    }));
  }

  render() {
    if (!this.election) {
      return html`<p>Loading...</p>`;
    }

    return html`
      <h2>Submit Your Encrypted Ballot</h2>

      <div class="info-section">
        <p>
          All information, other than your encrypted ballot,
          has been removed from memory.
        </p>
      </div>

      <div class="tracker-section">
        <p>As a reminder, your ballot tracking number is:</p>
        <p class="tracker-hash"><strong>${this.ballotHash}</strong></p>
      </div>

      <div class="info-section">
        <p>According to the election definition file, this ballot will be submitted to:</p>
        <p class="cast-url"><strong>${this.election.cast_url}</strong></p>
        <p>where you will log in to validate your eligibility to vote.</p>
      </div>

      <form
        method="POST"
        action="${this.election.cast_url}"
        id="submit_ballot_form"
        class="submit-form"
        @submit=${this.handleSubmit}
      >
        <input type="hidden" name="election_uuid" value="${this.election.uuid}" />
        <input type="hidden" name="election_hash" value="${this.election.election_hash}" />
        <textarea name="encrypted_vote" style="display: none;">${this.encryptedVoteJson}</textarea>

        <button type="submit" aria-label="Submit your encrypted ballot">
          Submit Ballot
        </button>
      </form>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'submit-screen': SubmitScreen;
  }
}
```

**Step 2: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 3: Commit**

```bash
git add heliosbooth2026/src/screens/submit-screen.ts
git commit -m "feat(booth2026): add submit-screen component"
```

---

## Task 5: Create Audit Screen Component

**Files:**
- Create: `heliosbooth2026/src/screens/audit-screen.ts`

**Step 1: Create the audit screen component**

Create `heliosbooth2026/src/screens/audit-screen.ts`:
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property, query } from 'lit/decorators.js';

/**
 * Events emitted by the audit screen.
 */
export interface AuditNavigationEvent {
  action: 'back-to-voting' | 'post-audit';
}

/**
 * Audit screen component - displays audit trail for spoiled ballots.
 */
@customElement('audit-screen')
export class AuditScreen extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    h2 {
      margin-top: 0;
    }

    .warning {
      background-color: #fff3cd;
      border: 1px solid #ffc107;
      border-radius: var(--border-radius, 4px);
      padding: var(--spacing-md, 16px);
      margin-bottom: var(--spacing-lg, 24px);
    }

    .warning strong {
      text-decoration: underline;
    }

    .explanation {
      margin-bottom: var(--spacing-lg, 24px);
    }

    .explanation p {
      margin: var(--spacing-sm, 8px) 0;
    }

    .audit-trail-section {
      margin-bottom: var(--spacing-lg, 24px);
    }

    .audit-textarea {
      width: 100%;
      min-height: 200px;
      font-family: monospace;
      font-size: var(--font-size-sm, 0.875rem);
      padding: var(--spacing-sm, 8px);
      border: 1px solid var(--color-border, #ddd);
      border-radius: var(--border-radius, 4px);
      resize: vertical;
    }

    .instructions {
      margin: var(--spacing-md, 16px) 0;
      font-size: var(--font-size-sm, 0.875rem);
    }

    .actions {
      display: flex;
      gap: var(--spacing-md, 16px);
      flex-wrap: wrap;
      align-items: center;
    }

    .post-note {
      margin-top: var(--spacing-md, 16px);
      font-size: var(--font-size-sm, 0.875rem);
      color: var(--color-text-secondary, #666);
    }

    .post-note strong {
      color: var(--color-text, #333);
    }
  `;

  @property({ type: String }) auditTrail: string = '';
  @property({ type: String }) electionUrl: string = '';
  @property({ type: Boolean }) postingAudit: boolean = false;

  @query('#audit_trail') private auditTextarea!: HTMLTextAreaElement;

  /**
   * Select all text in the audit trail textarea.
   */
  private selectAuditTrail(event: Event): void {
    event.preventDefault();
    if (this.auditTextarea) {
      this.auditTextarea.select();
    }
  }

  /**
   * Handle back to voting button click.
   */
  private handleBackToVoting(): void {
    this.dispatchEvent(new CustomEvent<AuditNavigationEvent>('audit-navigate', {
      detail: { action: 'back-to-voting' },
      bubbles: true,
      composed: true
    }));
  }

  /**
   * Handle post audited ballot button click.
   */
  private handlePostAudit(): void {
    this.dispatchEvent(new CustomEvent<AuditNavigationEvent>('audit-navigate', {
      detail: { action: 'post-audit' },
      bubbles: true,
      composed: true
    }));
  }

  render() {
    const verifierUrl = this.electionUrl
      ? `single-ballot-verify.html?election_url=${encodeURIComponent(this.electionUrl)}`
      : '#';

    return html`
      <h2>Your audited ballot</h2>

      <div class="warning" role="alert">
        <p>
          <strong>IMPORTANT</strong>: this ballot, now that it has been audited,
          <em>will not be tallied</em>.
        </p>
        <p>
          To cast a ballot, you must click the "Back to Voting" button below,
          re-encrypt it, and choose "cast" instead of "audit."
        </p>
      </div>

      <div class="explanation">
        <p>
          <strong>Why?</strong> Helios prevents you from auditing and casting the
          same ballot to provide you with some protection against coercion.
        </p>

        <p>
          <strong>Now what?</strong>
          <a href="#" @click=${this.selectAuditTrail}>Select your ballot audit info</a>,
          copy it to your clipboard, then use the
          <a href="${verifierUrl}" target="_blank" rel="noopener noreferrer">
            ballot verifier
          </a>
          to verify it.
        </p>
        <p>
          Once you're satisfied, click the "back to voting" button to re-encrypt
          and cast your ballot.
        </p>
      </div>

      <div class="audit-trail-section">
        <textarea
          id="audit_trail"
          class="audit-textarea"
          readonly
          aria-label="Audit trail data"
          .value=${this.auditTrail}
        ></textarea>
      </div>

      <div class="instructions">
        Before going back to voting, you can post this audited ballot to the
        Helios tracking center so that others might double-check the verification
        of this ballot.
      </div>

      <div class="post-note">
        <strong>
          Even if you post your audited ballot, you must go back to voting and
          choose "cast" if you want your vote to count.
        </strong>
      </div>

      <div class="actions">
        <button @click=${this.handleBackToVoting}>
          back to voting
        </button>

        <button
          class="secondary"
          @click=${this.handlePostAudit}
          ?disabled=${this.postingAudit}
          style="font-size: 0.8em;"
        >
          ${this.postingAudit ? 'Posting...' : 'post audited ballot to tracking center'}
        </button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'audit-screen': AuditScreen;
  }
}
```

**Step 2: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 3: Commit**

```bash
git add heliosbooth2026/src/screens/audit-screen.ts
git commit -m "feat(booth2026): add audit-screen component for ballot spoiling"
```

---

## Task 6: Create Encrypting Screen Component

**Files:**
- Create: `heliosbooth2026/src/screens/encrypting-screen.ts`

**Step 1: Create the encrypting screen component**

Create `heliosbooth2026/src/screens/encrypting-screen.ts`:
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * Encrypting screen component - shows progress during ballot encryption.
 */
@customElement('encrypting-screen')
export class EncryptingScreen extends LitElement {
  static styles = css`
    :host {
      display: block;
      text-align: center;
      padding: var(--spacing-xl, 32px);
    }

    h2 {
      margin-bottom: var(--spacing-lg, 24px);
    }

    .spinner {
      margin: var(--spacing-lg, 24px) 0;
    }

    .spinner img {
      width: 64px;
      height: 64px;
    }

    .progress {
      font-size: var(--font-size-lg, 1.25rem);
      margin-top: var(--spacing-md, 16px);
    }

    .note {
      color: var(--color-text-secondary, #666);
      margin-top: var(--spacing-lg, 24px);
    }
  `;

  @property({ type: Number }) percentDone: number = 0;

  render() {
    return html`
      <h2>Helios is now encrypting your ballot</h2>

      <div class="spinner" aria-hidden="true">
        <img src="/encrypting.gif" alt="" />
      </div>

      <div class="progress" role="status" aria-live="polite">
        ${this.percentDone}% complete
      </div>

      <p class="note">
        <strong>This may take up to two minutes.</strong>
      </p>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'encrypting-screen': EncryptingScreen;
  }
}
```

**Step 2: Copy the encrypting.gif from old booth**

```bash
cp heliosbooth/encrypting.gif heliosbooth2026/
cp heliosbooth/loading.gif heliosbooth2026/
```

**Step 3: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 4: Commit**

```bash
git add heliosbooth2026/src/screens/encrypting-screen.ts heliosbooth2026/encrypting.gif heliosbooth2026/loading.gif
git commit -m "feat(booth2026): add encrypting-screen with progress display"
```

---

## Task 7: Integrate Crypto Screens into Booth App

**Files:**
- Modify: `heliosbooth2026/src/booth-app.ts`

**Step 1: Add screen imports**

At the top of `heliosbooth2026/src/booth-app.ts`, after the existing screen import, add:

```typescript
import './screens/review-screen.js';
import './screens/submit-screen.js';
import './screens/audit-screen.js';
import './screens/encrypting-screen.js';
import type { ReviewNavigationEvent } from './screens/review-screen.js';
import type { AuditNavigationEvent } from './screens/audit-screen.js';
import type { WorkerOutMessage, EncryptedAnswerJSON } from './crypto/types.js';
```

**Step 2: Update the BoothScreen type**

Find the `BoothScreen` type definition and update it to include 'encrypting':

```typescript
type BoothScreen = 'loading' | 'election' | 'question' | 'encrypting' | 'review' | 'submit' | 'audit';
```

**Step 3: Add encryption-related state properties**

In the BoothApp class, add these new state properties after the existing ones:

```typescript
  // Encryption state
  @state() private worker: Worker | null = null;
  @state() private encryptionProgress: number = 0;
  @state() private answerTimestamps: number[] = [];
  @state() private dirty: boolean[] = [];
  @state() private encryptedBallot: unknown = null; // Full encrypted vote object
  @state() private auditTrail: string = '';
  @state() private rawElectionJson: string = '';
  @state() private postingAudit: boolean = false;
```

**Step 4: Add worker initialization method**

Add these methods to the BoothApp class:

```typescript
  /**
   * Initialize the encryption worker.
   */
  private initializeWorker(): void {
    if (this.worker || !this.rawElectionJson) return;

    this.worker = new Worker('/workers/encryption-worker.js');

    this.worker.onmessage = (event: MessageEvent<WorkerOutMessage>) => {
      if (event.data.type === 'log') {
        console.log('[Worker]', event.data.msg);
      } else if (event.data.type === 'result') {
        this.handleEncryptionResult(event.data.q_num, event.data.encrypted_answer, event.data.id);
      }
    };

    // Send election to worker
    this.worker.postMessage({
      type: 'setup',
      election: this.rawElectionJson
    });

    // Initialize dirty tracking
    if (this.election) {
      this.dirty = this.election.questions.map(() => true);
      this.answerTimestamps = this.election.questions.map(() => 0);
    }
  }

  /**
   * Handle encryption result from worker.
   */
  private handleEncryptionResult(qNum: number, encryptedAnswer: EncryptedAnswerJSON, id: number): void {
    // Check timestamp to avoid race conditions
    if (id !== this.answerTimestamps[qNum]) {
      console.log('Ignoring stale encryption result for question', qNum);
      return;
    }

    // Store encrypted answer
    if (typeof HELIOS !== 'undefined' && this.election) {
      const ea = HELIOS.EncryptedAnswer.fromJSONObject(encryptedAnswer, this.election);
      this.encryptedAnswers = [...this.encryptedAnswers];
      this.encryptedAnswers[qNum] = ea;
    }

    // Update progress
    const done = this.encryptedAnswers.filter(a => a !== null).length;
    this.encryptionProgress = Math.round((done / this.encryptedAnswers.length) * 100);

    // Check if all done
    if (done === this.encryptedAnswers.length) {
      this.finalizeEncryption();
    }
  }

  /**
   * Launch async encryption for a specific question.
   */
  private launchAsyncEncryption(questionNum: number): void {
    if (!this.worker) return;

    const timestamp = Date.now();
    this.answerTimestamps[questionNum] = timestamp;
    this.encryptedAnswers[questionNum] = null;
    this.dirty[questionNum] = false;

    this.worker.postMessage({
      type: 'encrypt',
      q_num: questionNum,
      answer: this.answers[questionNum] || [],
      id: timestamp
    });
  }

  /**
   * Start encryption process - seal the ballot.
   */
  private sealBallot(): void {
    this.currentScreen = 'encrypting';
    this.encryptionProgress = 0;

    // Launch encryption for all dirty questions
    this.dirty.forEach((isDirty, qNum) => {
      if (isDirty || this.encryptedAnswers[qNum] === null) {
        this.launchAsyncEncryption(qNum);
      }
    });

    // If nothing to encrypt (all cached), finalize immediately
    const allDone = this.encryptedAnswers.every(a => a !== null);
    if (allDone) {
      this.finalizeEncryption();
    }
  }

  /**
   * Finalize encryption after all answers are encrypted.
   */
  private finalizeEncryption(): void {
    if (!this.election || typeof HELIOS === 'undefined') return;

    // Create the full encrypted ballot from individual answers
    this.encryptedBallot = HELIOS.EncryptedVote.fromEncryptedAnswers(
      this.election,
      this.encryptedAnswers as EncryptedAnswer[]
    );

    // Serialize and hash
    const ballotObj = (this.encryptedBallot as EncryptedVote).toJSONObject();
    this.encryptedVoteJson = JSON.stringify(ballotObj);
    this.encryptedBallotHash = b64_sha256(this.encryptedVoteJson);

    // Navigate to review
    this.currentScreen = 'review';
  }

  /**
   * Get pretty choices for display.
   */
  private getPrettyChoices(): string[][] {
    if (!this.election || typeof BALLOT === 'undefined') {
      return [];
    }
    return BALLOT.pretty_choices(this.election, { answers: this.answers });
  }
```

**Step 5: Update the loadElection method**

In the `loadElection` method, store the raw JSON and initialize the worker. Find where it fetches the election and add:

After the line:
```typescript
    const rawJson = await electionResponse.text();
```

Add:
```typescript
    this.rawElectionJson = rawJson;
```

And at the end of `loadElection`, after `document.title` is set, add:

```typescript
      // Initialize encryption worker
      this.initializeWorker();
```

**Step 6: Add handler for validateCurrentQuestion to mark dirty**

Update the `handleAnswerChange` method to mark the question as dirty:

At the end of `handleAnswerChange`, add:

```typescript
    // Mark this question's encryption as dirty
    if (this.dirty.length > questionIndex) {
      this.dirty = [...this.dirty];
      this.dirty[questionIndex] = true;
    }
```

**Step 7: Update handleNavigation to trigger encryption on review**

In the `handleNavigation` method, update the `'review'` case:

```typescript
      case 'review':
        this.sealBallot();
        break;
```

**Step 8: Add handlers for review and audit navigation**

Add these methods:

```typescript
  /**
   * Handle navigation events from review screen.
   */
  private handleReviewNavigation(event: CustomEvent<ReviewNavigationEvent>): void {
    const { action, questionIndex } = event.detail;

    switch (action) {
      case 'change-question':
        if (typeof questionIndex === 'number') {
          this.goToQuestion(questionIndex);
        }
        break;

      case 'cast':
        this.prepareForCast();
        break;

      case 'audit':
        this.auditBallot();
        break;
    }
  }

  /**
   * Prepare for casting - clear plaintexts and go to submit screen.
   */
  private prepareForCast(): void {
    // Clear plaintexts from answers (security measure)
    this.answers = this.answers.map(() => []);

    // Clear plaintexts from encrypted ballot
    if (this.encryptedBallot && typeof (this.encryptedBallot as EncryptedVote).clearPlaintexts === 'function') {
      (this.encryptedBallot as EncryptedVote).clearPlaintexts();
    }

    // Clear audit trail
    this.auditTrail = '';

    this.currentScreen = 'submit';
  }

  /**
   * Audit the ballot - show audit trail.
   */
  private auditBallot(): void {
    if (!this.encryptedBallot) return;

    // Get audit trail (includes plaintexts and randomness)
    const auditObj = (this.encryptedBallot as EncryptedVote).toJSONObject(true);
    this.auditTrail = JSON.stringify(auditObj, null, 2);

    this.currentScreen = 'audit';
  }

  /**
   * Handle navigation events from audit screen.
   */
  private handleAuditNavigation(event: CustomEvent<AuditNavigationEvent>): void {
    const { action } = event.detail;

    switch (action) {
      case 'back-to-voting':
        this.resetAndReencrypt();
        break;

      case 'post-audit':
        this.postAuditedBallot();
        break;
    }
  }

  /**
   * Reset encryption and go back to re-encrypt.
   */
  private resetAndReencrypt(): void {
    // Mark all answers as dirty to force re-encryption
    this.dirty = this.dirty.map(() => true);
    this.encryptedAnswers = this.encryptedAnswers.map(() => null);
    this.encryptedBallot = null;
    this.encryptedBallotHash = '';
    this.encryptedVoteJson = '';
    this.auditTrail = '';

    // Go back to seal ballot (re-encrypt)
    this.sealBallot();
  }

  /**
   * Post audited ballot to tracking center.
   */
  private async postAuditedBallot(): Promise<void> {
    if (!this.electionUrl || !this.auditTrail) return;

    this.postingAudit = true;

    try {
      const response = await fetch(`${this.electionUrl}/post-audited-ballot`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `audited_ballot=${encodeURIComponent(this.auditTrail)}`
      });

      if (response.ok) {
        alert('This audited ballot has been posted.\nRemember, this vote will only be used for auditing and will not be tallied.\nClick "back to voting" and cast a new ballot to make sure your vote counts.');
      } else {
        alert('Failed to post audited ballot. Please try again.');
      }
    } catch (err) {
      alert('Failed to post audited ballot: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      this.postingAudit = false;
    }
  }

  /**
   * Handle ballot submission.
   */
  private handleBallotSubmit(): void {
    // Allow the page to unload
    // The beforeunload handler checks currentScreen
    this.currentScreen = 'loading'; // Temporarily set to allow navigation
  }
```

**Step 9: Add required import for EncryptedVote**

In the types import, make sure to include `EncryptedVote`:

```typescript
import type { Election, ElectionMetadata, EncryptedAnswer, EncryptedVote } from './crypto/types.js';
```

**Step 10: Update renderCurrentScreen method**

Update the `renderCurrentScreen` method with the new cases:

```typescript
  private renderCurrentScreen() {
    switch (this.currentScreen) {
      case 'loading':
        return html`
          <div class="loading">
            <p>Loading election...</p>
          </div>
        `;

      case 'election':
        return this.renderElectionScreen();

      case 'question':
        return this.renderQuestionScreen();

      case 'encrypting':
        return html`
          <encrypting-screen
            .percentDone=${this.encryptionProgress}
          ></encrypting-screen>
        `;

      case 'review':
        return html`
          <review-screen
            .election=${this.election}
            .electionMetadata=${this.electionMetadata}
            .questions=${this.election?.questions || []}
            .choices=${this.getPrettyChoices()}
            .ballotHash=${this.encryptedBallotHash}
            .encryptedVoteJson=${this.encryptedVoteJson}
            .showAuditSection=${this.electionMetadata?.use_advanced_audit_features ?? false}
            @review-navigate=${this.handleReviewNavigation}
          ></review-screen>
        `;

      case 'submit':
        return html`
          <submit-screen
            .election=${this.election}
            .ballotHash=${this.encryptedBallotHash}
            .encryptedVoteJson=${this.encryptedVoteJson}
            @ballot-submit=${this.handleBallotSubmit}
          ></submit-screen>
        `;

      case 'audit':
        return html`
          <audit-screen
            .auditTrail=${this.auditTrail}
            .electionUrl=${this.electionUrl}
            .postingAudit=${this.postingAudit}
            @audit-navigate=${this.handleAuditNavigation}
          ></audit-screen>
        `;

      default:
        return html`<p>Unknown screen</p>`;
    }
  }
```

**Step 11: Update the getProgressStep method**

```typescript
  private getProgressStep(): number {
    switch (this.currentScreen) {
      case 'question': return 1;
      case 'encrypting':
      case 'review': return 2;
      case 'submit': return 3;
      case 'audit': return 4;
      default: return 0;
    }
  }
```

**Step 12: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors (or only minor type adjustments needed)

**Step 13: Commit**

```bash
git add heliosbooth2026/src/booth-app.ts
git commit -m "feat(booth2026): integrate crypto screens and encryption workflow"
```

---

## Task 8: Verify Complete Phase 3 Implementation

**Files:** None (verification only)

**Step 1: Run TypeScript check**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 2: Run the build**

Run:
```bash
cd heliosbooth2026 && npm run build
```
Expected: Build completes successfully

**Step 3: Run Django tests**

Run:
```bash
uv run python manage.py test -v 2
```
Expected: All tests pass

**Step 4: Manual testing**

Start both servers:
```bash
# Terminal 1
cd heliosbooth2026 && npm run dev

# Terminal 2
uv run python manage.py runserver
```

Test with a real election:
1. Create a test election in Helios or use an existing one
2. Access `http://localhost:5173/booth2026/?election_url=http://localhost:8000/helios/elections/<uuid>`
3. Verify complete flow: election info → questions → encryption → review → submit/audit

**Step 5: Final commit**

```bash
git add -A
git status
```
If any uncommitted changes:
```bash
git commit -m "feat(booth2026): complete Phase 3 crypto and submission implementation"
```

---

## Phase 3 Completion Checklist

- [ ] `workers/encryption-worker.js` created and adapted from boothworker-single.js
- [ ] Worker message types added to crypto/types.ts
- [ ] `review-screen.ts` shows encryption progress, ballot summary, seal/audit/submit buttons
- [ ] `submit-screen.ts` displays ballot hash, provides cast form
- [ ] `audit-screen.ts` shows audit trail JSON, back-to-voting flow
- [ ] `encrypting-screen.ts` shows encryption progress
- [ ] Encryption orchestration in booth-app with worker communication
- [ ] Progress tracking during encryption
- [ ] Can encrypt ballot and see progress percentage
- [ ] Can view ballot hash/tracker
- [ ] Can submit via form POST
- [ ] Can audit and re-vote (spoil ballot, re-encrypt)
- [ ] Can post audited ballot to tracking center
- [ ] TypeScript compiles without errors
- [ ] Build succeeds
- [ ] All Django tests pass
