# Helios Booth Lit Redesign - Phase 1: Setup & Core Shell

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Create the project scaffolding and basic navigation for the new Lit-based voting booth

**Architecture:** Vite + TypeScript + Lit 3.x web components. Single-bundle output for offline operation. Props-drilling state management with booth-app as the central state holder.

**Tech Stack:** Lit 3.3.x, TypeScript 5.x, Vite 6.x

**Scope:** 4 phases from original design (this is phase 1 of 4)

**Codebase verified:** 2026-01-18

---

## Task 1: Create Project Directory Structure

**Files:**
- Create: `heliosbooth2026/` directory
- Create: `heliosbooth2026/package.json`
- Create: `heliosbooth2026/tsconfig.json`
- Create: `heliosbooth2026/vite.config.ts`
- Create: `heliosbooth2026/index.html`

**Step 1: Create the directory and package.json**

Create directory `heliosbooth2026/` at project root.

Create `heliosbooth2026/package.json`:
```json
{
  "name": "heliosbooth2026",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "lit": "^3.3.2"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}
```

**Step 2: Create tsconfig.json**

Create `heliosbooth2026/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "moduleResolution": "bundler",
    "skipLibCheck": true,
    "experimentalDecorators": true,
    "useDefineForClassFields": false,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**Step 3: Create vite.config.ts**

Create `heliosbooth2026/vite.config.ts`:
```typescript
import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  base: '/booth2026/',
  build: {
    outDir: 'dist',
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        manualChunks: () => 'booth',
        entryFileNames: 'booth.js',
        assetFileNames: 'booth.[ext]'
      }
    }
  },
  server: {
    port: 5173
  }
});
```

**Step 4: Create index.html entry point**

Create `heliosbooth2026/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Helios Voting Booth</title>
  <link rel="stylesheet" href="/src/styles/booth.css">
</head>
<body>
  <booth-app></booth-app>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

**Step 5: Verify installation**

Run:
```bash
cd heliosbooth2026 && npm install
```
Expected: Dependencies installed without errors

Run:
```bash
cd heliosbooth2026 && npm run build
```
Expected: Build fails (no src files yet) - this is expected at this step

**Step 6: Commit**

```bash
git add heliosbooth2026/package.json heliosbooth2026/tsconfig.json heliosbooth2026/vite.config.ts heliosbooth2026/index.html
git commit -m "feat(booth2026): initialize Vite + TypeScript + Lit project structure"
```

---

## Task 2: Copy and Organize Crypto Libraries

**Files:**
- Create: `heliosbooth2026/lib/jscrypto/` directory (copied from `heliosbooth/js/jscrypto/`)
- Create: `heliosbooth2026/lib/underscore-min.js` (copied from `heliosbooth/js/underscore-min.js`)
- Create: `heliosbooth2026/src/crypto/types.ts`

**Step 1: Copy jscrypto directory**

```bash
cp -r heliosbooth/js/jscrypto heliosbooth2026/lib/
cp heliosbooth/js/underscore-min.js heliosbooth2026/lib/
```

Expected: Files copied successfully

**Step 2: Create TypeScript type declarations for crypto globals**

