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
