# HumanizeAI

An emerald-glow writing workspace that refines expression while checking meaning and important details.

## Stack and architecture

React 19, Vite 8, TypeScript, Tailwind v4, DM Sans, Lucide icons, Zod validation, and the official Google Gemini SDK. The responsive landing page leads to a split-screen editor, comparison view, verification report, browser-local history, and persistent preferences.

- `src/App.tsx`: navigation, writing workspace, reports, copy/download, history and preferences.
- `src/lib/model.ts`: shared types, bounded word diff, heuristic entity extraction and exact comparisons.
- `server/refine.ts`: validated server-only Gemini workflow.
- `server/vite-api.ts`: development API middleware.
- `api/refine.ts`: production Vercel function.

## Configuration

Copy `.env.example` to `.env.local` and set `GEMINI_API_KEY`. Optionally change `GEMINI_MODEL` (default `gemini-2.5-flash`). Never prefix secrets with `VITE_`, expose them in client code, or save them in browser storage. Restart the host-supervised preview after changing environment variables. Missing credentials return an explicit 503 error, never synthetic output.

## Commands

```sh
pnpm install
pnpm build
pnpm typecheck
pnpm test
pnpm test:browser
pnpm format
```

Inside Figma Make, the development server is host-managed; do not start a second server. Outside Make, `pnpm dev` starts Vite. There is no configured lint command.

## Processing

1. Validate text (1–12,000 characters) and selected controls on the server.
2. Request structured writing analysis, a rewrite, and grounded change explanations from Gemini.
3. Validate the response; discard findings/explanations not grounded in the documents.
4. Compare extracted names, dates, email addresses and numeric values deterministically.
5. Make a separate Gemini call to inspect semantic changes, uncertainty and unsupported additions.
6. Report Checks passed, Review recommended, Verification failed, or Verification unavailable. Failed verification is never shown as a pass.

Completed results are kept locally, including verification failures, so the user can review them. Requests and secrets are not logged. Users can reopen, copy, delete, or clear saved sessions. History does not synchronize between devices.

## Tests

`pnpm test` runs isolated unit tests with mocked Gemini responses: validation, missing credentials, rewriting and verification failures, malformed output, rate limits, entity preservation, changed scores, lost dates, unsupported claims, meaning warnings, unchanged text, comparison and browser storage. These are not live AI tests.

`pnpm test:browser` runs Chromium tests against the existing development server (default port 3000; override with `TEST_BASE_URL`). Install Chromium first with `pnpm exec playwright install chromium`. Browser checks cover responsive navigation, validation and service errors, and a mocked result workflow including comparison, report, clipboard, TXT download, history persistence/deletion and preference persistence. Mocked results exist only in test interception, never in the app.

## Deployment

The project is prepared for Vercel: install with pnpm, build with `pnpm build`, and serve `dist`. Vercel discovers `api/refine.ts` as a serverless endpoint; configure `GEMINI_API_KEY` and optional `GEMINI_MODEL` as server environment variables. Use a Node runtime supported by the installed SDK and allow a function duration of at least 100 seconds if your plan permits, because refinement and verification are sequential. Configure platform request-size/rate limits and abuse controls before a public launch.

`vercel.json` preserves the API endpoint and sends frontend routes to the SPA. Static-only hosting, including a cached/static Make publish, cannot run the Gemini endpoint without a separately deployed backend. No public deployment has been performed.

## Limitations and privacy

- Live rewriting requires a valid server-side Gemini key and network access.
- Automated verification is not a factual truth check or a guarantee. It compares against the original, not external evidence.
- Entity extraction is heuristic: single-word names and domain terminology can be missed; ambiguous matches require human review. Added or missing exact values trigger review.
- Long-document diffs use a bounded fallback rather than exhaustive alignment.
- Browser storage is best-effort and keeps up to 100 sessions. Clearing browser data removes history. Never submit sensitive information without authorization; text is sent to Google Gemini when refining.
- There is no authentication or cross-device synchronization. Clipboard/download availability depends on browser permissions.
- Production abuse protection, monitoring, accessibility/browser QA and live integration testing are still required before describing the service as production-ready.
