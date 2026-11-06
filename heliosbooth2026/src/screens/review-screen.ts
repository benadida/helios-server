import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
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

    .audit-optional {
      font-size: 0.8em;
      color: #444;
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

  @state() private auditExpanded: boolean = false;

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

            ${(this.choices[index]?.length ?? 0) < question.max ? html`
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
              <img src="${new URL(/* @vite-ignore */ '/booth2026/loading.gif', import.meta.url).href}" alt="" width="20" height="20" />
            </span>
          ` : ''}
        </div>
      </div>

      ${this.showAuditSection ? html`
        <div class="audit-section">
          <h4 @click=${this.toggleAuditSection}>
            Spoil & Audit
            <span class="audit-optional">[optional]</span>
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
