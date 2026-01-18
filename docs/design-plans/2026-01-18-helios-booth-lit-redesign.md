# Helios Booth Lit Redesign

## Summary

The Helios Booth Lit Redesign builds a modern replacement for the existing jQuery-based voting booth using Lit web components, TypeScript, and Vite. The new booth runs independently at `/booth2026/` without requiring server changes, preserving the election system's offline security model and byte-for-byte identical cryptographic operations.

The implementation follows a props-drilling state management pattern where the main `booth-app` component holds all voter state and distributes data to screen components (election, question, review, submit, and audit screens) through reactive properties, with screens communicating state changes via events. By copying and adapting the existing crypto libraries (`jscrypto/`), reusing the Web Worker encryption pattern, and maintaining identical ballot formatting, the new booth achieves code clarity and maintainability while ensuring full compatibility with existing election servers and verification tools.

## Definition of Done

**Deliverables:**
- A design plan for a new Lit-based voting booth at `/booth2026/`
- Runs alongside existing booth (separate URL, no server changes needed)
- Preserves all cryptographic operations unchanged
- Preserves offline security model (no network during voting)
- Basic accessibility from the start (semantic HTML, ARIA labels, keyboard navigation)
- i18n architecture noted but implementation deferred to future iteration
- 4 high-level implementation phases

**Success criteria:**
A simpler, clearer version of the existing detailed plan that's actionable across multiple PRs.

## Glossary

- **Lit 3.x**: A lightweight web components library for building fast, efficient UI with template literals and reactive properties.
- **Web Components**: Browser-native reusable UI elements defined as custom HTML tags with encapsulated DOM and styling.
- **Vite**: A modern frontend build tool that uses native ES modules during development and creates optimized production bundles.
- **Props drilling**: A state management pattern where parent components pass data down to children via properties, and children communicate back via events.
- **Web Worker**: A browser API enabling background JavaScript execution in a separate thread, used here for non-blocking ballot encryption.
- **jscrypto**: Helios's JavaScript cryptographic library implementing ElGamal encryption, BigInt arithmetic, and ballot serialization.
- **ElGamal encryption**: The public-key cryptographic scheme used by Helios for encrypting individual votes.
- **@lit/localize**: Lit's internationalization library using the `msg()` function for translation (planned for future iteration).
- **ARIA labels**: Accessibility attributes describing UI elements for screen readers and assistive technologies.

## Architecture

A new Lit-based voting booth at `heliosbooth2026/` running independently alongside the existing jQuery booth at `heliosbooth/`.

**Technology stack:**
- Lit 3.x for web components
- TypeScript for type safety
- Vite for bundling (single bundle, no code splitting for offline operation)

**State management:** Props drilling pattern. `booth-app` holds all state as reactive properties and passes data to screen components via props. Screens emit events for state changes. No global state or context API.

**Component structure:**

```
booth-app (main container, holds all state)
├── election-screen   (election info, start button)
├── question-screen   (question display, answer selection, navigation)
├── review-screen     (encryption progress, ballot review)
├── submit-screen     (ballot hash, cast form)
└── audit-screen      (audit trail display)
```

**Data flow:**
1. `booth-app` loads election JSON on mount
2. User navigates through questions, `booth-app` tracks answers
3. On review, Web Worker encrypts ballot, posts progress back
4. On submit, form POSTs encrypted ballot to server's cast URL

**Crypto integration:** Copy `heliosbooth/js/jscrypto/` into `heliosbooth2026/lib/jscrypto/`. Create TypeScript type declarations for the global objects (`HELIOS`, `ElGamal`, `BigInt`). Adapt `boothworker-single.js` for the new structure. Encrypted ballot JSON must be byte-for-byte identical to old booth output.

**Critical constraint:** Zero network calls between "Start" and "Submit". All assets bundled, all encryption client-side.

## Existing Patterns

Investigation found the existing booth at `heliosbooth/` uses:
- Single HTML entry point (`vote.html`) loading a compressed JS bundle
- `BOOTH` object as monolithic state container
- jQuery jTemplates for rendering
- Panel-based UI with show/hide
- Web Worker for async encryption

**Patterns this design follows:**
- Same crypto layer (unchanged `jscrypto/` directory)
- Same Web Worker encryption approach
- Same API endpoints and ballot format
- Same panel-based screen switching concept

**Patterns this design changes:**
- jQuery → Lit web components
- Monolithic BOOTH object → typed state in booth-app
- jQuery templates → Lit template literals
- Implicit globals → explicit TypeScript types

The new booth produces identical encrypted ballots, ensuring server compatibility.

## Implementation Phases

### Phase 1: Setup & Core Shell
**Goal:** Project scaffolding and basic navigation working

**Components:**
- `heliosbooth2026/` directory with Vite + TypeScript + Lit configuration
- `lib/jscrypto/` — copied crypto libraries from old booth
- `src/crypto/types.ts` — TypeScript declarations for crypto globals
- `src/booth-app.ts` — main component with screen switching
- `src/screens/election-screen.ts` — loads election, shows info, start button
- Basic CSS structure

**Dependencies:** None (first phase)

**Done when:** Can load an election from URL parameter, display election info, click "Start" to switch screens

### Phase 2: Voting Flow
**Goal:** Complete question navigation and answer selection

**Components:**
- `src/screens/question-screen.ts` — question display, answer checkboxes, validation
- Navigation logic in `booth-app` — previous/next/review
- Answer state tracking — selections per question
- Progress indicator — "Question N of M"
- Answer randomization — shuffle if election specifies

**Dependencies:** Phase 1 (booth-app, election loading)

**Done when:** Can navigate through all questions, select answers respecting min/max constraints, see progress, proceed to review

### Phase 3: Crypto & Submission
**Goal:** Full voting flow including encryption and submission

**Components:**
- `workers/encryption-worker.js` — adapted from `boothworker-single.js`
- `src/screens/review-screen.ts` — encryption progress, ballot summary, seal/audit/submit buttons
- `src/screens/submit-screen.ts` — ballot hash display, cast form
- `src/screens/audit-screen.ts` — audit trail JSON, back-to-voting flow
- Encryption orchestration in `booth-app` — worker communication, progress tracking

**Dependencies:** Phase 2 (answers collected)

**Done when:** Can encrypt ballot, see progress, view ballot hash, submit via form POST, or audit and re-vote

### Phase 4: Polish & Deployment
**Goal:** Production-ready booth at `/booth2026/`

**Components:**
- Accessibility — semantic HTML, ARIA labels, keyboard navigation
- Error handling — loading states, error messages
- CSS polish — responsive layout, visual consistency
- Offline verification — test zero network during voting
- Deployment configuration — serve from `/booth2026/` URL

**Dependencies:** Phase 3 (complete flow working)

**Done when:** Booth passes accessibility basics, handles errors gracefully, works offline during voting, deployed and accessible at `/booth2026/`

## Additional Considerations

**i18n architecture:** Design supports future i18n via `@lit/localize`. All user-facing strings would use `msg()` function. Implementation deferred — first iteration is English only.

**Offline verification:** Each phase should verify no unexpected network calls. Phase 4 includes explicit offline testing (disconnect network after load, complete vote).
