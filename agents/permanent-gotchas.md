---
description: >
  Read-only catalog of bugs the agent cannot reliably discover on its own —
  first-run crashes, silently-wrong behavior, or load-bearing durable rules
  whose root cause isn't obviously web-searchable. Everything else (version
  bumps, well-documented deprecations, framework guides) belongs to WebSearch
  at scaffold time, not this file.
disable-model-invocation: true
model: inherit
---

# Permanent gotchas

Audit criterion: an entry stays here **only if the agent can't reach the conclusion in <30s with one WebSearch.** That usually means the bug crashes before the symptom is searchable, or the failure is silent (no error to search for). Well-documented framework changes (Pydantic v1→v2, `'use client'`, Svelte 5 runes, package renames, CLI flag deprecations) don't live here — the agent finds them on demand.

---

## Python / FastAPI

### Hatchling editable install fails when project name doesn't match directory name

**Symptom:** `pip install -e ".[dev]"` fails with `ValueError: Unable to determine which files to ship inside the wheel`, even though `[tool.hatch.build.targets.wheel] packages = ["app"]` is set.

**Root cause:** hatchling's `only_include` config uses `dict.get("only-include", self.default_only_include())`. Python evaluates the default arg eagerly, so `default_only_include()` runs every time — and it raises when no directory matches the normalized project name (`api-new` → `api_new`, but the package directory is `app/`).

**Fix:** Set `only-include` explicitly on both wheel and editable targets. The redundancy is load-bearing. See `templates/permanent-gotchas/fastapi/pyproject.toml` — the only template file kept in v0.9.0, because reconstructing this from prose has bitten previous migrations.

### `passlib[bcrypt]` is broken under bcrypt ≥ 4.0

**Symptom:** First call to `pwd_context.hash(password)` raises `ValueError: password cannot be longer than 72 bytes`, regardless of the caller's password length.

**Root cause:** Passlib (last release 2020, unmaintained) runs a one-time `detect_wrap_bug()` on first use, calling `bcrypt.hashpw` with a 73-byte test secret. bcrypt 4.x raises on > 72 bytes instead of silently truncating. Passlib doesn't catch the exception → first hash call crashes.

**Fix:** **Never use `passlib[bcrypt]` for any new Python migration.** Use the `bcrypt` package directly with explicit 72-byte truncation in a `_prep()` helper. Example skeleton (the agent should regenerate, not copy):

```python
import bcrypt

def _prep(password: str) -> bytes:
    encoded = password.encode("utf-8")
    return encoded[:72]  # bcrypt 4.x raises on > 72 bytes; truncating doesn't reduce entropy

def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prep(password), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prep(password), hashed.encode("utf-8"))
```

If the team needs arbitrary-length passwords, replace `_prep` with a SHA-256 pre-hash. Document the choice in `notes/__auth__.md`.

---

## Java / Spring Boot

### Spring Boot's `/health` is at `/actuator/health`, not `/health`

**Symptom:** Smoke gate (or any caller) hitting `/health` gets 404, even though `spring-boot-starter-actuator` is on the classpath.

**Why this stays:** The smoke gate silently passes the install+build step then 404s on the health probe — easy to misread as a bug in the gate rather than a path mismatch. Once you know the rule, it's obvious; before you know it, you debug the wrong layer.

**Fix:** Write an explicit `@RestController` for `/health` rather than relying on actuator matching the smoke URL. Skeleton:

```java
@RestController
public class HealthController {
    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }
}
```

Put it under the project's base package so `@SpringBootApplication`'s component scan picks it up.

---

## TypeScript / NestJS

### `reflect-metadata` must be the first import in `main.ts`

**Symptom:** `Reflect.getMetadata is not a function` at startup, **or** silent DI failures with `undefined` providers — depends on which decorator-annotated class is parsed first.

**Root cause:** Nest's DI relies on the `reflect-metadata` polyfill being loaded before any decorator-annotated class is parsed. The Nest CLI puts it first; the migrator must not remove or reorder it when porting.

**Fix:** Keep `import 'reflect-metadata';` as **the very first line** of `apps/api-new/src/main.ts`. Above every other import. Above any comment block that the migrator might re-emit at the top of the file.

