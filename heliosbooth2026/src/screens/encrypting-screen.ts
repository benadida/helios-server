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
        <img src="${new URL(/* @vite-ignore */ '/booth2026/encrypting.gif', import.meta.url).href}" alt="" />
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
