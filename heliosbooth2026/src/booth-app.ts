import { LitElement, html, css, nothing } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import type { Election, ElectionMetadata, EncryptedAnswer, EncryptedVote, BigIntType, WorkerOutMessage, EncryptedAnswerJSON } from './crypto/types.js';
import './screens/question-screen.js';
import type { AnswerChangeEvent, NavigationEvent } from './screens/question-screen.js';
import './screens/review-screen.js';
import './screens/submit-screen.js';
import './screens/audit-screen.js';
import './screens/encrypting-screen.js';
import type { ReviewNavigationEvent } from './screens/review-screen.js';
import type { AuditNavigationEvent } from './screens/audit-screen.js';

/**
 * Screen states for the voting booth flow.
 */
export type BoothScreen = 'loading' | 'election' | 'question' | 'encrypting' | 'review' | 'submit' | 'audit';

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

    .skip-link {
      position: absolute;
      top: -40px;
      left: 0;
      background: var(--color-primary, #1a73e8);
      color: white;
      padding: var(--spacing-sm, 8px) var(--spacing-md, 16px);
      z-index: 100;
      text-decoration: none;
    }

    .skip-link:focus {
      top: 0;
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
      outline: none;
    }

    .loading {
      text-align: center;
      padding: var(--spacing-xl, 32px);
    }

    .loading-detail {
      font-size: var(--font-size-sm, 0.875rem);
      color: var(--color-text-secondary, #666);
    }

    .error,
    .error-message {
      background-color: #fee;
      border: 1px solid var(--color-error, #dc3545);
      color: var(--color-error, #dc3545);
      padding: var(--spacing-md, 16px);
      border-radius: var(--border-radius, 4px);
    }

    .error {
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

    .start-button-container {
      text-align: center;
      margin-top: var(--spacing-lg, 24px);
    }

    .help-email {
      margin-top: var(--spacing-lg, 24px);
    }

    .error-screen {
      text-align: center;
      padding: var(--spacing-xl, 32px);
    }

    .error-screen .error-message {
      margin: var(--spacing-lg, 24px) 0;
    }

    .error-actions {
      display: flex;
      gap: var(--spacing-md, 16px);
      justify-content: center;
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

  // Worker-based encryption
  @state() private worker: Worker | null = null;
  @state() private encryptionProgress: number = 0;
  @state() private answerTimestamps: number[] = [];
  @state() private dirty: boolean[] = [];
  @state() private encryptedBallot: EncryptedVote | null = null;
  @state() private auditTrail: string = '';
  @state() private rawElectionJson: string = '';
  @state() private postingAudit: boolean = false;

  // Initialization state
  @state() private isInitializing: boolean = true;

  // Event handler binding for beforeunload
  private boundBeforeUnload = this.handleBeforeUnload.bind(this);

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener('beforeunload', this.boundBeforeUnload);
    this.initializeBooth();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener('beforeunload', this.boundBeforeUnload);
  }

  /**
   * Initialize the booth by loading crypto libraries and election data.
   */
  private async initializeBooth(): Promise<void> {
    this.isInitializing = true;
    this.error = null;

    try {
      // Get election URL from query params
      const params = new URLSearchParams(window.location.search);
      const electionUrl = params.get('election_url');

      if (!electionUrl) {
        this.error = 'No election URL provided. Please access this page from an election link.';
        this.currentScreen = 'election';
        this.isInitializing = false;
        return;
      }

      this.electionUrl = electionUrl;

      // Wait for BigInt crypto to be ready with timeout
      await this.waitForCryptoWithTimeout(10000);

      // Load election data
      await this.loadElection(electionUrl);

      this.currentScreen = 'election';
    } catch (err) {
      console.error('Booth initialization failed:', err);

      if (err instanceof Error) {
        if (err.message.includes('fetch')) {
          this.error = 'Unable to connect to the election server. Please check your internet connection and try again.';
        } else if (err.message.includes('crypto') || err.message.includes('BigInt')) {
          this.error = 'Failed to initialize cryptographic libraries. Please try using a different browser.';
        } else {
          this.error = `Failed to initialize booth: ${err.message}`;
        }
      } else {
        this.error = 'An unexpected error occurred. Please reload the page.';
      }

      this.currentScreen = 'election';
    } finally {
      this.isInitializing = false;
    }
  }

  /**
   * Wait for the BigInt crypto library to be ready.
   */
  private waitForCrypto(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Note: BigInt is accessed via (window as any) to avoid conflicts with TypeScript's built-in BigInt
      const cryptoBigInt = (typeof window !== 'undefined' ? (window as any).BigInt : undefined) as BigIntType;
      if (cryptoBigInt && typeof cryptoBigInt.setup === 'function') {
        cryptoBigInt.setup(resolve, reject);
      } else {
        // Crypto libs not loaded via script tags yet - for now just resolve
        // In production, crypto libs are loaded via script tags in index.html
        console.warn('BigInt not available - crypto operations will fail');
        resolve();
      }
    });
  }

  /**
   * Wait for crypto with a timeout.
   */
  private waitForCryptoWithTimeout(timeoutMs: number): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('Crypto library initialization timed out'));
      }, timeoutMs);

      this.waitForCrypto()
        .then(() => {
          clearTimeout(timeoutId);
          resolve();
        })
        .catch((err) => {
          clearTimeout(timeoutId);
          reject(err);
        });
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
    this.rawElectionJson = rawJson;

    // Fetch election metadata
    const metaResponse = await fetch(`${electionUrl}/meta`);
    if (metaResponse.ok) {
      this.electionMetadata = await metaResponse.json();
    }

    // Parse election using HELIOS library
    if (typeof HELIOS !== 'undefined' && HELIOS.Election && typeof HELIOS.Election.fromJSONString === 'function') {
      const parsedElection = HELIOS.Election.fromJSONString(rawJson);
      if (typeof b64_sha256 === 'function') {
        parsedElection.hash = b64_sha256(rawJson);
        parsedElection.election_hash = parsedElection.hash;
      }

      this.election = parsedElection;

      // Initialize answer tracking
      this.answers = parsedElection.questions.map(() => []);
      this.encryptedAnswers = parsedElection.questions.map(() => null);

      // Set up answer ordering (for randomization if configured)
      this.setupAnswerOrderings();

      // Update document title
      document.title = `Helios Voting Booth - ${parsedElection.name}`;

      // Initialize encryption worker
      this.initializeWorker();
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
   * Initialize the encryption worker.
   */
  private initializeWorker(): void {
    if (this.worker || !this.rawElectionJson) return;

    this.worker = new Worker(new URL('../workers/encryption-worker.js', import.meta.url).href);

    this.worker.onmessage = (event: MessageEvent<WorkerOutMessage>) => {
      if (event.data.type === 'log') {
        console.log('[Worker]', event.data.msg);
      } else if (event.data.type === 'result') {
        this.handleEncryptionResult(event.data.q_num, event.data.encrypted_answer, event.data.id);
      }
    };

    this.worker.onerror = (event: ErrorEvent) => {
      console.error('[Worker Error]', event.message, event.filename, event.lineno);
      this.error = 'Ballot encryption failed. The voting booth encountered an error. Please try again or contact support.';
      this.currentScreen = 'election';
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
    this.focusMainContent();

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
    const ballotObj = this.encryptedBallot!.toJSONObject();
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
   * Handle beforeunload event - warn user about losing ballot data.
   */
  private handleBeforeUnload(event: BeforeUnloadEvent): string | undefined {
    // Only warn if user has started voting (is on question or later screens)
    if (this.currentScreen === 'question' ||
        this.currentScreen === 'encrypting' ||
        this.currentScreen === 'review' ||
        this.currentScreen === 'audit') {
      const message = 'If you leave this page with an in-progress ballot, your ballot will be lost.';
      event.preventDefault();
      event.returnValue = message;
      return message;
    }
    return undefined;
  }

  /**
   * Render error screen with recovery options.
   */
  private renderErrorScreen() {
    return html`
      <section class="error-screen" role="alert" aria-labelledby="error-title">
        <h2 id="error-title">Something went wrong</h2>

        <div class="error-message">
          <p>${this.error}</p>
        </div>

        <div class="error-actions">
          <button @click=${() => window.location.reload()}>
            Reload Page
          </button>

          ${this.election?.cast_url ? html`
            <button class="secondary" @click=${() => window.location.href = this.election!.cast_url}>
              Return to Election Page
            </button>
          ` : ''}
        </div>
      </section>
    `;
  }

  /**
   * Focus the main content area when screen changes.
   */
  private focusMainContent(): void {
    // Use requestAnimationFrame to ensure DOM has updated
    requestAnimationFrame(() => {
      const main = this.shadowRoot?.querySelector('#main-content') as HTMLElement;
      if (main) {
        main.focus();
      }
    });
  }

  /**
   * Navigate to a specific screen.
   */
  navigateTo(screen: BoothScreen): void {
    this.currentScreen = screen;
    this.focusMainContent();
  }

  /**
   * Start voting - go to first question.
   */
  startVoting(): void {
    this.currentQuestionIndex = 0;
    this.currentScreen = 'question';
    this.focusMainContent();

    // If only one question, show review button immediately
    if (this.election && this.election.questions.length === 1) {
      this.allQuestionsSeen = true;
    }
  }

  /**
   * Handle answer selection changes from question screen.
   */
  private handleAnswerChange(event: CustomEvent<AnswerChangeEvent>): void {
    const { questionIndex, answerIndex, selected } = event.detail;

    // Create a new answers array (immutable update)
    const newAnswers = [...this.answers];
    const questionAnswers = [...(newAnswers[questionIndex] || [])];

    if (selected) {
      // Add answer if not already present
      if (!questionAnswers.includes(answerIndex)) {
        questionAnswers.push(answerIndex);
      }
    } else {
      // Remove answer
      const idx = questionAnswers.indexOf(answerIndex);
      if (idx !== -1) {
        questionAnswers.splice(idx, 1);
      }
    }

    newAnswers[questionIndex] = questionAnswers;
    this.answers = newAnswers;

    // Mark this question's encryption as dirty
    if (this.dirty.length > questionIndex) {
      this.dirty = [...this.dirty];
      this.dirty[questionIndex] = true;
    }
  }

  /**
   * Validate current question has minimum required selections.
   */
  private validateCurrentQuestion(): boolean {
    if (!this.election) return false;

    const question = this.election.questions[this.currentQuestionIndex];
    const answers = this.answers[this.currentQuestionIndex] || [];

    if (answers.length < question.min) {
      alert(`You need to select at least ${question.min} answer(s).`);
      return false;
    }

    return true;
  }

  /**
   * Handle navigation events from question screen.
   */
  private handleNavigation(event: CustomEvent<NavigationEvent>): void {
    const { direction } = event.detail;

    // Validate before navigating away (skip validation for previous navigation)
    if (direction !== 'previous' && !this.validateCurrentQuestion()) {
      return;
    }

    switch (direction) {
      case 'previous':
        if (this.currentQuestionIndex > 0) {
          this.currentQuestionIndex--;
        }
        break;

      case 'next':
        if (this.election && this.currentQuestionIndex < this.election.questions.length - 1) {
          // Mark that we've reached the last question when we get there
          if (this.currentQuestionIndex === this.election.questions.length - 2) {
            this.allQuestionsSeen = true;
          }
          this.currentQuestionIndex++;
        }
        break;

      case 'review':
        this.sealBallot();
        break;
    }
  }

  /**
   * Go to a specific question (used for editing from review screen).
   */
  goToQuestion(index: number): void {
    if (this.election && index >= 0 && index < this.election.questions.length) {
      this.currentQuestionIndex = index;
      this.currentScreen = 'question';
      this.focusMainContent();
    }
  }

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
    if (this.encryptedBallot && this.hasClearPlaintexts(this.encryptedBallot)) {
      this.encryptedBallot.clearPlaintexts();
    }

    // Clear audit trail
    this.auditTrail = '';

    this.currentScreen = 'submit';
    this.focusMainContent();
  }

  /**
   * Audit the ballot - show audit trail.
   */
  private auditBallot(): void {
    if (!this.encryptedBallot) return;

    // Get audit trail (includes plaintexts and randomness)
    const auditObj = this.encryptedBallot.toJSONObject(true);
    this.auditTrail = JSON.stringify(auditObj, null, 2);

    this.currentScreen = 'audit';
    this.focusMainContent();
  }

  /**
   * Helper to check if object has clearPlaintexts method.
   */
  private hasClearPlaintexts(obj: unknown): obj is { clearPlaintexts(): void } {
    return typeof obj === 'object' && obj !== null && 'clearPlaintexts' in obj && typeof (obj as Record<string, unknown>).clearPlaintexts === 'function';
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

  /**
   * Render the question screen.
   */
  private renderQuestionScreen() {
    if (!this.election) {
      return html`<p>Loading...</p>`;
    }

    const question = this.election.questions[this.currentQuestionIndex];
    const ordering = this.election.question_answer_orderings?.[this.currentQuestionIndex]
      ?? question.answers.map((_, i) => i);

    // Show review button once user has seen the last question
    // or if they're on the last question
    const showReview = this.allQuestionsSeen ||
      this.currentQuestionIndex === this.election.questions.length - 1;

    return html`
      <question-screen
        .question=${question}
        .questionIndex=${this.currentQuestionIndex}
        .totalQuestions=${this.election.questions.length}
        .selectedAnswers=${this.answers[this.currentQuestionIndex] || []}
        .answerOrdering=${ordering}
        .showReviewButton=${showReview}
        @answer-change=${this.handleAnswerChange}
        @navigate=${this.handleNavigation}
      ></question-screen>
    `;
  }

  /**
   * Get the current progress step number (1-4).
   */
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

  render() {
    return html`
      <a href="#main-content" class="skip-link">Skip to main content</a>

      <header class="banner" role="banner">
        <div class="exit-link">
          <a href="#"
             @click=${(e: Event) => { e.preventDefault(); this.handleExit(); }}
             aria-label="Exit voting booth">
            exit
          </a>
        </div>
        <h1>Helios Voting Booth</h1>
      </header>

      ${this.currentScreen !== 'loading' && this.currentScreen !== 'election' ? html`
        <nav class="progress-bar" aria-label="Voting progress">
          <span class="progress-step ${this.getProgressStep() >= 1 ? 'active' : ''}"
                aria-current=${this.getProgressStep() === 1 ? 'step' : nothing}>
            1. Select
          </span>
          <span class="progress-step ${this.getProgressStep() >= 2 ? 'active' : ''}"
                aria-current=${this.getProgressStep() === 2 ? 'step' : nothing}>
            2. Review
          </span>
          <span class="progress-step ${this.getProgressStep() >= 3 ? 'active' : ''}"
                aria-current=${this.getProgressStep() === 3 ? 'step' : nothing}>
            3. Submit
          </span>
          <span class="progress-step ${this.getProgressStep() === 4 ? 'active' : ''}"
                aria-current=${this.getProgressStep() === 4 ? 'step' : nothing}>
            4. Done
          </span>
        </nav>
      ` : ''}

      ${this.error ? html`
        <div class="error" role="alert" aria-live="assertive">${this.error}</div>
      ` : ''}

      <main id="main-content" class="content" tabindex="-1">
        ${this.renderCurrentScreen()}
      </main>
    `;
  }

  private renderCurrentScreen() {
    switch (this.currentScreen) {
      case 'loading':
        return html`
          <div class="loading" role="status" aria-live="polite">
            <p>${this.isInitializing ? 'Initializing voting booth...' : 'Loading...'}</p>
            <p class="loading-detail">This may take a few seconds</p>
          </div>
        `;

      case 'election':
        if (this.error && !this.election) {
          return this.renderErrorScreen();
        }
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

        <div class="start-button-container">
          <button @click=${this.startVoting} aria-label="Start voting">
            Start
          </button>
        </div>

        ${this.electionMetadata?.help_email ? html`
          <p class="help-email">
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
