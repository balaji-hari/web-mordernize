---
name: next-app-router
display_name: Next.js (App Router) + TypeScript
role: target-ui
---

## Scaffold

```sh
npx create-next-app@latest apps/web-new --typescript --tailwind --eslint --app --no-src-dir
```

Node ≥ **20.10** required. Adjust the `--tailwind` / `--eslint` flags per `migration.md §3` styling choices.

### Wire to API

Write `apps/web-new/.env.local.example` + `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:<api-port>
API_URL=http://localhost:<api-port>
```

The `NEXT_PUBLIC_` prefix is required for client-component fetches; the non-public `API_URL=` is for server-side fetches.

**If the API stack is `nestjs`**, use port **3001** for `<api-port>` — see `agents/permanent-gotchas.md` (Nest's default 3000 collides with Next).

## Test framework

`jest` (default for Next.js). Install: `npm i -D jest jest-environment-jsdom @types/jest ts-jest @testing-library/react @testing-library/jest-dom`. Write `jest.config.js` with `testEnvironment: "jsdom"`, `transform` via `ts-jest`, `collectCoverageFrom: ["src/**/*.{ts,tsx}"]`. Tests in `__tests__/` or colocated. Scripts: `"test": "jest --ci --runInBand"`, `"test:coverage": "jest --ci --coverage"`.

Test smoke: `npm test -- --ci --runInBand`.

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 3000 | `npm install` | `npm run dev` | http://localhost:3000 |

## Recommendation context

Natural target for: `aspnet-mvc`, `aspnet-core-mvc` (convention-over-config controllers map cleanly to file-based App Router routes). Pick when SEO matters (SSR/RSC), when the team is already used to .NET routing conventions, or when the migrated app needs many statically-rendered pages.
