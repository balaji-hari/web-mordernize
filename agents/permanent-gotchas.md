---
description: >
  Read-only catalog of durable, version-agnostic bugs and workarounds the
  scaffolder and unit-migrator have encountered. Each entry documents a tool
  or library quirk that Claude cannot reliably discover on its own (training
  cutoff, library is abandoned, or behavior is silent/cryptic). The /scaffold
  skill and the unit-migrator agent reference this file rather than inlining
  fixes that age fast.
disable-model-invocation: true
model: inherit
---

# Permanent gotchas

This file lists tool/library quirks that bit a previous migration. Each entry is **version-agnostic** — the underlying behavior doesn't depend on a specific framework version. Update an entry only when the quirk's root cause changes; do **not** add "X is current as of <date>" notes that go stale.

Use it as a checklist when scaffolding a target or translating a unit: if the stack you're emitting code for has an entry here, encode the workaround inline. The companion `templates/permanent-gotchas/<stack>/` directory carries the concrete file shapes.

---

## Python / FastAPI

### Hatchling editable install fails when project name doesn't match directory name

**Symptom:** `pip install -e ".[dev]"` fails with `ValueError: Unable to determine which files to ship inside the wheel`, even though `[tool.hatch.build.targets.wheel] packages = ["app"]` is set.

**Root cause:** hatchling's `only_include` config property uses `dict.get("only-include", self.default_only_include())`. Python evaluates the default arg eagerly, so `default_only_include()` runs every time — and it raises when no directory matches the normalized project name (`api-new` → `api_new`, but the package directory is `app/`).

**Fix:** Set `only-include` explicitly on both wheel and editable targets:

```toml
[tool.hatch.build.targets.wheel]
packages = ["app"]
only-include = ["app"]

[tool.hatch.build.targets.editable]
packages = ["app"]
only-include = ["app"]
```

The redundancy is load-bearing — both `only-include` lines are required.

### `passlib[bcrypt]` is broken under bcrypt ≥4.0

**Symptom:** First call to `pwd_context.hash(password)` raises `ValueError: password cannot be longer than 72 bytes`, regardless of the caller's password length.

**Root cause:** Passlib (last release 2020, unmaintained) runs a one-time `detect_wrap_bug()` on first use, calling `bcrypt.hashpw` with a 73-byte test secret. bcrypt 4.x raises on >72 bytes instead of silently truncating. Passlib doesn't catch the exception → first hash call crashes.

**Fix:** **Never use `passlib[bcrypt]`.** Use the `bcrypt` package directly with explicit 72-byte truncation. See `templates/permanent-gotchas/fastapi/security.py` for the canonical shape.

### `@app.on_event("startup")` is removed

**Symptom:** Code using `@app.on_event("startup")` / `@app.on_event("shutdown")` emits deprecation warnings on FastAPI 0.93+ and breaks on 0.121+.

**Fix:** Use a `lifespan` async context manager. See `templates/permanent-gotchas/fastapi/main.py`.

### Pydantic v1 patterns don't work in v2

**Symptom:** Migrated model code uses `@validator`, `class Config:`, `.dict()`, or `__fields__` and fails or behaves wrong on FastAPI ≥0.100 (which requires Pydantic v2).

**Fix when translating units:** rewrite to v2:
- `@validator` → `@field_validator`
- `@root_validator` → `@model_validator`
- `class Config:` → `model_config = ConfigDict(...)`
- `.dict()` → `.model_dump()`
- `.json()` → `.model_dump_json()`
- `__fields__` → `model_fields`

---

## Java / Spring Boot

### Spring Boot's `/health` is at `/actuator/health`, not `/health`

**Symptom:** Smoke gate (or any caller) hitting `/health` gets 404. Actuator dependency is included but path doesn't match.

**Fix:** Write an explicit `@RestController` for `/health`. Don't rely on actuator matching the smoke URL. See `templates/permanent-gotchas/spring-boot/HealthController.java`.

### Spring Initializr silently rewrites hyphenated artifactId into the base package