### Nest default port collides with Next.js dev

**Symptom:** Running Next.js (port 3000) + NestJS (also 3000 by default) → second one fails with `EADDRINUSE`, or — worse — the request hits the wrong server.

**Fix:** Bind Nest to **3001** by default: `await app.listen(process.env.PORT ?? 3001);`. Reflect 3001 in every UI ↔ API wiring step (`.env.local`, dev proxy config). This isn't a version-sensitive choice — Nest's default has been 3000 for years and Next's default is unlikely to move.

---

## Cross-cutting

### Page-wrapping chrome and global stylesheets aren't "units"

**Symptom (chrome):** migrated pages render bare — no header, no footer, no nav. The legacy app's chrome silently disappears.

**Symptom (CSS):** legacy CSS was copied to `public/` (or `assets/`) by `/scaffold`, but the migrated app shows partial / no styling — some rules apply, most don't.

**Root cause:** every legacy stack has a "wraps every page" template plus global stylesheets, and neither shows up as a unit in `/plan` because they aren't standalone content. Shape varies, the pattern is universal:

| Legacy stack | Wrapping template | Global stylesheet location |
|---|---|---|
| ASP.NET WebForms | `Site.master` | `Content/site.css`, `Styles/*.css` |
| ASP.NET MVC / Razor | `Views/Shared/_Layout.cshtml` | `Content/site.css`, `wwwroot/css/site.css` |
| JSP | `header.jsp` + `footer.jsp` via `<jsp:include>` | `src/main/webapp/resources/css/*.css` |
| ColdFusion | `<cfinclude template="...">` chrome files | `assets/css/*.css` |
| Struts | tile definitions in `tiles.xml` | `WebContent/styles/*.css` |
| AngularJS 1.x | `index.html` body shell | `assets/styles/*.css` |
| Classic PHP | `include 'header.php'` / `'footer.php'` | `assets/css/*.css` |

Bundlers (Vite, Next, Angular CLI) serve `public/` as static assets but don't auto-import stylesheets into the JS bundle. Many legacy designs cascade off a body-level wrapper class (`<body class="esh-shop">`); the new `index.html` doesn't carry it, so any rule scoped to `body.<class> ...` silently does nothing.

**Fix on the first feature unit** (before the first content page lands; subsequent units inherit the result):

1. Identify the legacy wrapping template using the table above as a starting point; if the legacy stack isn't listed, search for files that are `include`d / referenced from every content page.
2. Translate it into the target's root layout file:
   - React/Vite → wrap `<App />` in `apps/web-new/src/App.tsx` with `<Header />` + `<Outlet />` + `<Footer />`
   - Next.js → write `apps/web-new/app/layout.tsx`
   - Angular → edit `apps/web-new/src/app/app.component.html`
   - SvelteKit → write `apps/web-new/src/routes/+layout.svelte`
3. Import every global stylesheet from the entry file (`main.tsx` / `app/layout.tsx` / `app.config.ts` / `+layout.svelte`). `public/` doesn't auto-import.
4. Preserve the legacy body wrapper class — set it on `<html>` in `index.html` or on the root component's outermost element.
5. Order: legacy CSS imports go **after** framework defaults (Tailwind preflight, Material CSS reset) so legacy rules win the cascade for class-scoped selectors.
6. Record what was done in `notes/__layout__.md` so subsequent units don't redo it.

This rule is shape-agnostic on purpose. New legacy stacks (PHP, ColdFusion, Struts, Razor) hit the same pattern — Claude identifies the wrapping template + global CSS for whatever the team's source happens to be and applies the same five steps.

### A config-referenced value missing from the target config breaks silently

**Symptom:** the app builds, typechecks, and parity review passes, but at runtime something is quietly wrong — every product image renders broken, a base URL resolves to a bare filename, a feature toggle reads `false`, a link points nowhere. No error, no failed test.

**Root cause:** legacy code reads a config value (an `appSettings`/`Web.config` key, `application.properties` entry, env var) and the migration ports the *code* that reads it but never carries the *value* into the target config (`appsettings*.json`, `.env`, `application.yml`). The key resolves to null/empty, the code takes a fallback path, and the result looks plausible but wrong. A static parity review compares code, not config files, so it can't see the gap; a build doesn't exercise the value.

