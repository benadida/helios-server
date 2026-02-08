# Helios Booth Lit Redesign - Phase 4: Polish & Deployment

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Production-ready booth with accessibility, error handling, and deployment configuration

**Architecture:** Enhance existing components with ARIA labels, keyboard navigation, error states, and loading indicators. Configure Vite for production builds served at `/booth2026/`.

**Tech Stack:** Lit 3.3.x, TypeScript 5.x, Vite 6.x

**Scope:** 4 phases from original design (this is phase 4 of 4)

**Codebase verified:** 2026-01-18

**Dependencies:** Phase 3 must be complete (full voting flow working)

---

## Task 1: Enhance Accessibility in Booth App

**Files:**
- Modify: `heliosbooth2026/src/booth-app.ts`

**Step 1: Add skip link and improve landmark structure**

In the `render()` method of `booth-app.ts`, update to include skip links and proper ARIA landmarks:

Find the opening of the render() return and update:

```typescript
  render() {
    return html`
      <a href="#main-content" class="skip-link">Skip to main content</a>

      <header class="banner" role="banner">
        <div class="exit-link">
          <a href="#"
             @click=${(e: Event) => { e.preventDefault(); this.handleExit(); }}
             aria-label="Exit voting booth">
            exit
          </a>
        </div>
        <h1>Helios Voting Booth</h1>
      </header>

      ${this.currentScreen !== 'loading' && this.currentScreen !== 'election' ? html`
        <nav class="progress-bar" aria-label="Voting progress">
          <span class="progress-step ${this.getProgressStep() >= 1 ? 'active' : ''}"
                ${this.getProgressStep() === 1 ? 'aria-current="step"' : ''}>
            1. Select
          </span>
          <span class="progress-step ${this.getProgressStep() >= 2 ? 'active' : ''}"
                ${this.getProgressStep() === 2 ? 'aria-current="step"' : ''}>
            2. Review
          </span>
          <span class="progress-step ${this.getProgressStep() >= 3 ? 'active' : ''}"
                ${this.getProgressStep() === 3 ? 'aria-current="step"' : ''}>
            3. Submit
          </span>
          <span class="progress-step ${this.getProgressStep() === 4 ? 'active' : ''}"
                ${this.getProgressStep() === 4 ? 'aria-current="step"' : ''}>
            4. Done
          </span>
        </nav>
      ` : ''}

      ${this.error ? html`
        <div class="error" role="alert" aria-live="assertive">${this.error}</div>
      ` : ''}

      <main id="main-content" class="content" role="main">
        ${this.renderCurrentScreen()}
      </main>
    `;
  }
```

**Step 2: Add skip-link styles**

Add to the static styles in booth-app.ts:

```css
    .skip-link {
      position: absolute;
      top: -40px;
      left: 0;
      background: var(--color-primary, #1a73e8);
      color: white;
      padding: var(--spacing-sm, 8px) var(--spacing-md, 16px);
      z-index: 100;
      text-decoration: none;
    }

    .skip-link:focus {
      top: 0;
    }
```

**Step 3: Add focus management for screen transitions**

Add a method to manage focus when screens change:

```typescript
  /**
   * Focus the main content area when screen changes.
   */
  private focusMainContent(): void {
    // Use requestAnimationFrame to ensure DOM has updated
    requestAnimationFrame(() => {
      const main = this.shadowRoot?.querySelector('#main-content') as HTMLElement;
      if (main) {
        main.focus();
      }
    });
  }
```

Update the `navigateTo` method to call this:

```typescript
  navigateTo(screen: BoothScreen): void {
    this.currentScreen = screen;
    this.focusMainContent();
  }
```

Also update `sealBallot`, `prepareForCast`, `auditBallot`, and other screen transition methods to call `this.focusMainContent()` at the end.

**Step 4: Verify TypeScript compiles**

