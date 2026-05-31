---
name: express
display_name: Express.js (Node API workhorse)
role: target-api
---

## Scaffold

Express has no opinionated scaffolder (the official `express-generator` is older and out of fashion). Recommended approach is a manual scaffold:

```sh
mkdir -p apps/api-new && cd apps/api-new
npm init -y
npm i express cors dotenv
npm i -D typescript @types/express @types/cors @types/node ts-node-dev
npx tsc --init
```

Then write `apps/api-new/src/index.ts`:
```ts
import 'dotenv/config';
import express from 'express';
import cors from 'cors';

const app = express();
const PORT = process.env.PORT ?? 3001;

app.use(cors({
  origin: ['http://localhost:5173', 'http://localhost:3000', 'http://localhost:4200'],
  credentials: true,
}));
app.use(express.json());

app.get('/health', (_req, res) => res.json({ status: 'UP' }));

app.listen(PORT, () => console.log(`API listening on :${PORT}`));
```

Add `package.json` scripts:
```json
{
  "scripts": {
    "dev": "ts-node-dev --respawn --transpile-only src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  }
}
```

Port **3001** to avoid colliding with Next.js's default 3000 (same rule as NestJS).

## Test framework

`vitest` (default for new Node projects) or `jest`. Install: `npm i -D vitest @vitest/coverage-v8 supertest @types/supertest`. Use `supertest` for HTTP-level tests against the Express app instance.

Sample `tests/health.test.ts`:
```ts
import request from 'supertest';
import { app } from '../src/index';
test('GET /health', async () => {
  const res = await request(app).get('/health');
  expect(res.status).toBe(200);
  expect(res.body).toEqual({ status: 'UP' });
});
```

Test smoke: `npm run test -- --run`.

## Auth notes

Use **`bcrypt`** (npm, native binding) for password hashing. Auth middleware patterns: `jsonwebtoken` for JWT, `express-session` for cookie sessions, `passport` only if integrating with a third-party IdP (otherwise it's overkill).

Avoid `bcryptjs` (pure-JS, much slower than native `bcrypt`).

Refer to `agents/permanent-gotchas.md` for cross-cutting auth rules (bcrypt 72-byte truncation, CSRF, etc.).

## Dev server

| Dev port | Install/activate | Dev command | URL | Health check |
|---|---|---|---|---|
| 3001 | `npm install` | `npm run dev` | http://localhost:3001 | `curl http://localhost:3001/health` |

## Recommendation context

Pick when the team wants the most-pragmatic Node API choice — no framework opinions, vast middleware ecosystem, minimal cognitive overhead. Good fit for migrating off old Node API stacks (Hapi, Restify, older Express) or as the API behind a JavaScript-first frontend stack.

Choose `nestjs` instead if the team wants strong opinionation (DI, modules, decorators). Choose `hono` for ultra-lightweight / edge-deployment scenarios.
