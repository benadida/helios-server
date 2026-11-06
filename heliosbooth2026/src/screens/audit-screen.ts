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

    .post-button {
      font-size: 0.8em;
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
      ? `verify.html?election_url=${encodeURIComponent(this.electionUrl)}`
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
          class="secondary post-button"
          @click=${this.handlePostAudit}
          ?disabled=${this.postingAudit}
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
