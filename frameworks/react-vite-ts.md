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

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 5173 | `npm install` | `npm run dev` | http://localhost:5173 |

## Recommendation context

Natural target for: `aspnet-webforms`, `aspnet-mvc`, `java-jsp`, `java-spring-mvc`, `java-struts`, `jquery-spaghetti`, `php-classic`, `coldfusion`, `vbscript-asp-classic` — broad ecosystem and the lowest-friction default when no other constraint applies.
