import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { Question } from '../crypto/types.js';

/**
 * Events emitted by the question screen.
 */
export interface AnswerChangeEvent {
  questionIndex: number;
  answerIndex: number;
  selected: boolean;
}

export interface NavigationEvent {
  direction: 'previous' | 'next' | 'review';
}

/**
 * Question screen component for displaying and selecting answers.
 */
@customElement('question-screen')
export class QuestionScreen extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .question-header {
      margin-bottom: var(--spacing-md, 16px);
    }

    .question-text {
      font-size: var(--font-size-lg, 1.25rem);
      font-weight: bold;
      white-space: pre-line;
      margin-bottom: var(--spacing-sm, 8px);
    }

    .question-meta {
      font-size: var(--font-size-sm, 0.875rem);
      color: var(--color-text-secondary, #666);
    }

    .answers-list {
      list-style: none;
      padding: 0;
      margin: var(--spacing-md, 16px) 0;
    }

    .answer-item {
      padding: var(--spacing-sm, 8px) var(--spacing-md, 16px);
      margin-bottom: var(--spacing-xs, 4px);
      border: 1px solid var(--color-border, #ddd);
      border-radius: var(--border-radius, 4px);
      cursor: pointer;
      transition: background-color 0.15s ease, border-color 0.15s ease;
    }

    .answer-item:hover {
      background-color: var(--color-surface, #f5f5f5);
    }

    .answer-item.selected {
      background-color: #e3f2fd;
      border-color: var(--color-primary, #1a73e8);
    }

    .answer-item.disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .answer-item.disabled:hover {
      background-color: transparent;
    }

    .answer-checkbox {
      margin-right: var(--spacing-sm, 8px);
    }

    .answer-label {
      display: flex;
      align-items: flex-start;
      gap: var(--spacing-sm, 8px);
    }

    .answer-text {
      flex: 1;
    }

    .answer-link {
      font-size: var(--font-size-sm, 0.875rem);
      white-space: nowrap;
    }

    .warning-box {
      color: var(--color-text-secondary, #666);
      text-align: center;
      font-size: var(--font-size-sm, 0.875rem);
      padding: var(--spacing-sm, 8px);
      min-height: 50px;
    }

    .navigation {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: var(--spacing-lg, 24px);
      padding-top: var(--spacing-md, 16px);
      border-top: 1px solid var(--color-border, #ddd);
    }

    .nav-left {
      display: flex;
      gap: var(--spacing-sm, 8px);
    }

    .nav-right {
      display: flex;
      gap: var(--spacing-sm, 8px);
    }
  `;

  // Props from parent
  @property({ type: Object }) question: Question | null = null;
  @property({ type: Number }) questionIndex: number = 0;
  @property({ type: Number }) totalQuestions: number = 0;
  @property({ type: Array }) selectedAnswers: number[] = [];
  @property({ type: Array }) answerOrdering: number[] = [];
  @property({ type: Boolean }) showReviewButton: boolean = false;

  // Local state
  @state() private maxReached: boolean = false;

  /**
   * Check if maximum selections reached.
   */
  private updateMaxReached(): void {
    if (!this.question) return;
    this.maxReached = this.question.max !== null &&
      this.selectedAnswers.length >= this.question.max;
  }

  updated(changedProperties: Map<string, unknown>): void {
    if (changedProperties.has('selectedAnswers') || changedProperties.has('question')) {
      this.updateMaxReached();
    }
  }

  /**
   * Handle answer checkbox click.
   */
  private handleAnswerClick(answerIndex: number): void {
    const isSelected = this.selectedAnswers.includes(answerIndex);

    // If trying to select but max reached, ignore
    if (!isSelected && this.maxReached) {
      return;
    }

    this.dispatchEvent(new CustomEvent<AnswerChangeEvent>('answer-change', {
      detail: {
        questionIndex: this.questionIndex,
        answerIndex,
        selected: !isSelected
      },
      bubbles: true,
      composed: true
    }));
  }

  /**
   * Handle keyboard interaction on answer items.
   */
  private handleAnswerKeydown(event: KeyboardEvent, answerIndex: number): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      this.handleAnswerClick(answerIndex);
    }
  }

  /**
   * Handle navigation button clicks.
   */
  private handleNavigation(direction: 'previous' | 'next' | 'review'): void {
    this.dispatchEvent(new CustomEvent<NavigationEvent>('navigate', {
      detail: { direction },
      bubbles: true,
      composed: true
    }));
  }

  /**
   * Build the selection constraint text (e.g., "vote for 1 to 3").
   */
  private getConstraintText(): string {
    if (!this.question) return '';

    const { min, max } = this.question;

    if (min !== undefined && min > 0) {
      if (max !== undefined) {
        return `vote for ${min} to ${max}`;
      }
      return `vote for at least ${min}`;
    }

    if (max !== undefined) {
      if (max > 1) {
        return `vote for up to ${max}`;
      }
      return `vote for ${max}`;
    }

    return 'vote for as many as you approve of';
  }

  /**
   * Get warning message based on selection state.
   */
  private getWarningMessage(): string {
    if (!this.question) return '';

    if (this.maxReached && this.question.max && this.question.max > 1) {
      return 'Maximum number of options selected. To change your selection, please de-select a current selection first.';
    }

    if (!this.maxReached && this.question.max && this.selectedAnswers.length < this.question.max) {
      return `You may select up to ${this.question.max} choices total.`;
    }

    return '';
  }

  render() {
    if (!this.question) {
      return html`<p>Loading question...</p>`;
    }

    const ordering = this.answerOrdering.length > 0
      ? this.answerOrdering
      : this.question.answers.map((_, i) => i);

    const isFirstQuestion = this.questionIndex === 0;
    const isLastQuestion = this.questionIndex === this.totalQuestions - 1;

    return html`
      <form @submit=${(e: Event) => e.preventDefault()} aria-label="Question ${this.questionIndex + 1} of ${this.totalQuestions}">
        <div class="question-header">
          <div class="question-text">${this.question.question}</div>
          <div class="question-meta">
            #${this.questionIndex + 1} of ${this.totalQuestions} &mdash;
            ${this.getConstraintText()}
          </div>
        </div>

        <ul class="answers-list" role="group" aria-label="Answer options">
          ${ordering.map(answerIndex => {
            const isSelected = this.selectedAnswers.includes(answerIndex);
            const isDisabled = !isSelected && this.maxReached;
            const answerText = this.question!.answers[answerIndex];
            const answerUrl = this.question!.answer_urls?.[answerIndex];

            return html`
              <li
                class="answer-item ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}"
                tabindex="${isDisabled ? -1 : 0}"
                @click=${() => this.handleAnswerClick(answerIndex)}
                @keydown=${(e: KeyboardEvent) => this.handleAnswerKeydown(e, answerIndex)}
              >
                <label class="answer-label">
                  <input
                    type="checkbox"
                    class="answer-checkbox"
                    .checked=${isSelected}
                    .disabled=${isDisabled}
                    @change=${(e: Event) => {
                      e.stopPropagation();
                      this.handleAnswerClick(answerIndex);
                    }}
                    aria-label="${answerText}"
                  />
                  <span class="answer-text">${answerText}</span>
                  ${answerUrl ? html`
                    <span class="answer-link">
                      [<a href="${answerUrl}" target="_blank" rel="noopener noreferrer" @click=${(e: Event) => e.stopPropagation()}>more info</a>]
                    </span>
                  ` : ''}
                </label>
              </li>
            `;
          })}
        </ul>

        <div class="warning-box" role="status" aria-live="polite">
          ${this.getWarningMessage()}
        </div>

        <nav class="navigation" aria-label="Question navigation">
          <div class="nav-left">
            ${!isFirstQuestion ? html`
              <button
                type="button"
                class="secondary"
                @click=${() => this.handleNavigation('previous')}
                aria-label="Go to previous question"
              >
                Previous
              </button>
            ` : ''}

            ${!isLastQuestion ? html`
              <button
                type="button"
                @click=${() => this.handleNavigation('next')}
                aria-label="Go to next question"
              >
                Next
              </button>
            ` : ''}
          </div>

          <div class="nav-right">
            ${this.showReviewButton ? html`
              <button
                type="button"
                @click=${() => this.handleNavigation('review')}
                aria-label="Proceed to review your ballot"
              >
                Proceed
              </button>
            ` : ''}
          </div>
        </nav>
      </form>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'question-screen': QuestionScreen;
  }
}