**Symptom:** Calling `start.spring.io` with `artifactId=api-new` and no `packageName` produces a base package of `com.example.apinew` (hyphen stripped, lowercased). Generated `@SpringBootApplication` class lands where the team didn't expect.

**Fix:** Always set `packageName` explicitly in the Initializr request. Document the choice in the team's notes.

### CORS is rejected by default

**Symptom:** UI on `localhost:5173` (or 3000, 4200) calls API on `localhost:8080` → browser blocks with CORS error.

**Fix:** Write a `@Configuration` class implementing `WebMvcConfigurer.addCorsMappings(...)` with the dev allow-list. See `templates/permanent-gotchas/spring-boot/CorsConfig.java`.

### `javax.*` → `jakarta.*` package rename in Spring Boot 3

**Symptom:** Legacy code copied verbatim with `import javax.persistence.Entity;` fails to compile.

**Fix when translating units:** rewrite `javax.persistence.*` → `jakarta.persistence.*`, `javax.servlet.*` → `jakarta.servlet.*`, `javax.validation.*` → `jakarta.validation.*`. Spring Boot 3 dropped all `javax.*` Jakarta-EE-derived packages.

---

## .NET / minimal API

### `--use-minimal-apis` flag has been removed

**Symptom:** `dotnet new webapi --use-minimal-apis -o apps/api-new` errors on .NET 9+ with "unrecognized option."

**Fix:** Drop the flag. Minimal APIs are the default in `dotnet new webapi` since .NET 8. Pass `--use-controllers` only if the team explicitly wants the controller-based template.

### `WebApplicationFactory<Program>` can't find `Program`

**Symptom:** Test project fails to compile with "Program is inaccessible due to its protection level."

**Root cause:** The top-level-statements `Program.cs` shipped by `dotnet new webapi` declares `Program` as `internal`. `WebApplicationFactory<Program>` requires it to be public.

**Fix:** Add `public partial class Program { }` at the bottom of `Program.cs`. Alternative: `[assembly: InternalsVisibleTo("<TestProjectName>")]`, but the partial-class line is the documented Microsoft pattern.

### Hyphenated project paths split assembly name from namespace

**Symptom:** `dotnet new webapi -o apps/api-new` produces `<AssemblyName>api-new</AssemblyName>` + `<RootNamespace>api_new</RootNamespace>` (underscore-sanitized). Builds work, but test code referencing the namespace surprises authors.

**Fix:** If PascalCase consistency matters, pass `-n ApiNew` (or similar) to force matching project/assembly/namespace names. Otherwise document the split.

### `dotnet new webapi` does not include CORS or `/health`

**Symptom:** Fresh scaffold serves nothing useful at `/health`; first cross-origin fetch from UI fails.

**Fix:** Add `builder.Services.AddCors(...)` + `app.UseCors(...)` + `app.MapGet("/health", ...)` to `Program.cs`. See `templates/permanent-gotchas/dotnet/Program-additions.cs`.

### xUnit v2 vs v3 coverage collector mismatch

**Symptom:** `dotnet test --collect:"XPlat Code Coverage"` runs but reports zero tests or zero coverage when the test project was generated with `dotnet new xunit3`.

**Root cause:** xUnit v3 uses Microsoft Testing Platform (MTP), not VSTest. `coverlet.collector` (VSTest-only) silently does nothing.

**Fix:** For `xunit3` projects, use `Microsoft.Testing.Extensions.CodeCoverage` instead of `coverlet.collector`. For greenfield work on .NET 10, document the choice; for legacy compatibility default to xUnit v2.

---

## TypeScript / NestJS

### `reflect-metadata` must be the first import in `main.ts`

**Symptom:** `Reflect.getMetadata is not a function` at startup, or DI fails silently with `undefined` providers.

**Root cause:** Nest's DI relies on the `reflect-metadata` polyfill being loaded before any decorator-annotated class is parsed.

**Fix:** Keep `import 'reflect-metadata';` as **the very first line** of `apps/api-new/src/main.ts`. The Nest CLI puts it there; the unit-migrator must not remove or reorder it. See `templates/permanent-gotchas/nestjs/main.ts`.