Run:
```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 5: Commit**

```bash
git add heliosbooth2026/src/booth-app.ts
git commit -m "feat(booth2026): enhance accessibility with skip links and focus management"
```

---

## Task 2: Add Error Handling and Loading States

**Files:**
- Modify: `heliosbooth2026/src/booth-app.ts`

**Step 1: Add loading state property**

Add to the state properties:

```typescript
  @state() private isInitializing: boolean = true;
```

**Step 2: Create error screen renderer**

Add a method to render error states:

```typescript
  /**
   * Render error screen with recovery options.
   */
  private renderErrorScreen() {
    return html`
      <section class="error-screen" role="alert" aria-labelledby="error-title">
        <h2 id="error-title">Something went wrong</h2>

        <div class="error-message">
          <p>${this.error}</p>
        </div>

        <div class="error-actions">
          <button @click=${() => window.location.reload()}>
            Reload Page
          </button>

          ${this.election?.cast_url ? html`
            <button class="secondary" @click=${() => window.location.href = this.election!.cast_url}>
              Return to Election Page
            </button>
          ` : ''}
        </div>
      </section>
    `;
  }
```

**Step 3: Add error screen styles**

Add to static styles:

```css
    .error-screen {
      text-align: center;
      padding: var(--spacing-xl, 32px);
    }

    .error-message {
      background-color: #fee;
      border: 1px solid var(--color-error, #dc3545);
      color: var(--color-error, #dc3545);
      padding: var(--spacing-md, 16px);
      border-radius: var(--border-radius, 4px);
      margin: var(--spacing-lg, 24px) 0;
    }

    .error-actions {
      display: flex;
      gap: var(--spacing-md, 16px);
      justify-content: center;
    }
```

**Step 4: Improve initializeBooth error handling**

Update the `initializeBooth` method to handle various error cases:

```typescript
  private async initializeBooth(): Promise<void> {
    this.isInitializing = true;
    this.error = null;

    try {
      // Get election URL from query params
      const params = new URLSearchParams(window.location.search);
      const electionUrl = params.get('election_url');

      if (!electionUrl) {
        this.error = 'No election URL provided. Please access this page from an election link.';
        this.currentScreen = 'election';
        this.isInitializing = false;
        return;
      }

      this.electionUrl = electionUrl;

      // Wait for BigInt crypto to be ready with timeout
      await this.waitForCryptoWithTimeout(10000);
      this.cryptoReady = true;

      // Load election data
      await this.loadElection(electionUrl);

      this.currentScreen = 'election';
    } catch (err) {
      console.error('Booth initialization failed:', err);

      if (err instanceof Error) {
        if (err.message.includes('fetch')) {
          this.error = 'Unable to connect to the election server. Please check your internet connection and try again.';
        } else if (err.message.includes('crypto') || err.message.includes('BigInt')) {
          this.error = 'Failed to initialize cryptographic libraries. Please try using a different browser.';
        } else {
          this.error = `Failed to initialize booth: ${err.message}`;
        }
      } else {
        this.error = 'An unexpected error occurred. Please reload the page.';
      }

      this.currentScreen = 'election';
    } finally {
      this.isInitializing = false;
    }
  }

  /**
   * Wait for crypto with a timeout.
   */
  private waitForCryptoWithTimeout(timeoutMs: number): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('Crypto library initialization timed out'));
      }, timeoutMs);

      this.waitForCrypto()
        .then(() => {
          clearTimeout(timeoutId);
          resolve();
        })
        .catch((err) => {
          clearTimeout(timeoutId);
          reject(err);
        });
    });
  }
```

**Step 5: Update renderCurrentScreen to handle errors**

Update the loading case to show initialization progress:

```typescript
      case 'loading':
        return html`
          <div class="loading" role="status" aria-live="polite">
            <p>${this.isInitializing ? 'Initializing voting booth...' : 'Loading...'}</p>
            <p class="loading-detail">This may take a few seconds</p>
          </div>
        `;
```

Also update the election case to show errors properly:

```typescript
      case 'election':
        if (this.error && !this.election) {
          return this.renderErrorScreen();
        }
        return this.renderElectionScreen();
