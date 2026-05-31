---
name: svelte-kit
display_name: SvelteKit (Svelte 5)
role: target-ui
---

## Scaffold

```sh
npx sv create apps/web-new
```

Node ≥ **22** required. Pick the `minimal` template + TypeScript non-interactively. The `sv` CLI ships with Svelte 5 / SvelteKit 2 (the older `create-svelte` CLI is retired).

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

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 5173 | `npm install` | `npm run dev` | http://localhost:5173 |

## Recommendation context

Pick when the team values minimal boilerplate, fast HMR, and a single-file-component model. Good fit for migrating small-to-medium content-heavy apps where SSR is nice-to-have rather than essential.