### Nest default port collides with Next.js dev

**Symptom:** Running Next.js (port 3000) + NestJS (also 3000 by default) → second one fails with `EADDRINUSE`.

**Fix:** Bind Nest to 3001 by default (`await app.listen(process.env.PORT ?? 3001)`). Document this in any UI ↔ API wiring step.

### `bcryptjs` is a slow pure-JS port — avoid

**Symptom:** Password hashing in NestJS is 10–30× slower than expected, blocking the event loop.

**Fix:** Use `bcrypt` (the native binding) or `argon2` (faster and stronger). `bcryptjs` only exists as a fallback for environments where native modules don't build; the modern Node.js binary distributions always have native bcrypt available.

---

## UI frameworks

### Vite ≥7 dropped Node 18/20

**Symptom:** `npm install` succeeds but `npm run build` fails with cryptic ESM / SyntaxError messages.

**Fix:** Require **Node 22+** for any Vite-based UI scaffold (`react-vite-ts`, `vue3-vite`, `svelte-kit`).

### `npm create svelte@latest` is retired

**Symptom:** Command runs but prints a deprecation banner and may fail to scaffold a current SvelteKit project.

**Fix:** Use `npx sv create <dir>` (the `sv` CLI from Svelte 5).

### Angular CLI doesn't always generate `karma.conf.js`

**Symptom:** `ng new ... --strict` on Angular 18+ produces a project without `karma.conf.js`; the `karma-jasmine` test recipe fails.

**Fix:** Install Karma manually (`npm i -D karma karma-jasmine karma-chrome-launcher karma-coverage jasmine-core @types/jasmine`) and run `npx karma init` if `karma.conf.js` is missing. For greenfield Angular work, consider switching the test runner to Vitest or Web Test Runner — Karma is on Angular's deprecation runway.

### Svelte 5 runes vs Svelte 4 reactivity

**Symptom:** Migrated Svelte components look correct but state doesn't update / `$:` blocks don't fire.

**Fix when translating units:** Use Svelte 5 runes:
- `let count = 0` (reactive in 4) → `let count = $state(0)` (in 5)
- `$: doubled = count * 2` → `let doubled = $derived(count * 2)`
- `$: { sideEffect(count); }` → `$effect(() => { sideEffect(count); })`
- `on:click` → `onclick`

### Next.js: stateful components need `'use client'`

**Symptom:** Build error "useState only available in client components" (or hooks/state/event handlers used in a Server Component).

**Fix when translating units:** Add `'use client';` as the very first line of any component that uses hooks, state, event handlers, or browser-only APIs. Server Components are the default in App Router; the migrator must opt every interactive component out explicitly.

---

## Cross-cutting

### CORS isn't configured in any default API scaffold

Every API stack's `<framework> new` / Initializr output rejects cross-origin requests by default. Every API template under `templates/permanent-gotchas/<stack>/` writes a permissive-for-dev CORS configuration with the standard dev allow-list:

- `http://localhost:5173` (Vite default)
- `http://localhost:3000` (Next.js default)
- `http://localhost:4200` (Angular default)

Tighten before any non-local deploy.

### `/health` endpoint is on the team

No framework's default scaffold serves `GET /health` returning 200 — the plugin's smoke gate hits this URL, so every API template writes an explicit health route.

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

Bundlers (Vite, Next, Angular CLI) also serve `public/` as static assets but don't auto-import stylesheets into the JS bundle. Many legacy designs cascade off a body-level wrapper class (`<body class="esh-shop">`); the new `index.html` doesn't carry it, so any rule scoped to `body.<class> ...` silently does nothing.

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

---

## Adding a new entry

When a migration hits a bug that wasn't here and you fix it, ask: *is the root cause version-specific, or is it a permanent quirk of the tool?* Permanent quirks go here. Version-specific issues (e.g., "JaCoCo 0.8.12 breaks on Java 23") stay in the recipe and get bumped on review — not here, because they age.