```

**Step 6: Commit**

```bash
git add heliosbooth2026/src/booth-app.ts
git commit -m "feat(booth2026): improve error handling and loading states"
```

---

## Task 3: Add Responsive CSS and Visual Polish

**Files:**
- Modify: `heliosbooth2026/src/styles/booth.css`

**Step 1: Update the base CSS with responsive styles**

Replace the content of `heliosbooth2026/src/styles/booth.css`:

```css
/* Helios Booth 2026 - Base Styles */

:root {
  --color-primary: #1a73e8;
  --color-primary-dark: #1557b0;
  --color-background: #fff;
  --color-surface: #f5f5f5;
  --color-border: #ddd;
  --color-text: #333;
  --color-text-secondary: #666;
  --color-success: #28a745;
  --color-warning: #ffc107;
  --color-error: #dc3545;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  --font-size-sm: 0.875rem;
  --font-size-md: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.5rem;
  --border-radius: 4px;
  --max-width: 800px;
}

* {
  box-sizing: border-box;
}

html {
  font-size: 16px;
}

body {
  margin: 0;
  padding: 0;
  font-family: var(--font-family);
  font-size: var(--font-size-md);
  color: var(--color-text);
  background-color: var(--color-background);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Focus visible for keyboard navigation */
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Remove default focus for mouse users */
:focus:not(:focus-visible) {
  outline: none;
}

/* Utility classes */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Button styles */
button,
.button {
  display: inline-block;
  padding: var(--spacing-sm) var(--spacing-md);
  font-family: inherit;
  font-size: var(--font-size-md);
  font-weight: 500;
  text-align: center;
  text-decoration: none;
  color: #fff;
  background-color: var(--color-primary);
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.1s ease;
  min-height: 44px; /* Touch target size */
  min-width: 44px;
}

button:hover,
.button:hover {
  background-color: var(--color-primary-dark);
}

button:active,
.button:active {
  transform: scale(0.98);
}

button:disabled,
.button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
  transform: none;
}

button:focus-visible,
.button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Secondary button style */
button.secondary,
.button.secondary {
  background-color: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
}

button.secondary:hover,
.button.secondary:hover {
  background-color: var(--color-surface);
}

button.secondary:disabled,
.button.secondary:disabled {
  color: #999;
  border-color: #ccc;
  background-color: transparent;
}

