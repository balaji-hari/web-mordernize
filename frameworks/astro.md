---
name: astro
display_name: Astro (content-first, islands architecture)
role: target-ui
---

## Scaffold

```sh
npm create astro@latest apps/web-new -- --template minimal --typescript strict --no-install --no-git
cd apps/web-new && npm install
```

Preflight the Node version before scaffolding: resolve Astro's current required Node floor (its docs/release notes) and verify local Node meets it — recent tool majors drop older Node LTS lines. The `--template minimal` skips example content; switch to `--template basics` if the team wants the default starter pages. Add framework integrations as needed: `npx astro add react`, `npx astro add vue`, `npx astro add tailwind`.

### Wire to API

Write `apps/web-new/.env.example` + `.env`:
```
PUBLIC_API_URL=http://localhost:<api-port>
```
Astro exposes `PUBLIC_*` env vars to client code via `import.meta.env.PUBLIC_API_URL`. Write `apps/web-new/src/lib/api.ts`:
```ts
export const API_URL = import.meta.env.PUBLIC_API_URL;
```

## Test framework

`vitest` (default for Astro). Install: `npm i -D vitest @vitest/coverage-v8 jsdom`. Astro provides its own testing helpers via `astro/test-utils` for component tests; for page integration tests use `astro:test` (still experimental in some versions — fall back to Playwright for E2E).

Test smoke: `npm run test -- --run`.

## Verify commands

| Check | Command |
|---|---|
| lint | `npm --prefix ${ui_root} run lint` (Astro doesn't scaffold ESLint by default — add it if the team wants a lint gate) |
| typecheck | `npx astro check` (Astro's own diagnostics tool — type-checks `.astro` files plus TS, which plain `tsc` can't do) |
| test | `npm --prefix ${ui_root} test -- --run ${target_path}` |

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 4321 | `npm install` | `npm run dev` | http://localhost:4321 |

## Integration

Read by `/web-modernize:integrate`.

- **Central router:** Astro routing is **file-based** (`apps/web-new/src/pages/`) — there's no single router file to reconcile; `/integrate` verifies each migrated UI unit owns a page file (`.astro`, `.md`, or `.mdx`) matching its `routes[]` entry, and flags any migrated unit with no corresponding page file (an orphan).
- **Nav:** `apps/web-new/src/components/Nav.astro` (rendered from the shared layout the first unit established, `src/layouts/Layout.astro` — see `notes/__layout__.md`) — built from migrated UI routes' labels, preserving legacy menu order.
- **Strangler proxy (only `strategy: strangler-fig`):** dev — add a `vite: { server: { proxy: {...} } }` block in `astro.config.mjs` (Astro's dev server runs on Vite) routing not-yet-migrated path prefixes to the legacy origin; prod — an upstream nginx (or equivalent) reverse-proxy config mapping migrated route prefixes → the new app and everything else → legacy. `/integrate` refreshes both as more units migrate.

## Recommendation context

Strong target for: `wordpress` (when migrating to a headless CMS setup), `php-classic`, `coldfusion`, and any other content-heavy server-rendered legacy stack. Astro's islands architecture is ideal when most pages are static content with sparse interactive widgets.

Less suited for highly-interactive SPA-style apps — pick `react-vite-ts` or `next-app-router` for those.
