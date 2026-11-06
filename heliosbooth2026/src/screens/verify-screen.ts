import { LitElement, html, css } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';

/**
 * Single ballot verifier component.
 * Verifies that an audited ballot was encrypted correctly.
 */
@customElement('verify-screen')
export class VerifyScreen extends LitElement {
  static styles = css`
    :host {
      display: block;
      max-width: 800px;
      margin: 0 auto;
      padding: var(--spacing-md, 16px);
    }

    h2 {
      margin-top: 0;
    }

    .description {
      font-size: 1.1rem;
      margin-bottom: var(--spacing-lg, 24px);
    }

    label {
      display: block;
      font-weight: 500;
      margin-bottom: var(--spacing-xs, 4px);
    }

    .field {
      margin-bottom: var(--spacing-md, 16px);
    }

    input[type="text"] {
      width: 100%;
      padding: var(--spacing-sm, 8px);
      font-size: var(--font-size-md, 1rem);
      border: 1px solid var(--color-border, #ddd);
      border-radius: var(--border-radius, 4px);
      box-sizing: border-box;
    }

    textarea {
      width: 100%;
      min-height: 180px;
      padding: var(--spacing-sm, 8px);
      font-family: monospace;
      font-size: var(--font-size-sm, 0.875rem);
      border: 1px solid var(--color-border, #ddd);
      border-radius: var(--border-radius, 4px);
      resize: vertical;
      box-sizing: border-box;
    }

    .results {
      margin-top: var(--spacing-lg, 24px);
      padding: var(--spacing-md, 16px);
      background-color: var(--color-surface, #f5f5f5);
      border-radius: var(--border-radius, 4px);
      font-family: monospace;
      font-size: var(--font-size-sm, 0.875rem);
      white-space: pre-wrap;
      word-break: break-all;
    }

    .result-line {
      margin: var(--spacing-xs, 4px) 0;
    }

    .result-success {
      color: var(--color-success, #28a745);
      font-weight: bold;
      font-size: 1.1rem;
      margin-top: var(--spacing-md, 16px);
    }

    .result-failure {
      color: var(--color-error, #dc3545);
      font-weight: bold;
      font-size: 1.1rem;
      margin-top: var(--spacing-md, 16px);
    }

    .loading-indicator {
      display: inline-block;
      margin-left: var(--spacing-sm, 8px);
    }

    .error {
      color: var(--color-error, #dc3545);
      margin-top: var(--spacing-md, 16px);
    }

    .cast-warning {
      background-color: #fff3cd;
      border: 1px solid #ffc107;
      border-radius: var(--border-radius, 4px);
      padding: var(--spacing-md, 16px);
      margin-top: var(--spacing-md, 16px);
    }
  `;

  @state() private electionUrl: string = '';
  @state() private auditTrail: string = '';
  @state() private resultLines: string[] = [];
  @state() private verifying: boolean = false;
  @state() private finalResult: 'success' | 'failure' | null = null;
  @state() private errorMessage: string = '';
  @state() private castBallotWarning: boolean = false;

  @query('#election_url') private electionUrlInput!: HTMLInputElement;
  @query('#audit_trail') private auditTrailTextarea!: HTMLTextAreaElement;

  connectedCallback(): void {
    super.connectedCallback();
    // Pre-fill election URL from query params
    const params = new URLSearchParams(window.location.search);
    const url = params.get('election_url');
    if (url) {
      this.electionUrl = url;
    }
  }

  /**
   * Start the verification process.
   */
  private async handleVerify(e: Event): Promise<void> {
    e.preventDefault();

    const electionUrl = this.electionUrlInput?.value?.trim();
    const auditTrail = this.auditTrailTextarea?.value?.trim();

    if (!electionUrl) {
      this.errorMessage = 'Please enter the election URL.';
      return;
    }

    if (!auditTrail) {
      this.errorMessage = 'Please paste the audit trail data.';
      return;
    }

    // Parse the audit trail JSON
    let encryptedVoteJson: Record<string, unknown>;
    try {
      encryptedVoteJson = JSON.parse(auditTrail);
    } catch {
      this.errorMessage = 'Invalid JSON in audit trail. Please paste the complete audit data.';
      return;
    }

    // Check for cast ballot (can't verify those)
    if (encryptedVoteJson['cast_at']) {
      this.castBallotWarning = true;
      this.errorMessage = '';
      return;
    }

    // Reset state
    this.resultLines = [];
    this.finalResult = null;
    this.errorMessage = '';
    this.verifying = true;
    this.castBallotWarning = false;

    this.appendResult('loading election...');

    try {
      // Fetch election data
      const response = await fetch(electionUrl);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const rawJson = await response.text();

      // Try to use a web worker for verification
      if (window.Worker) {
        this.verifyWithWorker(rawJson, encryptedVoteJson);
      } else {
        this.verifyOnMainThread(rawJson, encryptedVoteJson);
      }
    } catch {
      this.appendResult('PROBLEM LOADING election. Are you sure you have the right election URL?');
      this.appendResult('');
      this.finishVerification(false);
    }
  }

