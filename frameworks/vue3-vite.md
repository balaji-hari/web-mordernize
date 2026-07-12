---
name: vue3-vite
display_name: Vue 3 + Vite + TypeScript
role: target-ui
---

## Scaffold

```sh
npm create vite@latest apps/web-new -- --template vue-ts && cd apps/web-new && npm install
```

Preflight the Node version before scaffolding: resolve the scaffolder's current required Node floor (its docs/release notes) and verify local Node meets it — recent tool majors drop older Node LTS lines. Install Vue Router + Pinia if `migration.md §3` state management says so.

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

## Verify commands

| Check | Command |
|---|---|
| lint | `npm --prefix ${ui_root} run lint` |
| typecheck | `npm --prefix ${ui_root} run typecheck` (wires to `vue-tsc --noEmit` — plain `tsc` can't check `.vue` single-file components) |
| test | `npm --prefix ${ui_root} test -- --run ${target_path}` |

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 5173 | `npm install` | `npm run dev` | http://localhost:5173 |

## Integration

Read by `/web-modernize:integrate` to assemble the composed app from migrated units.

- **Central router:** `apps/web-new/src/router/index.ts` — a Vue Router `createRouter({ history: createWebHistory(), routes: [...] })` reconciled from each migrated UI unit's `routes[]`. Wire it via `app.use(router)` in `src/main.ts`, inside the root layout the first unit established (`src/App.vue` — see `notes/__layout__.md`), not a fresh tree.
- **Nav:** `apps/web-new/src/components/Nav.vue` — built from the UI routes that carry a `label`, rendered in the layout. Preserve the legacy menu order/grouping recorded in `notes/__layout__.md`.
- **Strangler proxy (only when `strategy: strangler-fig`):** dev — add a `server.proxy` map in `vite.config.ts` routing not-yet-migrated path prefixes to the legacy origin; prod — emit an nginx (or equivalent) reverse-proxy config mapping **migrated** route prefixes → the new app and **everything else → legacy**. `/integrate` refreshes both as more units migrate.

## Recommendation context

Gentle learning curve for teams coming from Angular or template-heavy MVC stacks. Pick when the team is already comfortable with template-driven UIs.
