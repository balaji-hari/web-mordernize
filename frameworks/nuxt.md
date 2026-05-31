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

Node ≥ **20** required. Nuxt 3.x uses Vue 3 + Vite under the hood; the `nuxi` CLI replaces the older `create-nuxt-app`.

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

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 3000 | `npm install` | `npm run dev` | http://localhost:3000 |

## Recommendation context

Natural target for: `vue-2`, `angularjs-1` — teams that want Vue's mental model with SSR/SSG built in. Choose Nuxt over `vue3-vite` when SEO / static generation / data fetching conventions matter; choose plain `vue3-vite` for SPA-only apps.
