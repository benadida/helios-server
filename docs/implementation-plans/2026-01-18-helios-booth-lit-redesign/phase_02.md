# Helios Booth Lit Redesign - Phase 2: Voting Flow

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Implement complete question navigation and answer selection

**Architecture:** Question screen component receives election data and current question index via props from booth-app. User selections are tracked in booth-app state and passed down. Events bubble up for navigation and answer changes.

**Tech Stack:** Lit 3.3.x, TypeScript 5.x

**Scope:** 4 phases from original design (this is phase 2 of 4)

**Codebase verified:** 2026-01-18

**Dependencies:** Phase 1 must be complete (booth-app, election loading, crypto types)

---

## Task 1: Create Question Screen Component

**Files:**
- Create: `heliosbooth2026/src/screens/question-screen.ts`

**Step 1: Create the question screen component**

Create `heliosbooth2026/src/screens/question-screen.ts`:
```typescript
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
      color: var(--color-success, #28a745);
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

    if (min && min > 0) {
      if (max) {
        return `vote for ${min} to ${max}`;
      }
      return `vote for at least ${min}`;
    }

    if (max) {
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
                role="checkbox"
                aria-checked="${isSelected}"
                aria-disabled="${isDisabled}"
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
```

**Step 2: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 3: Commit**

```bash
git add heliosbooth2026/src/screens/question-screen.ts
git commit -m "feat(booth2026): add question-screen component with answer selection"
```

---

## Task 2: Integrate Question Screen into Booth App

**Files:**
- Modify: `heliosbooth2026/src/booth-app.ts`

**Step 1: Add import for question-screen**

At the top of `heliosbooth2026/src/booth-app.ts`, after the existing imports, add:

```typescript
import './screens/question-screen.js';
import type { AnswerChangeEvent, NavigationEvent } from './screens/question-screen.js';
```

**Step 2: Add event handlers for answer changes and navigation**

In the `BoothApp` class, add these methods after the `startVoting()` method:

```typescript
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

    // Mark this question's encryption as dirty (will be used in Phase 3)
    // For now, just track that answers changed
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

    // Validate before navigating away
    if (!this.validateCurrentQuestion()) {
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
        this.currentScreen = 'review';
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
    }
  }
```

**Step 3: Update the renderCurrentScreen method**

In `booth-app.ts`, find the `renderCurrentScreen()` method and update the `'question'` case:

Replace:
```typescript
      case 'question':
        return html`<p>Question screen - to be implemented in Phase 2</p>`;
```

With:
```typescript
      case 'question':
        return this.renderQuestionScreen();
```

**Step 4: Add the renderQuestionScreen method**

Add this method to the `BoothApp` class:

```typescript
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
```

**Step 5: Update the startVoting method**

In `booth-app.ts`, update the `startVoting()` method to mark the first question as seen if there's only one question:

```typescript
  /**
   * Start voting - go to first question.
   */
  startVoting(): void {
    this.currentQuestionIndex = 0;
    this.currentScreen = 'question';

    // If only one question, show review button immediately
    if (this.election && this.election.questions.length === 1) {
      this.allQuestionsSeen = true;
    }
  }
```

**Step 6: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 7: Commit**

```bash
git add heliosbooth2026/src/booth-app.ts
git commit -m "feat(booth2026): integrate question-screen with answer tracking and navigation"
```

---

## Task 3: Add onbeforeunload Warning for In-Progress Ballots

**Files:**
- Modify: `heliosbooth2026/src/booth-app.ts`

**Step 1: Add beforeunload handler**

In `booth-app.ts`, add a `disconnectedCallback` method and update `connectedCallback`:

Find the `connectedCallback` method and update it to add the beforeunload listener:

```typescript
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
   * Handle beforeunload event - warn user about losing ballot data.
   */
  private handleBeforeUnload(event: BeforeUnloadEvent): string | undefined {
    // Only warn if user has started voting (is on question or later screens)
    if (this.currentScreen === 'question' ||
        this.currentScreen === 'review' ||
        this.currentScreen === 'audit') {
      const message = 'If you leave this page with an in-progress ballot, your ballot will be lost.';
      event.preventDefault();
      event.returnValue = message;
      return message;
    }
    return undefined;
  }
```

Note: You'll need to add the `boundBeforeUnload` property declaration near the other state declarations.

**Step 2: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 3: Commit**

```bash
git add heliosbooth2026/src/booth-app.ts
git commit -m "feat(booth2026): add beforeunload warning for in-progress ballots"
```

---

## Task 4: Test Question Navigation Flow

**Files:** None (verification only)

**Step 1: Start development server**

Run:
```bash
cd heliosbooth2026 && npm run dev
```

**Step 2: Test with a sample election URL**

To test, you'll need a running Helios server with an election. Start the Django server in another terminal:

```bash
uv run python manage.py runserver
```

Then access the booth with an election URL parameter. If you have a test election UUID, visit:
```
http://localhost:5173/booth2026/?election_url=http://localhost:8000/helios/elections/<uuid>
```

**Step 3: Verify these behaviors manually:**

1. Election info screen shows election name, description, and Start button
2. Clicking Start navigates to question 1
3. Can select/deselect answers
4. Selection limit enforced (can't select more than max)
5. Previous/Next buttons work
6. Proceed button appears after viewing last question
7. Progress bar updates correctly
8. Browser warns when trying to leave mid-vote

**Step 4: Run build to ensure production build works**

Run:
```bash
cd heliosbooth2026 && npm run build
```
Expected: Build completes successfully

**Step 5: Run Django tests to ensure no regressions**

Run:
```bash
uv run python manage.py test -v 2
```
Expected: All tests pass

**Step 6: Commit any final adjustments**

```bash
git add -A
git status
```
If any uncommitted changes:
```bash
git commit -m "feat(booth2026): complete Phase 2 voting flow implementation"
```

---

## Phase 2 Completion Checklist

- [ ] `src/screens/question-screen.ts` created with full answer selection UI
- [ ] Question display shows question text and selection constraints
- [ ] Answer checkboxes work with selection tracking
- [ ] Answer randomization respects election/question settings
- [ ] Min/max answer constraints enforced
- [ ] Warning messages displayed appropriately
- [ ] Previous/Next navigation works
- [ ] Progress indicator shows "Question N of M"
- [ ] Proceed button appears after seeing all questions
- [ ] Browser warns before leaving mid-vote
- [ ] TypeScript compiles without errors
- [ ] Build succeeds
- [ ] All existing Django tests pass
