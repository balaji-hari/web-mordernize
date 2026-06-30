---
name: react-vite-ts
display_name: React 18 + Vite + TypeScript
role: target-ui
---

## Scaffold

```sh
npm create vite@latest apps/web-new -- --template react-ts && cd apps/web-new && npm install
```

Node ≥ **22** required (Vite 7 dropped Node 18 and 20). Preflight the version before running the scaffolder.

After scaffold, replace `apps/web-new/src/App.tsx` with a placeholder reading `Legacy app migration in progress — managed by web-modernize plugin`.

Install libraries per `migration.md §3` "State management" + "Styling" (no version pins; `npm install` picks current).

### Wire to API (skip if `state.target_stack.api == "none"`)

Write `apps/web-new/.env.example` + `.env`:
```
VITE_API_URL=http://localhost:<api-port>
```
Write `apps/web-new/src/lib/api.ts`:
```ts
export const API_URL = import.meta.env.VITE_API_URL;
```
The migrator imports `API_URL` when porting fetch calls.

## Test framework

`vitest` (default). Install: `npm i -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom`. Write `vitest.config.ts` with `test.environment = "jsdom"`, `test.globals = true`, `test.coverage = { provider: "v8", reporter: ["text","json","html"], include: ["src/**"] }`. Tests colocated as `*.test.ts(x)`. Scripts: `"test": "vitest run"`, `"test:coverage": "vitest run --coverage"`.

Test smoke: `npm run test -- --run`.

## Dynamic tests

Read by `/web-modernize:scaffold` (when `migration.md §12` "Dynamic testing" is `yes`) and run by `/web-modernize:verify --dynamic` (advisory, never blocks).

- **E2E (Phase B):** `npm i -D @playwright/test && npx playwright install --with-deps chromium`. Write `playwright.config.ts` (`testDir: "e2e"`, `webServer` running `npm run dev` on 5173, `baseURL`). Script: `"test:e2e": "playwright test"`. verify.config `dynamic.e2e`: `npm --prefix ${ui_root} run test:e2e`.
  - **Per-unit authoring:** `/web-modernize:scaffold` writes ONE seed sample spec; thereafter `unit-migrator` §7d authors one spec per UI unit at `apps/web-new/e2e/<unit.id>.spec.ts` (keyed by **unit id**, not route, to avoid collisions when units share a route prefix), driven by the unit's `routes[]` + its `## Behaviour contract (Given/When/Then)`. Assert asset `src` resolution (`naturalWidth > 0`) and key-element/class visibility — **not** pixel diffs.
- **API replay (Phase A):** scaffold `apps/web-new/e2e/replay.mjs` (or under the API app) — reads recorded request/response fixtures from `${baseline_dir}`, replays each request against `VITE_API_URL`, and diffs the JSON response (status + body shape) against the recording; exits non-zero with a diff report on mismatch. verify.config `dynamic.api_replay`: `node apps/web-new/e2e/replay.mjs --baseline ${baseline_dir}`.
- **Baseline:** `/web-modernize:verify --capture-baseline` records the legacy app's responses into `${baseline_dir}` (`.claude/modernize/baseline/`, gitignored). Phase A skips with guidance until a baseline exists.

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 5173 | `npm install` | `npm run dev` | http://localhost:5173 |

## Integration

Read by `/web-modernize:integrate` to assemble the composed app from migrated units.

- **Central router:** `apps/web-new/src/router.tsx` — a React Router v6 `createBrowserRouter([...])` (or `<Routes>`) reconciled from each migrated UI unit's `routes[]`. Mount it inside the root layout the first unit established (`src/App.tsx` / see `notes/__layout__.md`), not a fresh tree.
- **Nav:** `apps/web-new/src/components/Nav.tsx` — built from the UI routes that carry a `label`, rendered in the layout. Preserve the legacy menu order/grouping recorded in `notes/__layout__.md`.
- **Strangler proxy (only when `strategy: strangler-fig`):** dev — add a `server.proxy` map in `vite.config.ts` routing not-yet-migrated path prefixes to the legacy origin; prod — emit an nginx (or equivalent) reverse-proxy config mapping **migrated** route prefixes → the new app and **everything else → legacy**. `/integrate` refreshes both as more units migrate.

## Recommendation context

Natural target for: `aspnet-webforms`, `aspnet-mvc`, `java-jsp`, `java-spring-mvc`, `java-struts`, `jquery-spaghetti`, `php-classic`, `coldfusion`, `vbscript-asp-classic` — broad ecosystem and the lowest-friction default when no other constraint applies.