/* Link styles */
a {
  color: var(--color-primary);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

a:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Form elements */
input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

textarea {
  font-family: monospace;
  font-size: var(--font-size-sm);
}

/* Responsive breakpoints */
@media (max-width: 600px) {
  :root {
    --spacing-md: 12px;
    --spacing-lg: 16px;
    --spacing-xl: 24px;
    --font-size-lg: 1.125rem;
    --font-size-xl: 1.25rem;
  }

  button,
  .button {
    width: 100%;
    justify-content: center;
  }
}

/* Print styles */
@media print {
  body {
    background: white;
    color: black;
  }

  button,
  .button {
    display: none;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :root {
    --color-border: #000;
    --color-text-secondary: #000;
  }

  button,
  .button {
    border: 2px solid currentColor;
  }
}
```

**Step 2: Commit**

```bash
git add heliosbooth2026/src/styles/booth.css
git commit -m "feat(booth2026): add responsive CSS and visual polish"
```

---

## Task 4: Configure Vite for Production Build

**Files:**
- Modify: `heliosbooth2026/vite.config.ts`
- Modify: `heliosbooth2026/index.html`

**Step 1: Update vite.config.ts for production**

Update `heliosbooth2026/vite.config.ts`:

```typescript
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  base: '/booth2026/',
  build: {
    outDir: 'dist',
    // Ensure single bundle for offline operation
    cssCodeSplit: false,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html')
      },
      output: {
        // Force everything into single bundle
        manualChunks: () => 'booth',
        entryFileNames: 'assets/booth.[hash].js',
        chunkFileNames: 'assets/booth.[hash].js',
        assetFileNames: 'assets/booth.[hash].[ext]'
      }
    },
    // Generate sourcemaps for debugging
    sourcemap: true,
    // Minify for production
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: false, // Keep console for debugging crypto issues
        drop_debugger: true
      }
    }
  },
  server: {
    port: 5173,
    // Proxy API requests to Django during development
    proxy: {
      '/helios': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  // Copy static assets
  publicDir: 'public'
});
```

**Step 2: Update index.html for production paths**

Update `heliosbooth2026/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Helios Voting Booth - Secure online voting with cryptographic verification">
  <meta name="robots" content="noindex, nofollow">
  <title>Helios Voting Booth</title>

  <!-- Preload critical assets -->
  <link rel="preload" href="/booth2026/src/styles/booth.css" as="style">

  <!-- Styles -->
  <link rel="stylesheet" href="/booth2026/src/styles/booth.css">

  <!-- Crypto libraries must load before the app (synchronous) -->
  <script src="/booth2026/lib/jscrypto/jsbn.js"></script>
  <script src="/booth2026/lib/jscrypto/jsbn2.js"></script>
  <script src="/booth2026/lib/jscrypto/sjcl.js"></script>
  <script src="/booth2026/lib/jscrypto/class.js"></script>
  <script src="/booth2026/lib/jscrypto/bigint.js"></script>
  <script src="/booth2026/lib/jscrypto/random.js"></script>
  <script src="/booth2026/lib/jscrypto/elgamal.js"></script>
  <script src="/booth2026/lib/jscrypto/sha1.js"></script>
  <script src="/booth2026/lib/jscrypto/sha2.js"></script>
  <script src="/booth2026/lib/jscrypto/helios.js"></script>
  <script src="/booth2026/lib/underscore-min.js"></script>

  <!-- Noscript fallback -->
  <noscript>
    <style>
      booth-app { display: none; }
      .noscript-message { display: block !important; }
    </style>
  </noscript>
</head>
<body>
  <div class="noscript-message" style="display: none; padding: 20px; text-align: center;">
    <h1>JavaScript Required</h1>
    <p>The Helios Voting Booth requires JavaScript to encrypt your ballot securely.</p>
    <p>Please enable JavaScript in your browser settings and reload this page.</p>
  </div>

  <booth-app></booth-app>

  <script type="module" src="/booth2026/src/main.ts"></script>
</body>
</html>
```

**Step 3: Create public directory for static assets**

```bash
mkdir -p heliosbooth2026/public
mv heliosbooth2026/encrypting.gif heliosbooth2026/public/
mv heliosbooth2026/loading.gif heliosbooth2026/public/
```

**Step 4: Update worker path for production**

In `booth-app.ts`, update the worker initialization to use the correct path:

```typescript
    this.worker = new Worker(new URL('/booth2026/workers/encryption-worker.js', import.meta.url));
```

**Step 5: Verify build works**

Run:
```bash
cd heliosbooth2026 && npm run build
```
Expected: Build completes with dist/ containing bundled assets

**Step 6: Commit**

```bash
git add heliosbooth2026/vite.config.ts heliosbooth2026/index.html heliosbooth2026/public/
git commit -m "feat(booth2026): configure Vite for production build"
```

---

## Task 5: Update Django URL Configuration for Production

**Files:**
- Modify: `urls.py` (project root)

**Step 1: Update URL route to serve both dev and built assets**

The existing route should work for both development (serving source files) and production (serving built dist files). Update `urls.py`:

Find the booth2026 route and update the comment:

```python
    # New Lit-based booth (serves source files in dev, built files in production)
    # In production, this should point to heliosbooth2026/dist instead
    re_path(r'booth2026/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosbooth2026'}),
```

For production deployment, this would be changed to:
```python
    re_path(r'booth2026/(?P<path>.*)$', serve, {'document_root' : settings.ROOT_PATH + '/heliosbooth2026/dist'}),
