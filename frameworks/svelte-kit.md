---
name: svelte-kit
display_name: SvelteKit
role: target-ui
---

## Scaffold

```sh
npx sv create apps/web-new
```

Preflight the Node version before scaffolding: resolve SvelteKit's current required Node floor (its docs/release notes) and verify local Node meets it — recent tool majors drop older Node LTS lines. Pick the `minimal` template + TypeScript non-interactively. The `sv` CLI is the current official scaffolding tool (the older `create-svelte` CLI is retired).

### Wire to API

Write `apps/web-new/.env.example` + `.env`:
```
PUBLIC_API_URL=http://localhost:<api-port>
```
Write `apps/web-new/src/lib/api.ts`:
```ts
import { PUBLIC_API_URL } from '$env/static/public';
export const API_URL = PUBLIC_API_URL;
```

## Test framework

`vitest` (default). Same recipe as `react-vite-ts` but install `@testing-library/svelte` instead of `@testing-library/react`. Sample test at `src/App.spec.ts`.

Test smoke: `npm run test -- --run`.

## Verify commands

| Check | Command |
|---|---|
| lint | `npm --prefix ${ui_root} run lint` (the `sv create` CLI can add ESLint + Prettier interactively — make sure the team picked that option) |
| typecheck | `npx svelte-check --tsconfig ./tsconfig.json` (SvelteKit's own type-checking tool — plain `tsc` can't check `.svelte` files) |
| test | `npm --prefix ${ui_root} test -- --run ${target_path}` |

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 5173 | `npm install` | `npm run dev` | http://localhost:5173 |

## Integration

Read by `/web-modernize:integrate`.

- **Central router:** SvelteKit routing is **file-based** (`apps/web-new/src/routes/`) — there's no single router file to reconcile; `/integrate` verifies each migrated UI unit owns a `+page.svelte` (plus `+page.ts`/`+page.server.ts` if needed) under the route folder matching its `routes[]` entry, and flags any migrated unit with no corresponding route folder (an orphan).
- **Nav:** `apps/web-new/src/lib/components/Nav.svelte` (rendered from the shared layout the first unit established, `src/routes/+layout.svelte` — see `notes/__layout__.md`) — built from migrated UI routes' labels, preserving legacy menu order.
- **Strangler proxy (only `strategy: strangler-fig`):** dev — add a `server.proxy` map in `vite.config.ts` routing not-yet-migrated path prefixes to the legacy origin; prod — an upstream nginx (or equivalent) reverse-proxy config, or a `hooks.server.ts` `handle` hook that forwards unmatched prefixes to the legacy origin. `/integrate` refreshes both as more units migrate.

## Recommendation context

Pick when the team values minimal boilerplate, fast HMR, and a single-file-component model. Good fit for migrating small-to-medium content-heavy apps where SSR is nice-to-have rather than essential.