Create `heliosbooth2026/src/crypto/types.ts`:
```typescript
/**
 * TypeScript type declarations for the Helios jscrypto library globals.
 * These are loaded via script tags from lib/jscrypto/ and available globally.
 */

// BigInt from lib/jscrypto/bigint.js (wraps sjcl BigInteger)
export interface BigIntType {
  ZERO: BigIntInstance;
  ONE: BigIntInstance;
  TWO: BigIntInstance;
  fromInt(value: number): BigIntInstance;
  fromJSONObject(obj: string): BigIntInstance;
  setup(callback: () => void, errorCallback?: () => void): void;
}

export interface BigIntInstance {
  add(other: BigIntInstance): BigIntInstance;
  subtract(other: BigIntInstance): BigIntInstance;
  multiply(other: BigIntInstance): BigIntInstance;
  mod(modulus: BigIntInstance): BigIntInstance;
  modPow(exponent: BigIntInstance, modulus: BigIntInstance): BigIntInstance;
  modInverse(modulus: BigIntInstance): BigIntInstance;
  equals(other: BigIntInstance): boolean;
  toJSONObject(): string;
  toString(): string;
}

// ElGamal from lib/jscrypto/elgamal.js
export interface ElGamalParams {
  p: BigIntInstance;
  q: BigIntInstance;
  g: BigIntInstance;
}

export interface ElGamalPublicKey {
  p: BigIntInstance;
  q: BigIntInstance;
  g: BigIntInstance;
  y: BigIntInstance;
  toJSONObject(): ElGamalPublicKeyJSON;
}

export interface ElGamalPublicKeyJSON {
  p: string;
  q: string;
  g: string;
  y: string;
}

export interface ElGamalType {
  Params: {
    fromJSONObject(obj: ElGamalParams): ElGamalParams;
  };
  PublicKey: {
    fromJSONObject(obj: ElGamalPublicKeyJSON): ElGamalPublicKey;
  };
}

// Question structure from election JSON
export interface Question {
  question: string;
  short_name: string;
  answers: string[];
  answer_urls?: (string | null)[];
  min: number;
  max: number;
  randomize_answer_order?: boolean;
}

// Election from lib/jscrypto/helios.js
export interface Election {
  uuid: string;
  name: string;
  short_name: string;
  description: string;
  questions: Question[];
  public_key: ElGamalPublicKey;
  cast_url: string;
  frozen_at: string;
  openreg: boolean;
  voters_hash: string | null;
  use_voter_aliases: boolean;
  voting_starts_at: string | null;
  voting_ends_at: string | null;
  election_hash: string;
  hash: string;
  BOGUS_P?: boolean;
  question_answer_orderings?: number[][];
}

export interface EncryptedAnswer {
  toJSONObject(includeRandomness?: boolean): EncryptedAnswerJSON;
}

export interface EncryptedAnswerJSON {
  choices: unknown[];
  individual_proofs: unknown[];
  overall_proof: unknown;
  randomness?: unknown[];
  answer?: number[];
}

export interface EncryptedVote {
  toJSONObject(): EncryptedVoteJSON;
  get_hash(): string;
}

export interface EncryptedVoteJSON {
  answers: EncryptedAnswerJSON[];
  election_hash: string;
  election_uuid: string;
}

export interface HELIOSType {
  Election: {
    fromJSONString(raw: string): Election;
    fromJSONObject(obj: unknown): Election;
  };
  EncryptedAnswer: {
    new(question: Question, answer: number[], publicKey: ElGamalPublicKey): EncryptedAnswer;
    fromJSONObject(obj: EncryptedAnswerJSON, election: Election): EncryptedAnswer;
  };
  EncryptedVote: {
    fromEncryptedAnswers(election: Election, answers: EncryptedAnswer[]): EncryptedVote;
  };
  get_bogus_public_key(): ElGamalPublicKey;
}

export interface RandomType {
  getRandomInteger(max: BigIntInstance): BigIntInstance;
}

export interface UTILSType {
  array_remove_value<T>(arr: T[], val: T): T[];
  PROGRESS: new () => {
    n_ticks: number;
    current_tick: number;
    addTicks(n: number): void;
    tick(): void;
    progress(): number;
  };
  object_sort_keys<T extends object>(obj: T): T;
}

// Election metadata from server
export interface ElectionMetadata {
  help_email: string;
  randomize_answer_order?: boolean;
  use_advanced_audit_features?: boolean;
}

// Declare globals that will be available after loading jscrypto scripts
declare global {
  const BigInt: BigIntType;
  const ElGamal: ElGamalType;
  const HELIOS: HELIOSType;
  const Random: RandomType;
  const UTILS: UTILSType;
  const USE_SJCL: boolean;
  const sjcl: {
    random: {
      startCollectors(): void;
      addEntropy(data: string): void;
    };
  };
  function b64_sha256(data: string): string;
}
```

**Step 3: Verify files exist**

Run:
```bash
ls -la heliosbooth2026/lib/jscrypto/
```
Expected: Lists all crypto library files (bigint.js, elgamal.js, helios.js, etc.)

**Step 4: Commit**

```bash
git add heliosbooth2026/lib/ heliosbooth2026/src/crypto/
git commit -m "feat(booth2026): copy jscrypto library and add TypeScript declarations"
```

---

## Task 3: Create Base CSS Styles

**Files:**
- Create: `heliosbooth2026/src/styles/booth.css`

