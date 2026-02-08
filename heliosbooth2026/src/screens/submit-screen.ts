import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { Election } from '../crypto/types.js';

/**
 * Submit screen component - final confirmation before ballot submission.
 *
 * Renders to light DOM (no Shadow DOM) so the <form> can POST normally.
 * Shadow DOM forms don't participate in native browser form submission.
 * Styles are in booth.css since light DOM components can't use adoptedStyleSheets.
 */
@customElement('submit-screen')
export class SubmitScreen extends LitElement {
  @property({ type: Object }) election: Election | null = null;
  @property({ type: String }) ballotHash: string = '';
  @property({ type: String }) encryptedVoteJson: string = '';

  /**
   * Render to light DOM so the <form> participates in native browser submission.
   */
  protected createRenderRoot(): HTMLElement | DocumentFragment {
    return this;
  }

  /**
   * Handle form submission - notify booth-app to clear beforeunload guard.
   */
  private handleSubmit(): void {
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
        <textarea name="encrypted_vote" class="encrypted-vote-input">${this.encryptedVoteJson}</textarea>

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