**Fix (shape-agnostic):** for every config key the migrated code references, confirm the key exists **with a value** in the target config and carry the legacy default across. If no safe default exists, add an explicit `// TODO: set <key>` placeholder and record it in `notes/<unit.id>.md` under "Gotchas — config carried over". The runtime counterpart is the asset-resolution assertion in the unit's E2E spec (`unit-migrator` §7d) — `naturalWidth > 0` catches the broken-image case that a missing image-base-URL key produces.

### A migration that compiles can still look wrong — compare against the legacy, don't just re-style

**Symptom:** the new page works and the data is correct, but it doesn't look like the old page — spacing, colours, layout, or whole decorative classes are gone. No error; the team only notices on a side-by-side glance.

**Root cause:** translating markup + logic without porting the legacy stylesheets and class semantics produces a clean-room redesign, not a migration. The visual definition lives in CSS the migrator didn't read or silently flattened to generic utilities.

**Fix:** follow `unit-migrator` §7b — read every stylesheet the source depends on, detect the legacy design system (class-name prefixes), and preserve the *semantic class names and visual result* when translating to the target styling system (don't flatten custom classes to anonymous utilities). When in doubt, compare the rendered target against the legacy and reconcile the difference rather than inventing a new look. The E2E spec (§7d) asserts the key legacy elements/classes are present so dropped chrome surfaces at runtime; pixel-diff visual regression remains out of scope.

### CORS and `/health` are on the agent

No default API scaffold (`dotnet new webapi`, `nest new`, Spring Initializr, FastAPI from scratch) serves `GET /health` returning 200, and none configure CORS for the dev UI ports. The scaffold smoke gate hits `/health` and the dev UI hits the API cross-origin, so both must be wired up at scaffold time. The agent generates the right shape per stack — no template files for this.

Standard dev allow-list: `http://localhost:5173` (Vite), `http://localhost:3000` (Next), `http://localhost:4200` (Angular). Tighten before any non-local deploy.

---

## Sandbox / environment

### `npm install` fails with `EALLOWSCRIPTS` inside the Claude Code sandbox

**Symptom:** IF `npm install` (or `npm ci`) fails with an `EALLOWSCRIPTS` error — even for a project that never enabled `ignore-scripts` or referenced `allow-scripts` itself — THEN unset `npm_config_allow_scripts` and `NPM_CONFIG_ALLOW_SCRIPTS` for that command and retry.

**Root cause:** where the Claude Code sandbox's global `.npmrc` sets `allow-scripts=@anthropic-ai/claude-code` (so Claude Code's own installer can run its lifecycle scripts), npm's `resolve-allow-scripts.js` treats the `npm_config_allow_scripts` / `NPM_CONFIG_ALLOW_SCRIPTS` env var as a CLI-level policy and rejects it outright for any project-scoped install — regardless of what the project itself declares. This applies to **any** Node-based scaffold run inside such a sandbox (NestJS, Express, Hono, or a Vite/Next/Angular UI — not specific to one framework or source stack), and it only applies where the environment actually sets that `.npmrc` line; an environment without it won't hit this.

**Fix:**

```sh
unset npm_config_allow_scripts NPM_CONFIG_ALLOW_SCRIPTS
npm install
```

(PowerShell: `Remove-Item Env:npm_config_allow_scripts, Env:NPM_CONFIG_ALLOW_SCRIPTS -ErrorAction SilentlyContinue`.) Re-run whichever `npm install`/`npm ci` step failed once the vars are cleared.

---

## Adding a new entry

Before adding: ask whether a smart agent could reach this fix in ~30 seconds with one WebSearch. If yes, the entry doesn't belong here — leave it for the scaffold-time agent to discover. If the bug crashes before a search would naturally happen, or the symptom is silent (no error to search for), it belongs here.

When something does qualify, write it **version-agnostic** — describe the root cause and the durable fix shape, not "as of <date>". Entries with embedded version numbers go stale; entries with root causes don't.