**Step 1: Create the styles directory and base CSS**

Create `heliosbooth2026/src/styles/booth.css`:
```css
/* Helios Booth 2026 - Base Styles */

:root {
  --color-primary: #1a73e8;
  --color-primary-dark: #1557b0;
  --color-background: #fff;
  --color-surface: #f5f5f5;
  --color-border: #ddd;
  --color-text: #333;
  --color-text-secondary: #666;
  --color-success: #28a745;
  --color-warning: #ffc107;
  --color-error: #dc3545;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  --font-size-sm: 0.875rem;
  --font-size-md: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.5rem;
  --border-radius: 4px;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  font-family: var(--font-family);
  font-size: var(--font-size-md);
  color: var(--color-text);
  background-color: var(--color-background);
  line-height: 1.5;
}

/* Utility classes */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Button styles */
button,
.button {
  display: inline-block;
  padding: var(--spacing-sm) var(--spacing-md);
  font-family: inherit;
  font-size: var(--font-size-md);
  font-weight: 500;
  text-align: center;
  text-decoration: none;
  color: #fff;
  background-color: var(--color-primary);
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background-color 0.2s ease;
}

button:hover,
.button:hover {
  background-color: var(--color-primary-dark);
}

button:disabled,
.button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button:focus,
.button:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Secondary button style */
button.secondary,
.button.secondary {
  background-color: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
}

button.secondary:hover,
.button.secondary:hover {
  background-color: var(--color-surface);
}
```

**Step 2: Verify file created**

Run:
```bash
cat heliosbooth2026/src/styles/booth.css | head -20
```
Expected: Shows beginning of CSS file

**Step 3: Commit**

```bash
git add heliosbooth2026/src/styles/booth.css
git commit -m "feat(booth2026): add base CSS styles"
```

---

## Task 4: Create Main Entry Point and Booth App Shell

**Files:**
- Create: `heliosbooth2026/src/main.ts`
- Create: `heliosbooth2026/src/booth-app.ts`

**Step 1: Create the main entry point**

Create `heliosbooth2026/src/main.ts`:
```typescript
/**
 * Main entry point for the Helios Voting Booth 2026.
 * Loads crypto libraries and initializes the booth app.
 */

import './booth-app.js';

// The booth-app component will handle initialization after crypto libs load
console.log('Helios Booth 2026 loaded');
```

**Step 2: Create the booth-app component shell**

Create `heliosbooth2026/src/booth-app.ts`:
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import type { Election, ElectionMetadata, EncryptedAnswer } from './crypto/types.js';

/**
 * Screen states for the voting booth flow.
 */
type BoothScreen = 'loading' | 'election' | 'question' | 'review' | 'submit' | 'audit';

/**
 * Main booth application component.
 * Holds all voter state and manages screen navigation.
 */
@customElement('booth-app')
export class BoothApp extends LitElement {
  static styles = css`
    :host {
      display: block;
      max-width: 800px;
      margin: 0 auto;
      padding: var(--spacing-md, 16px);
    }

    .banner {
      background-color: var(--color-surface, #f5f5f5);
      padding: var(--spacing-md, 16px);
      text-align: center;
      margin-bottom: var(--spacing-lg, 24px);
      border-bottom: 1px solid var(--color-border, #ddd);
    }

    .banner h1 {
      margin: 0;
      font-size: var(--font-size-xl, 1.5rem);
    }

    .banner .exit-link {
      float: right;
      font-size: var(--font-size-sm, 0.875rem);
    }

    .banner .exit-link a {
      color: var(--color-text-secondary, #666);
      text-decoration: none;
    }

    .banner .exit-link a:hover {
      text-decoration: underline;
    }

    .content {
      min-height: 400px;
    }

    .loading {
      text-align: center;
      padding: var(--spacing-xl, 32px);
    }

    .error {
      background-color: #fee;
      border: 1px solid var(--color-error, #dc3545);
      color: var(--color-error, #dc3545);
      padding: var(--spacing-md, 16px);
      border-radius: var(--border-radius, 4px);
      margin-bottom: var(--spacing-md, 16px);
    }

    .progress-bar {
      display: flex;
      justify-content: center;
      gap: var(--spacing-md, 16px);
      margin-bottom: var(--spacing-lg, 24px);
      padding: var(--spacing-sm, 8px);
      background-color: var(--color-surface, #f5f5f5);
      border-radius: var(--border-radius, 4px);
    }

    .progress-step {
      padding: var(--spacing-xs, 4px) var(--spacing-sm, 8px);
      border-radius: var(--border-radius, 4px);
      font-size: var(--font-size-sm, 0.875rem);
    }

    .progress-step.active {
      background-color: var(--color-primary, #1a73e8);
      color: #fff;
    }

    .progress-step.completed {
      color: var(--color-success, #28a745);
    }
  `;

