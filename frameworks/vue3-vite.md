---
name: vue3-vite
display_name: Vue 3 + Vite + TypeScript
role: target-ui
---

## Scaffold

```sh
npm create vite@latest apps/web-new -- --template vue-ts && cd apps/web-new && npm install
```

Node ≥ **22** required. Install Vue Router + Pinia if `migration.md §3` state management says so.

### Wire to API

Write `apps/web-new/.env.example` + `.env`:
```
VITE_API_URL=http://localhost:<api-port>
```
Write `apps/web-new/src/lib/api.ts`:
```ts
export const API_URL = import.meta.env.VITE_API_URL;
```

## Test framework

`vitest` (default). Same recipe as `react-vite-ts` but install `@testing-library/vue` instead of `@testing-library/react`.

Test smoke: `npm run test -- --run`.

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 5173 | `npm install` | `npm run dev` | http://localhost:5173 |

## Recommendation context

Gentle learning curve for teams coming from Angular or template-heavy MVC stacks. Pick when the team is already comfortable with template-driven UIs.
