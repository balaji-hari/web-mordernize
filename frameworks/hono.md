---
name: hono
display_name: Hono (modern lightweight Node / edge API)
role: target-api
---

## Scaffold

```sh
npm create hono@latest apps/api-new -- --template nodejs --pm npm --install
cd apps/api-new
```

Preflight the Node version before scaffolding: resolve the scaffolder's current required Node floor (its docs/release notes) and verify local Node meets it — recent tool majors drop older Node LTS lines. The `npm create hono@latest` CLI prompts for a runtime template — pick `nodejs` (or `bun`, `deno`, `cloudflare-workers`, `vercel`, `aws-lambda`, etc. based on deployment target).

Then edit `apps/api-new/src/index.ts` to add CORS + `/health`:
```ts
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { serve } from '@hono/node-server';

const app = new Hono();

app.use('/*', cors({
  origin: ['http://localhost:5173', 'http://localhost:3000', 'http://localhost:4200'],
  credentials: true,
}));

app.get('/health', (c) => c.json({ status: 'UP' }));

serve({ fetch: app.fetch, port: 3001 });
```

Port **3001** to avoid colliding with Next.js's default 3000.

## Test framework

`vitest` (default). Install: `npm i -D vitest @vitest/coverage-v8`. Hono apps test cleanly via the framework's `app.request()` method — no HTTP server boot needed:
```ts
import { app } from '../src/index';
test('GET /health', async () => {
  const res = await app.request('/health');
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual({ status: 'UP' });
});
```

Test smoke: `npm run test -- --run`.

## Verify commands

| Check | Command |
|---|---|
| lint | `npm --prefix ${api_root} run lint` |
| typecheck | `npm --prefix ${api_root} run typecheck` |
| test | `npm --prefix ${api_root} test -- ${target_path}` |

## Auth notes

Hono provides built-in middleware for `bearerAuth`, `basicAuth`, and `jwt` (via `hono/jwt`). For password hashing use **`bcrypt`** (npm). For more elaborate auth flows, consider `@hono/auth-js` (Lucia / Auth.js integration).

Refer to `agents/permanent-gotchas.md` for cross-cutting auth rules (bcrypt 72-byte truncation, JWT pitfalls).

## Data migration

Hono is ORM-agnostic — this framework file doesn't prescribe one; the real choice is made by the `data` foundation concern (see `agents/cross-cutting-migrator.md`). The commands below assume the common default, **Prisma**, as a starting point, not a mandate:

Apply: `npx prisma migrate deploy`
Status (read-only reachability probe): `npx prisma migrate status`

## Dev server

| Dev port | Install/activate | Dev command | URL | Health check |
|---|---|---|---|---|
| 3001 | `npm install` | `npm run dev` | http://localhost:3001 | `curl http://localhost:3001/health` |

## Recommendation context

Pick when the API will deploy to an edge runtime (Cloudflare Workers, Vercel Edge, Deno Deploy, Bun) or when bundle size / cold-start latency matters. Hono is significantly faster and smaller than Express or NestJS.

Choose `express` instead for pragmatic Node-only deployments with maximum middleware ecosystem. Choose `nestjs` for opinionated enterprise structure.