  // Application state
  @state() private currentScreen: BoothScreen = 'loading';
  @state() private election: Election | null = null;
  @state() private electionMetadata: ElectionMetadata | null = null;
  @state() private electionUrl: string = '';
  @state() private error: string | null = null;

  // Voting state
  @state() private currentQuestionIndex: number = 0;
  @state() private answers: number[][] = [];
  @state() private allQuestionsSeen: boolean = false;

  // Encryption state
  @state() private encryptedAnswers: (EncryptedAnswer | null)[] = [];
  @state() private encryptedBallotHash: string = '';
  @state() private encryptedVoteJson: string = '';

  // Crypto readiness
  @state() private cryptoReady: boolean = false;

  connectedCallback(): void {
    super.connectedCallback();
    this.initializeBooth();
  }

  /**
   * Initialize the booth by loading crypto libraries and election data.
   */
  private async initializeBooth(): Promise<void> {
    try {
      // Get election URL from query params
      const params = new URLSearchParams(window.location.search);
      const electionUrl = params.get('election_url');

      if (!electionUrl) {
        this.error = 'No election URL provided. Please access this page from an election link.';
        this.currentScreen = 'election';
        return;
      }

      this.electionUrl = electionUrl;

      // Wait for BigInt crypto to be ready
      await this.waitForCrypto();
      this.cryptoReady = true;

      // Load election data
      await this.loadElection(electionUrl);

      this.currentScreen = 'election';
    } catch (err) {
      this.error = `Failed to initialize booth: ${err instanceof Error ? err.message : String(err)}`;
      this.currentScreen = 'election';
    }
  }