  /**
   * Verify using a web worker (non-blocking).
   */
  private verifyWithWorker(electionJson: string, voteJson: Record<string, unknown>): void {
    const worker = new Worker(
      new URL('../../workers/verifier-worker.js', import.meta.url).href
    );

    worker.onmessage = (event: MessageEvent) => {
      if (event.data.type === 'log') {
        console.log('[Verifier]', event.data.msg);
      } else if (event.data.type === 'status') {
        this.appendResult(event.data.msg);
      } else if (event.data.type === 'result') {
        this.finishVerification(event.data.result);
        worker.terminate();
      }
    };

    worker.onerror = () => {
      // Worker failed — fall back to main thread
      console.warn('Verifier worker failed, falling back to main thread');
      worker.terminate();
      this.verifyOnMainThread(electionJson, voteJson);
    };

    worker.postMessage({
      type: 'verify',
      election: electionJson,
      vote: voteJson
    });
  }

  /**
   * Verify on the main thread (fallback if Worker unavailable).
   */
  private verifyOnMainThread(electionJson: string, voteJson: Record<string, unknown>): void {
    // verify_ballot is loaded globally via script tag in verify.html
    const verifyBallot = (window as unknown as Record<string, unknown>)['verify_ballot'] as
      ((election: string, vote: Record<string, unknown>, cb: (msg: string) => void) => boolean) | undefined;

    if (typeof verifyBallot === 'function') {
      const result = verifyBallot(electionJson, voteJson, (msg: string) => {
        this.appendResult(msg);
      });
      this.finishVerification(result);
    } else {
      this.appendResult('Verification library not available.');
      this.finishVerification(false);
    }
  }

  private appendResult(msg: string): void {
    this.resultLines = [...this.resultLines, msg];
  }

  private finishVerification(success: boolean): void {
    this.verifying = false;
    this.finalResult = success ? 'success' : 'failure';
  }

  render() {
    return html`
      <h2>Helios Single-Ballot Verifier</h2>

      <p class="description">
        This verifier lets you enter an audited ballot and verify
        that it was prepared correctly.
      </p>

      <form @submit=${this.handleVerify}>
        <div class="field">
          <label for="election_url">Election URL:</label>
          <input
            type="text"
            id="election_url"
            .value=${this.electionUrl}
            @input=${(e: InputEvent) => { this.electionUrl = (e.target as HTMLInputElement).value; }}
            placeholder="https://example.com/helios/elections/..."
          />
        </div>

        <div class="field">
          <label for="audit_trail">Your Ballot:</label>
          <textarea
            id="audit_trail"
            .value=${this.auditTrail}
            @input=${(e: InputEvent) => { this.auditTrail = (e.target as HTMLTextAreaElement).value; }}
            placeholder="Paste your audit trail JSON here..."
          ></textarea>
        </div>

        <button type="submit" ?disabled=${this.verifying}>
          ${this.verifying ? 'Verifying...' : 'Verify'}
        </button>
      </form>

      ${this.errorMessage ? html`
        <p class="error">${this.errorMessage}</p>
      ` : ''}

      ${this.castBallotWarning ? html`
        <div class="cast-warning">
          <p>
            It looks like you are trying to verify a <strong>cast</strong> ballot.
            Only <strong>audited</strong> ballots can be verified.
          </p>
        </div>
      ` : ''}

      ${this.resultLines.length > 0 ? html`
        <div class="results" role="log" aria-live="polite" aria-label="Verification results">
          ${this.resultLines.map(line => html`
            <div class="result-line">${line}</div>
          `)}

          ${this.finalResult === 'success' ? html`
            <div class="result-success">SUCCESSFUL VERIFICATION, DONE!</div>
          ` : ''}

          ${this.finalResult === 'failure' ? html`
            <div class="result-failure">PROBLEM - THIS BALLOT DOES NOT VERIFY.</div>
          ` : ''}
        </div>
      ` : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'verify-screen': VerifyScreen;
  }
}