```

**Step 2: Verify routing works**

Run:
```bash
uv run python manage.py runserver
```

Visit http://localhost:8000/booth2026/ to verify the page loads.

**Step 3: Commit**

```bash
git add urls.py
git commit -m "docs(booth2026): add production deployment comment to URL config"
```

---

## Task 6: Verify Offline Operation

**Files:** None (verification only)

**Step 1: Build production assets**

```bash
cd heliosbooth2026 && npm run build
```

**Step 2: Test offline scenario**

1. Start Django server:
   ```bash
   uv run python manage.py runserver
   ```

2. Load the booth with an election URL in the browser

3. Open browser DevTools → Network tab

4. Click "Start" to begin voting

5. After the election loads, go to DevTools → Network → set to "Offline"

6. Complete the voting process:
   - Answer all questions
   - Review ballot
   - Verify encryption works (should complete without network)

7. Go back online before clicking "Submit" (submission requires network)

**Step 3: Document offline verification**

The booth should work completely offline between "Start" and "Submit". All these should work offline:
- Question navigation
- Answer selection
- Ballot encryption
- Review screen display
- Audit trail generation (if spoiled)

**Step 4: Commit any fixes**

If any issues found, fix and commit:
```bash
git add -A
git commit -m "fix(booth2026): ensure offline operation during voting"
```

---

## Task 7: Run Full Test Suite and Final Verification

**Files:** None (verification only)

**Step 1: Run Django tests**

```bash
uv run python manage.py test -v 2
```
Expected: All tests pass

**Step 2: TypeScript verification**

```bash
cd heliosbooth2026 && npx tsc --noEmit
```
Expected: No errors

**Step 3: Production build**

```bash
cd heliosbooth2026 && npm run build
```
Expected: Build succeeds

**Step 4: Manual end-to-end test**

Test the complete flow with a real election:

1. Create a test election (or use existing one)
2. Navigate to booth2026 with election URL
3. Verify:
   - [ ] Election info displays correctly
   - [ ] Start button works
   - [ ] Questions display with proper formatting
   - [ ] Answer selection works (including limits)
   - [ ] Navigation (Previous/Next) works
   - [ ] Progress indicator updates
   - [ ] Encryption completes with progress display
   - [ ] Review screen shows correct choices
   - [ ] Ballot hash displays
   - [ ] Submit form works (redirects to login)
   - [ ] Audit feature works (if enabled)
   - [ ] Keyboard navigation works throughout
   - [ ] Screen reader announces changes (test with VoiceOver/NVDA)

**Step 5: Final commit**

```bash
git add -A
git status
```
If any uncommitted changes:
```bash
git commit -m "feat(booth2026): complete Phase 4 polish and deployment"
```

---

## Phase 4 Completion Checklist

**Accessibility:**
- [ ] Skip link to main content
- [ ] Proper heading hierarchy
- [ ] ARIA landmarks (banner, main, navigation)
- [ ] ARIA labels on interactive elements
- [ ] Focus management on screen transitions
- [ ] Keyboard navigation throughout
- [ ] High contrast mode support
- [ ] Reduced motion support

**Error Handling:**
- [ ] Graceful handling of network errors
- [ ] Crypto initialization timeout handling
- [ ] User-friendly error messages
- [ ] Recovery options (reload, return to election)

**Visual Polish:**
- [ ] Responsive layout (mobile-friendly)
- [ ] Consistent spacing and typography
- [ ] Touch-friendly button sizes (44px minimum)
- [ ] Loading states with feedback
- [ ] Print styles

**Deployment:**
- [ ] Vite configured for production build
- [ ] Single bundle output (no code splitting)
- [ ] Sourcemaps generated
- [ ] Static assets properly handled
- [ ] Django URL route configured

**Offline Operation:**
- [ ] All assets bundled for offline use
- [ ] Encryption works without network
- [ ] No network calls between Start and Submit
- [ ] Verified by testing with DevTools offline mode

**Final Verification:**
- [ ] All Django tests pass
- [ ] TypeScript compiles without errors
- [ ] Production build succeeds
- [ ] End-to-end manual testing complete
- [ ] Booth accessible at `/booth2026/`
