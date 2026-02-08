import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import type { Election, ElectionMetadata, EncryptedAnswer, BigIntType } from './crypto/types.js';

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
    const helios = (typeof window !== 'undefined' ? (window as any).HELIOS : undefined);
    const b64_sha256_fn = (typeof window !== 'undefined' ? (window as any).b64_sha256 : undefined);

    if (helios && typeof helios.Election === 'object' && typeof helios.Election.fromJSONString === 'function') {
      const parsedElection = helios.Election.fromJSONString(rawJson);
      if (b64_sha256_fn && typeof b64_sha256_fn === 'function') {
        parsedElection.hash = b64_sha256_fn(rawJson);
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
