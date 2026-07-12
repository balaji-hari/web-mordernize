---
name: nuxt
display_name: Nuxt (Vue meta-framework, SSR/SSG)
role: target-ui
---

## Scaffold

```sh
npx nuxi@latest init apps/web-new --packageManager npm --no-gitInit
cd apps/web-new && npm install
```

Preflight the Node version before scaffolding: resolve Nuxt's current required Node floor (its docs/release notes) and verify local Node meets it — recent tool majors drop older Node LTS lines. Nuxt uses Vue 3 + Vite under the hood; the `nuxi` CLI is the current official scaffolding tool (it replaced the older `create-nuxt-app`).

### Wire to API

Write `apps/web-new/.env.example` + `.env`:
```
NUXT_PUBLIC_API_URL=http://localhost:<api-port>
```
Nuxt exposes runtime config via `useRuntimeConfig()`. Add to `nuxt.config.ts`:
```ts
export default defineNuxtConfig({
  runtimeConfig: { public: { apiUrl: process.env.NUXT_PUBLIC_API_URL ?? 'http://localhost:8000' } }
});
```
Then in any component / page:
```ts
const { apiUrl } = useRuntimeConfig().public;
```

## Test framework

`vitest` (default). Install: `npm i -D vitest @vitest/coverage-v8 @nuxt/test-utils happy-dom`. Use `@nuxt/test-utils/runtime` for unit tests that need the Nuxt context; for component-only tests `@vue/test-utils` works directly.

Test smoke: `npm run test -- --run`.

## Verify commands

| Check | Command |
|---|---|
| lint | `npm --prefix ${ui_root} run lint` (Nuxt doesn't scaffold ESLint by default — add the `@nuxt/eslint` module if the team wants a lint gate) |
| typecheck | `npx nuxi typecheck` (Nuxt's own CLI command — runs `vue-tsc` under the hood, which plain `tsc` can't do for `.vue` files) |
| test | `npm --prefix ${ui_root} test -- --run ${target_path}` |

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 3000 | `npm install` | `npm run dev` | http://localhost:3000 |

## Integration

Read by `/web-modernize:integrate`.

- **Central router:** Nuxt routing is **file-based** (auto-generated Vue Router config from `apps/web-new/pages/`) — there's no single router file to reconcile; `/integrate` verifies each migrated UI unit owns a page file (`pages/<route>.vue`) matching its `routes[]` entry, and flags any migrated unit with no corresponding page file (an orphan).
- **Nav:** `apps/web-new/components/Nav.vue` (rendered from the shared layout the first unit established, `layouts/default.vue` — see `notes/__layout__.md`) — built from migrated UI routes' labels, preserving legacy menu order.
- **Strangler proxy (only `strategy: strangler-fig`):** dev — add a `vite: { server: { proxy: {...} } }` map in `nuxt.config.ts`; prod — Nitro's `routeRules` (e.g. `{ '/legacy-prefix/**': { proxy: 'https://legacy-origin/**' } }` in `nuxt.config.ts`) or an upstream nginx config, mapping migrated prefixes to the new app and everything else to legacy. `/integrate` refreshes both as more units migrate.

## Recommendation context

Natural target for: `vue-2`, `angularjs-1` — teams that want Vue's mental model with SSR/SSG built in. Choose Nuxt over `vue3-vite` when SEO / static generation / data fetching conventions matter; choose plain `vue3-vite` for SPA-only apps.
