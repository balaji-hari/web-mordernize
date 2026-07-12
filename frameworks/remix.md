---
name: remix
display_name: Remix (React, server-first data routing) / React Router
role: target-ui
---

## Scaffold

```sh
npx create-remix@latest apps/web-new --template remix-run/remix/templates/remix --no-git-init --install
```

Preflight the Node version before scaffolding: resolve the scaffolder's current required Node floor (its docs/release notes) and verify local Node meets it — recent tool majors drop older Node LTS lines. Remix and React Router are now the same project — Remix's newer majors ship under the React Router name. New projects can choose either branding of the same underlying data-routing model:

- **Remix (Vite)**: command above — well-supported, conservative pick.
- **React Router framework mode**: `npx create-react-router@latest apps/web-new` — the newer shape; same data-routing model.

Both share the loader/action data-routing pattern; pick based on the team's preference for stability vs. latest. Check each CLI's current major before scaffolding — the shape (loaders/actions) is durable, the branding/version isn't.

### Wire to API

Write `apps/web-new/.env.example` + `.env`:
```
API_URL=http://localhost:<api-port>
```
Remix reads env vars on the server in `loader` / `action` functions via `process.env.API_URL`. Client-exposed config goes through the `RemixContext` pattern or window globals injected by the root loader.

## Test framework

`vitest` (default with Vite). Install: `npm i -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom`. Loaders and actions are pure functions — easy to unit-test directly.

Test smoke: `npm run test -- --run`.

## Verify commands

| Check | Command |
|---|---|
| lint | `npm --prefix ${ui_root} run lint` |
| typecheck | `npm --prefix ${ui_root} run typecheck` |
| test | `npm --prefix ${ui_root} test -- --run ${target_path}` |

## Dev server

| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| 3000 | `npm install` | `npm run dev` | http://localhost:3000 |

## Integration

Read by `/web-modernize:integrate`.

- **Central router:** Remix (classic) uses **file-based** routing under `apps/web-new/app/routes/` (flat-routes convention) — `/integrate` verifies each migrated UI unit owns a route module matching its `routes[]` entry, and flags any migrated unit with no corresponding route module (an orphan). React Router framework mode instead declares routes explicitly in `apps/web-new/app/routes.ts` — `/integrate` reconciles that array from each migrated unit's `routes[]`. Match whichever the team scaffolded.
- **Nav:** `apps/web-new/app/components/Nav.tsx` (rendered from the root layout the first unit established, `app/root.tsx` — see `notes/__layout__.md`) — built from migrated UI routes' labels, preserving legacy menu order.
- **Strangler proxy (only `strategy: strangler-fig`):** dev — add a `server.proxy` map in `vite.config.ts` (both branding options build on Vite) routing not-yet-migrated path prefixes to the legacy origin; prod — an upstream nginx (or equivalent) reverse-proxy config mapping migrated prefixes → the new app and everything else → legacy. `/integrate` refreshes both as more units migrate.

## Recommendation context

Pick when the migration is data-routing-heavy: lots of forms, server actions, progressive enhancement. The loader/action pattern is genuinely different from Next.js's RSC / `app router` approach — teams already used to "controllers that return data" (Rails, Django, Spring MVC, ASP.NET MVC) often find Remix's mental model the closest match in JavaScript-land.
