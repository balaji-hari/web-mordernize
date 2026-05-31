---
name: nestjs
display_name: NestJS (TypeScript)
role: target-api
---

## Scaffold

```sh
npm i -g @nestjs/cli
nest new apps/api-new --package-manager npm --skip-git --skip-install
cd apps/api-new && npm install
```

On locked-down boxes substitute `npx @nestjs/cli new apps/api-new`.

Then rewrite `apps/api-new/src/main.ts` so that:

- `import 'reflect-metadata';` is the **very first line** (above every other import) — see `agents/permanent-gotchas.md`. Omitting it crashes Nest at startup.
- `app.enableCors({ origin: [<dev allow-list>], credentials: true })` is called before `app.listen`. Dev allow-list: `http://localhost:5173`, `http://localhost:3000`, `http://localhost:4200`.
- `app.listen(process.env.PORT ?? 3001)` binds to **3001**, not Nest's default 3000 (which collides with Next.js dev). See `agents/permanent-gotchas.md`.

Add a `/health` route to the generated `app.controller.ts`:
```ts
@Get('health') health() { return { status: 'UP' }; }
```

## Test framework

`jest` (ships with `nest new`). Verify `package.json` has the `jest` block. Add coverage by ensuring `collectCoverageFrom` is configured. Scripts: `"test": "jest --ci --runInBand"`, `"test:coverage": "jest --ci --coverage"`.

Sample test at `__tests__/app.spec.ts` asserting `/health` returns 200.

Test smoke: `npm test -- --ci --runInBand`.

## Auth notes

Use **`bcrypt`** (npm) — well-maintained, native binding. Acceptable alternate: **`argon2`** for teams that prefer Argon2id over bcrypt.

**Avoid `bcryptjs`** — pure-JS implementation, much slower than the native `bcrypt` binding for high-throughput auth.

Seed dev users via `apps/api-new/scripts/seed-dev-users.ts`, run with `npx ts-node scripts/seed-dev-users.ts`. Gate on `NODE_ENV !== 'production'`.

Refer to `agents/permanent-gotchas.md` for cross-cutting auth rules (bcrypt 72-byte truncation).

## Dev server

| Dev port | Install/activate | Dev command | URL | Health check |
|---|---|---|---|---|
| 3001 | `npm install` | `npm run start:dev` | http://localhost:3001 | `curl http://localhost:3001/health` |

Note: 3001 (not 3000) — Nest's default collides with Next.js. The port choice is intentional and documented in `agents/permanent-gotchas.md`.

## Recommendation context

Pick when the team is already strong in TypeScript and wants a single-language stack (TS on UI + API). Strong opinionated structure (modules, providers, decorators) helps teams new to Node-side architecture.
