---
name: remix
display_name: Remix (React, server-first data routing) / React Router v7
role: target-ui
---

## Scaffold

```sh
npx create-remix@latest apps/web-new --template remix-run/remix/templates/remix --no-git-init --install
```

Node ≥ **20** required. As of 2024–2025, Remix has merged with React Router; the official Remix v3 is being shipped as React Router v7. New projects can choose either path:

- **Remix v2 (Vite)**: command above — well-supported, conservative pick.
- **React Router v7 framework mode**: `npx create-react-router@latest apps/web-new` — the newer shape; same data-routing model.

Both share the loader/action data-routing pattern; pick based on the team's preference for stability vs. latest.

### Wire to API

Write `apps/web-new/.env.example` + `.env`:
```
API_URL=http://localhost:<api-port>
```
Remix reads env vars on the server in `loader` / `action` functions via `process.env.API_URL`. Client-exposed config goes through the `RemixContext` pattern or window globals injected by the root loader.

## Test framework

`vitest` (default with Vite). Install: `npm i -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom`. Loaders and actions are pure functions — easy to unit-test directly.

Test smoke: `npm run test -- --run`.

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 3000 | `npm install` | `npm run dev` | http://localhost:3000 |

## Recommendation context

Pick when the migration is data-routing-heavy: lots of forms, server actions, progressive enhancement. The loader/action pattern is genuinely different from Next.js's RSC / `app router` approach — teams already used to "controllers that return data" (Rails, Django, Spring MVC, ASP.NET MVC) often find Remix's mental model the closest match in JavaScript-land.
