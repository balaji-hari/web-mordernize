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

Node ≥ **20** required. The `--template minimal` skips example content; switch to `--template basics` if the team wants the default starter pages. Add framework integrations as needed: `npx astro add react`, `npx astro add vue`, `npx astro add tailwind`.

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

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 4321 | `npm install` | `npm run dev` | http://localhost:4321 |

## Recommendation context

Strong target for: `wordpress` (when migrating to a headless CMS setup), `php-classic`, `coldfusion`, and any other content-heavy server-rendered legacy stack. Astro's islands architecture is ideal when most pages are static content with sparse interactive widgets.

Less suited for highly-interactive SPA-style apps — pick `react-vite-ts` or `next-app-router` for those.