  /**
   * Wait for the BigInt crypto library to be ready.
   */
  private waitForCrypto(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (typeof BigInt !== 'undefined' && BigInt.setup) {
        BigInt.setup(resolve, reject);
      } else {
        // Crypto libs not loaded via script tags yet - for now just resolve
        // In production, crypto libs are loaded via script tags in index.html
        console.warn('BigInt not available - crypto operations will fail');
        resolve();
      }
    });
  }

  /**
   * Load election data from the server.
   */
  private async loadElection(electionUrl: string): Promise<void> {
    // Fetch election JSON
    const electionResponse = await fetch(electionUrl);
    if (!electionResponse.ok) {
      throw new Error(`Failed to fetch election: ${electionResponse.status}`);
    }
    const rawJson = await electionResponse.text();

    // Fetch election metadata
    const metaResponse = await fetch(`${electionUrl}/meta`);
    if (metaResponse.ok) {
      this.electionMetadata = await metaResponse.json();
    }

    // Parse election using HELIOS library
    if (typeof HELIOS !== 'undefined') {
      this.election = HELIOS.Election.fromJSONString(rawJson);
      this.election.hash = b64_sha256(rawJson);
      this.election.election_hash = this.election.hash;

      // Initialize answer tracking
      this.answers = this.election.questions.map(() => []);
      this.encryptedAnswers = this.election.questions.map(() => null);

      // Set up answer ordering (for randomization if configured)
      this.setupAnswerOrderings();

      // Update document title
      document.title = `Helios Voting Booth - ${this.election.name}`;
    } else {
      throw new Error('HELIOS crypto library not loaded');
    }
  }

  /**
   * Set up answer orderings for each question (supports randomization).
   */
  private setupAnswerOrderings(): void {
    if (!this.election) return;

    this.election.question_answer_orderings = this.election.questions.map((question, _i) => {
      const ordering = question.answers.map((_, j) => j);

      // Shuffle if randomization is enabled at election or question level
      if (
        (this.electionMetadata?.randomize_answer_order) ||
        question.randomize_answer_order
      ) {
        this.shuffleArray(ordering);
      }

      return ordering;
    });
  }

  /**
   * Fisher-Yates shuffle algorithm.
   */
  private shuffleArray<T>(array: T[]): T[] {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }

  /**
   * Handle exit button click.
   */
  private handleExit(): void {
    if (this.currentScreen !== 'election' && this.currentScreen !== 'loading') {
      const confirmed = confirm(
        'Are you sure you want to exit the booth and lose all information about your current ballot?'
      );
      if (!confirmed) return;
    }

    if (this.election?.cast_url) {
      window.location.href = this.election.cast_url;
    }
  }

  /**
   * Navigate to a specific screen.
   */
  navigateTo(screen: BoothScreen): void {
    this.currentScreen = screen;
  }

  /**
   * Start voting - go to first question.
   */
  startVoting(): void {
    this.currentQuestionIndex = 0;
    this.currentScreen = 'question';
  }

  /**
   * Get the current progress step number (1-4).
   */
  private getProgressStep(): number {
    switch (this.currentScreen) {
      case 'question': return 1;
      case 'review': return 2;
      case 'submit': return 3;
      case 'audit': return 4;
      default: return 0;
    }
  }

  render() {
    return html`
      <div class="banner">
        <div class="exit-link">
          <a href="#" @click=${(e: Event) => { e.preventDefault(); this.handleExit(); }}>exit</a>
        </div>
        <h1>Helios Voting Booth</h1>
      </div>

      ${this.currentScreen !== 'loading' && this.currentScreen !== 'election' ? html`
        <div class="progress-bar" role="navigation" aria-label="Voting progress">
          <span class="progress-step ${this.getProgressStep() >= 1 ? 'active' : ''}" aria-current="${this.getProgressStep() === 1 ? 'step' : 'false'}">1. Select</span>
          <span class="progress-step ${this.getProgressStep() >= 2 ? 'active' : ''}" aria-current="${this.getProgressStep() === 2 ? 'step' : 'false'}">2. Review</span>
          <span class="progress-step ${this.getProgressStep() >= 3 ? 'active' : ''}" aria-current="${this.getProgressStep() === 3 ? 'step' : 'false'}">3. Submit</span>
          <span class="progress-step ${this.getProgressStep() >= 4 ? 'active' : ''}" aria-current="${this.getProgressStep() === 4 ? 'step' : 'false'}">4. Done</span>
        </div>
      ` : ''}

      ${this.error ? html`
        <div class="error" role="alert">${this.error}</div>
      ` : ''}

      <main class="content">
        ${this.renderCurrentScreen()}
      </main>
    `;
  }

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
        return html`<p>Question screen - to be implemented in Phase 2</p>`;

      case 'review':
        return html`<p>Review screen - to be implemented in Phase 3</p>`;

      case 'submit':
        return html`<p>Submit screen - to be implemented in Phase 3</p>`;

      case 'audit':
        return html`<p>Audit screen - to be implemented in Phase 3</p>`;

      default:
        return html`<p>Unknown screen</p>`;
    }
  }

  /**
   * Render the election info screen (start screen).
   */
  private renderElectionScreen() {
    if (!this.election) {
      return html`
        <div class="loading">
          <p>Loading election information...</p>
        </div>
      `;
    }

    return html`
      <section aria-labelledby="election-title">
        <h2 id="election-title">${this.election.name}</h2>

        ${this.election.description ? html`
          <div class="election-description">
            <p>${this.election.description}</p>
          </div>
        ` : ''}

        <div class="voting-instructions">
          <p>To vote, follow these steps:</p>
          <ol>
            <li><strong>Select</strong> your preferred options.</li>
            <li><strong>Review</strong> your choices, which are then encrypted.</li>
            <li><strong>Submit</strong> your encrypted ballot and authenticate to verify your eligibility.</li>
          </ol>
        </div>

        <div class="start-button-container" style="text-align: center; margin-top: 24px;">
          <button @click=${this.startVoting} aria-label="Start voting">
            Start
          </button>
        </div>

        ${this.electionMetadata?.help_email ? html`
          <p style="margin-top: 24px;">
            You can
            <a href="mailto:${this.electionMetadata.help_email}?subject=Help%20with%20election%20${encodeURIComponent(this.election.name)}&body=I%20need%20help%20with%20election%20${this.election.uuid}"
               target="_blank">
              email for help
            </a>.
          </p>
        ` : ''}
      </section>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'booth-app': BoothApp;
  }
}
```

**Step 3: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors (or only warnings about unused variables which is expected at this stage)

**Step 4: Commit**

```bash
git add heliosbooth2026/src/main.ts heliosbooth2026/src/booth-app.ts
git commit -m "feat(booth2026): add main entry point and booth-app shell component"
```

---

## Task 5: Update index.html with Crypto Script Loading

**Files:**
- Modify: `heliosbooth2026/index.html`

**Step 1: Update index.html to load crypto scripts before app**

Replace `heliosbooth2026/index.html` with:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Helios Voting Booth</title>
  <link rel="stylesheet" href="/src/styles/booth.css">

  <!-- Crypto libraries must load before the app -->
  <script src="/lib/jscrypto/jsbn.js"></script>
  <script src="/lib/jscrypto/jsbn2.js"></script>
  <script src="/lib/jscrypto/sjcl.js"></script>
  <script src="/lib/jscrypto/class.js"></script>
  <script src="/lib/jscrypto/bigint.js"></script>
  <script src="/lib/jscrypto/random.js"></script>
  <script src="/lib/jscrypto/elgamal.js"></script>
  <script src="/lib/jscrypto/sha1.js"></script>
  <script src="/lib/jscrypto/sha2.js"></script>
  <script src="/lib/jscrypto/helios.js"></script>
  <script src="/lib/underscore-min.js"></script>
</head>
<body>
  <booth-app></booth-app>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

**Step 2: Verify the app runs in development**

Run:
```bash
cd heliosbooth2026 && npm run dev
```
Expected: Vite dev server starts. Visit http://localhost:5173/booth2026/ and see the booth app loading (will show "No election URL provided" error which is expected)

**Step 3: Commit**

```bash
git add heliosbooth2026/index.html
git commit -m "feat(booth2026): add crypto library script loading to index.html"
```

---

## Task 6: Add Django URL Route for booth2026

**Files:**
- Modify: `urls.py` (project root)

**Step 1: Add URL route for booth2026**

In `urls.py`, add a new re_path after line 12 (the existing booth route):

Find this line:
```python
    re_path(r'booth/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosbooth'}),
```

Add after it:
```python
    re_path(r'booth2026/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosbooth2026'}),
```

**Step 2: Verify the route works**

Run:
```bash
uv run python manage.py runserver
```

In a separate terminal:
```bash
curl -I http://localhost:8000/booth2026/
```
Expected: HTTP 200 response (or 304 if cached)

**Step 3: Commit**

```bash
git add urls.py
git commit -m "feat(booth2026): add Django URL route for new booth"
```

---

## Task 7: Verify Complete Phase 1 Setup

**Files:** None (verification only)

**Step 1: Run the full test suite**

Run:
```bash
uv run python manage.py test -v 2
```
Expected: All existing tests pass (booth2026 is independent, shouldn't break anything)

**Step 2: Verify development workflow**

Run:
```bash
cd heliosbooth2026 && npm run dev
```
Expected: Vite dev server starts successfully

In another terminal:
```bash
cd heliosbooth2026 && npm run build
```
Expected: Build completes, `dist/` directory created with bundled files

**Step 3: Verify crypto types**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No TypeScript errors

**Step 4: Final commit for phase 1**

```bash
git add -A
git status
```
If any uncommitted files, commit them:
```bash
git commit -m "feat(booth2026): complete Phase 1 setup and core shell"
```

---

## Phase 1 Completion Checklist

- [ ] `heliosbooth2026/` directory created with Vite + TypeScript + Lit configuration
- [ ] `lib/jscrypto/` contains copied crypto libraries
- [ ] `src/crypto/types.ts` provides TypeScript declarations for crypto globals
- [ ] `src/booth-app.ts` implements main component with screen switching
- [ ] `src/screens/election-screen.ts` implemented inline in booth-app (loads election, shows info, start button)
- [ ] Base CSS structure in place
- [ ] Django URL route serves `/booth2026/`
- [ ] Can load an election from URL parameter
- [ ] Can display election info
- [ ] Can click "Start" to switch screens (navigates to question screen placeholder)
- [ ] All existing tests pass
