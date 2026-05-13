---
description: >
  Creates the target project skeleton (UI, optional API, optional DB migrations
  directory) per the target stack in migration.md. Each subsystem is tracked
  independently in state.json.scaffold so partial completion is safe to resume.
  Does NOT migrate any features — just lays down the empty modern project so
  /web-modernize:auth and /web-modernize:next have somewhere to write to.
disable-model-invocation: false
---

# `/web-modernize:scaffold`

You are the **scaffold** skill. Your job is to bring up the modern project's skeleton — directory layout, package files, base configuration — without porting any feature code.

## Preflight

1. Parse `$ARGUMENTS`:
   - Empty → run the full scaffold (UI + API + DB + assets).
   - `--assets-only` → run **only** the "Copy legacy assets" step below. Skip the framework scaffolder, API, DB, and `verify.config.json` updates. Use case: a team mid-migration whose `/scaffold` ran before v0.3.1 (no asset copy) and needs to backfill missing images, fonts, favicon. Requires `state.status >= "scaffolded"` — see the precondition below.

2. Read `state.json`. Mode-dependent precondition:
   - **Full scaffold** (no flag): require `status == "planned"` (or `"scaffolded"` for re-runs of incomplete scaffolds). Otherwise redirect:
     - If `status` is earlier (`uninitialized`, `initialized`, `analyzed`): print "Run /web-modernize:<missing-skill> first." and stop.
     - If `status` is later (`auth_done`, `in_progress`, `complete`): tell user scaffolding is already done. To re-scaffold, they must `/web-modernize:abandon` first.
   - **`--assets-only`**: require `status >= "scaffolded"` (`scaffolded`, `auth_done`, `in_progress`, or `complete`). If earlier, redirect: "Asset backfill needs a target scaffold to copy into. Run /web-modernize:scaffold (without --assets-only) first."

3. Read `migration.md` §3 (UI), §4 (API), §5 (DB), §8 (constraints — esp. deployment target). For `--assets-only`, you only need §3 (specifically the optional "Asset directories" field, if present).

4. Read `.claude/modernize/plan.md` (for context, not strictly required).

5. Decide target directories. Default convention (use unless §8 says otherwise):
   - UI: `apps/web-new/`
   - API: `apps/api-new/`
   - DB: `db/migrations/`

6. If any of these directories already exist and are non-empty (full scaffold only), ask the user before touching them.

If `--assets-only`, skip directly to "Copy legacy assets" below; do not run the per-subsystem checklist or update `verify.config.json`.

## Per-subsystem checklist

Process each subsystem in order: UI → API → DB. For each, set `state.json.scaffold.<subsystem>` to `{"status": "in_progress", "path": "...", "started_at": "..."}` before starting. **Before flipping the subsystem to `"status": "done"`, run the smoke-build gate** (see "Smoke-build the subsystem" below). If smoke-build fails, leave `status` as `in_progress` and stop — do not advance to the next subsystem. This makes resume-after-interruption straightforward and guarantees a subsystem only reaches `done` when its skeleton actually installs and builds.

### UI scaffold

Based on `migration.md §3 Framework`:

#### `react-vite-ts`

1. Confirm Node ≥ 18 is available (`node --version`). If not, ask user how to proceed.
2. Run: `npm create vite@latest apps/web-new -- --template react-ts` (or whatever directory was decided).
3. `cd apps/web-new && npm install`.
4. Add libraries based on §3 "State management" and "Styling":
   - State: `redux-toolkit + react-redux` | `zustand` | (none)
   - Styling: `tailwindcss postcss autoprefixer` + run `npx tailwindcss init -p` | `@mui/material @emotion/react @emotion/styled` | (none)
5. Add scripts to `apps/web-new/package.json` (or confirm they exist): `dev`, `build`, `lint`, `typecheck`, `test`.
6. Add a minimal `apps/web-new/src/App.tsx` placeholder reading `Legacy app migration in progress — managed by web-modernize plugin`.

#### `next-app-router`

`npx create-next-app@latest apps/web-new --typescript --tailwind --eslint --app --no-src-dir` (adjust flags per §3 styling answer).

#### `vue3-vite`

`npm create vite@latest apps/web-new -- --template vue-ts`, install Vue Router and Pinia if §3 state management says so.

#### `angular-17`

`npx @angular/cli@17 new apps/web-new --routing --style=<scss|css> --strict --skip-git`.

#### `svelte-kit`

`npm create svelte@latest apps/web-new`, prompt non-interactively for skeleton project + TS.

#### Custom / other

Tell the user the plugin doesn't have a recipe for this framework. Ask them to scaffold manually, then confirm completion so the plugin can record `scaffold.ui.status = "done"` and move on.

### API scaffold

Only run if `state.target_stack.api != "none"` AND `!= "reuse-existing"`. Otherwise set `scaffold.api = {"status": "skipped", "reason": "target API = <value>"}` and move to DB.

Based on `target_stack.api`:

- `dotnet-minimal-api`: `dotnet new webapi --use-minimal-apis -o apps/api-new`
- `spring-boot-3`: use start.spring.io API (see legacy-analyzer or instruct user; offer to provide curl command)
- `nestjs`: `npm i -g @nestjs/cli` then `nest new apps/api-new` (use the `--package-manager npm --skip-git --skip-install` flags then `npm install` afterward to keep state.json consistent)
- `fastapi`: create `apps/api-new/` with `pyproject.toml` + `app/main.py` skeleton

Add a `/health` endpoint that returns `200 OK` so deployment smoke tests work immediately.

### DB scaffold

Only run if `state.target_stack.db != "unchanged"`. Otherwise mark skipped.

- `schema-migrate-to-<X>`: create `db/migrations/` with a placeholder migration `0001_init.sql` and a README explaining the migration tool the team chose.
- `replatform-to-<Y>`: create `db/` with a `README.md` describing the source → target plan; defer actual migration scripts to a later phase.

### Test harness

Run this sub-step **after** the framework CLI / API skeleton creation, **before** the smoke-build gate. Pick the recipe based on `state.testing.ui_framework` (for the UI subsystem) and `state.testing.api_framework` (for the API subsystem). Recipes per runner:

#### `vitest` (UI: Vite-based React/Vue/Svelte, SvelteKit)

1. `npm i -D vitest @vitest/coverage-v8 jsdom @testing-library/<framework-bindings> @testing-library/jest-dom` (substitute `react` / `vue` / `svelte` for `<framework-bindings>`; for SvelteKit also add `@sveltejs/vite-plugin-svelte` if not already present).
2. Write `vitest.config.ts` at the scaffold root with `test.environment = "jsdom"`, `test.globals = true`, `test.coverage = { provider: "v8", reporter: ["text", "json", "html"], include: ["src/**"] }`. Merge with existing Vite config via `mergeConfig` if `vite.config.ts` exists.
3. Test files are colocated (`*.test.ts`/`*.test.tsx`). Write one sample at `src/App.test.tsx` (or `.spec.ts` for SvelteKit) that renders the placeholder `App` and asserts visible text.
4. Add `package.json` scripts: `"test": "vitest run"`, `"test:coverage": "vitest run --coverage"`.

#### `jest` (UI: Next.js; API: NestJS)

1. For Next.js: `npm i -D jest jest-environment-jsdom @types/jest ts-jest @testing-library/react @testing-library/jest-dom`. For NestJS: `nest new` already added jest; verify `package.json` has the `jest` block.
2. Write `jest.config.js` at the scaffold root (or merge with the existing one for Nest). For Next.js include `testEnvironment: "jsdom"`, `transform` with `ts-jest`, and `collectCoverageFrom: ["src/**/*.{ts,tsx}"]`.
3. Tests live in `__tests__/` or as colocated `*.spec.ts`/`*.test.ts`. Write one sample (`__tests__/app.spec.ts` for Nest, `__tests__/page.test.tsx` for Next) that imports the root and asserts a basic invariant.
4. Add scripts: `"test": "jest --ci --runInBand"`, `"test:coverage": "jest --ci --coverage"`.

#### `karma-jasmine` (UI: Angular)

1. Angular CLI's `ng new` already installs karma + jasmine and writes `karma.conf.js` and `tsconfig.spec.json`. Verify both exist.
2. Add `coverageReporter` to `karma.conf.js`:
   ```js
   coverageReporter: { dir: require('path').join(__dirname, './coverage/'), reporters: [{ type: 'html' }, { type: 'text-summary' }, { type: 'json-summary' }] }
   ```
   Add `karma-coverage` to `plugins` if not present.
3. Leave the CLI-generated `src/app/app.component.spec.ts` in place as the sample.
4. Add scripts: `"test": "ng test --watch=false --browsers=ChromeHeadless"`, `"test:coverage": "ng test --watch=false --code-coverage --browsers=ChromeHeadless"`. Tell the user that headless Chrome must be installed on the CI runner.

#### `pytest` (API: FastAPI)

1. Edit `pyproject.toml`:
   - Add `pytest`, `pytest-cov`, `httpx` to `[project.optional-dependencies].dev`.
   - Add a `[tool.pytest.ini_options]` block with `testpaths = ["tests"]`, `addopts = "-q"`.
   - Add a `[tool.coverage.run]` block with `source = ["app"]`.
2. Re-run `pip install -e ".[dev]"` so the new dev deps land in the environment.
3. Create `tests/__init__.py` (empty) and `tests/conftest.py` with:
   ```python
   import pytest
   from fastapi.testclient import TestClient
   from app.main import app

   @pytest.fixture
   def client():
       return TestClient(app)
   ```
4. Write `tests/test_health.py`:
   ```python
   def test_health(client):
       resp = client.get("/health")
       assert resp.status_code == 200
   ```

#### `xunit` (API: .NET minimal API)

1. From the scaffold parent: `dotnet new xunit -o tests/<ProjectName>.Tests`, then `dotnet add tests/<ProjectName>.Tests reference apps/api-new/<ProjectName>.csproj`.
2. In the test project, `dotnet add package coverlet.collector` and `dotnet add package Microsoft.AspNetCore.Mvc.Testing`.
3. Make `Program.cs` discoverable for `WebApplicationFactory<Program>` by adding `public partial class Program { }` at the bottom of `Program.cs` (or use a `[assembly: InternalsVisibleTo]` attribute).
4. Write `tests/<ProjectName>.Tests/HealthTests.cs` using `WebApplicationFactory<Program>` to assert `GET /health` returns 200.
5. Add a Makefile target or document `dotnet test --collect:"XPlat Code Coverage"` as the coverage command.

#### `nunit` / `mstest` (API: .NET minimal API alternates)

Same as `xunit` but `dotnet new nunit` or `dotnet new mstest`. The `WebApplicationFactory<Program>` pattern is identical; only the attribute syntax differs (`[Test]` for NUnit, `[TestMethod]` for MSTest).

#### `junit5` (API: Spring Boot)

1. `start.spring.io` output already includes `spring-boot-starter-test` which brings JUnit 5. Verify.
2. Add JaCoCo to `pom.xml`:
   ```xml
   <plugin>
     <groupId>org.jacoco</groupId>
     <artifactId>jacoco-maven-plugin</artifactId>
     <version>0.8.12</version>
     <executions>
       <execution><goals><goal>prepare-agent</goal></goals></execution>
       <execution><id>report</id><phase>test</phase><goals><goal>report</goal></goals></execution>
     </executions>
   </plugin>
   ```
   (Or the Gradle equivalent: `id 'jacoco'` + `jacocoTestReport` task.)
3. Write `src/test/java/<base-package>/HealthControllerTests.java` using `@SpringBootTest(webEnvironment = RANDOM_PORT)` + `WebTestClient` (or `@AutoConfigureMockMvc` + `MockMvc`) to assert `GET /health` returns 200.

#### `manual` / `other: <name>`

The team chose a runner the plugin doesn't have a recipe for. Set `scaffold.<subsystem>.test_harness = "manual"`, do not install or write any test files, and print:

```
Test harness for <stack> is manual — install <framework> yourself, write a sample test, and commit before /web-modernize:next runs the first unit. The smoke gate will record "test_harness": "manual" and skip the harness smoke step; per-unit coverage will be skipped (soft-skip, never blocks).
```

If `state.testing.api_framework == "n/a"` (i.e., §4 set API to `none` / `reuse-existing`), skip the API test harness entirely and record `scaffold.api.test_harness = "n/a"`.

### Smoke-build the subsystem

After files are written for a subsystem (including the test harness above) and **before** flipping `state.json.scaffold.<subsystem>.status` to `"done"`, run two commands from the subsystem's path: an **install + build** smoke, then a **test-harness** smoke. Capture exit code, stdout, and stderr for each.

**Install + build smoke** (proves the skeleton compiles and installs):

| Subsystem / stack | Working dir | Smoke command |
|---|---|---|
| UI `react-vite-ts`, `vue3-vite`, `svelte-kit` | `<scaffold.ui.path>` | `npm install && npm run build` |
| UI `next-app-router` | `<scaffold.ui.path>` | `npm install && npm run build` |
| UI `angular-17` | `<scaffold.ui.path>` | `npm install && npm run build` |
| UI `custom`/other | — | record `"smoke": "n/a"`, continue |
| API `fastapi` | `<scaffold.api.path>` | `pip install -e ".[dev]" && python -c "import app.main"` |
| API `dotnet-minimal-api` | `<scaffold.api.path>` | `dotnet build` |
| API `spring-boot-3` | `<scaffold.api.path>` | `./mvnw -q -DskipTests package` (fall back to `mvn -q -DskipTests package` if no wrapper) |
| API `nestjs` | `<scaffold.api.path>` | `npm install && npm run build` |
| API `none` / `reuse-existing` | — | not run (subsystem is `skipped`) |
| DB any | — | no-op for now; record `"smoke": "n/a"` |

**Test-harness smoke** (proves the harness picks up and runs the sample test). Pick the command from `state.testing.ui_framework` / `state.testing.api_framework`:

| Test runner | Working dir | Smoke command |
|---|---|---|
| `vitest` | `<scaffold.<subsystem>.path>` | `npm run test -- --run` |
| `jest` | `<scaffold.<subsystem>.path>` | `npm test -- --ci --runInBand` |
| `karma-jasmine` | `<scaffold.ui.path>` | `npm run test -- --watch=false --browsers=ChromeHeadless` |
| `pytest` | `<scaffold.api.path>` | `pytest -q tests/test_health.py` |
| `xunit` / `nunit` / `mstest` | repo root or `tests/<Project>.Tests/` | `dotnet test --no-build` |
| `junit5` | `<scaffold.api.path>` | `./mvnw -q test` (fall back to `mvn -q test`) |
| `manual` | — | record `"test_harness": "manual"`, skip the run |
| `n/a` (subsystem `skipped`) | — | record `"test_harness": "n/a"`, skip the run |

The test-harness smoke runs only if the install + build smoke succeeded. If install + build fails, do not run the test-harness smoke for that subsystem (it would fail downstream anyway).

On **success** (both smokes exit 0, or one is `n/a`/`manual`), record on the subsystem block and flip to `done`:

```json
"scaffold": {
  "<subsystem>": {
    "status": "done",
    "path": "...",
    "started_at": "...",
    "finished_at": "<now>",
    "smoke": {
      "command": "<install+build cmd>",
      "exit_code": 0,
      "ran_at": "<now>",
      "test_harness": {
        "runner": "<vitest|pytest|...|manual|n/a>",
        "command": "<test-harness cmd>",
        "exit_code": 0,
        "ran_at": "<now>"
      }
    }
  }
}
```

On **failure** (either smoke is non-zero), record and stop. The `smoke` block carries whichever sub-block failed; if `smoke.exit_code != 0` the test-harness smoke was not run (`test_harness.skipped_reason: "install+build failed"`).

```json
"scaffold": {
  "<subsystem>": {
    "status": "in_progress",
    "path": "...",
    "started_at": "...",
    "smoke": {
      "command": "<install+build cmd>",
      "exit_code": <N>,
      "ran_at": "<now>",
      "stderr_tail": "<last ~40 lines of stderr, trimmed>",
      "test_harness": { "skipped_reason": "install+build failed" }
    }
  }
}
```

If install+build passed but the test-harness smoke failed, the `test_harness` sub-block carries the non-zero exit and stderr tail; the outer `smoke.exit_code` stays 0 but the overall gate still fails (subsystem stays `in_progress`).

Print the captured `stderr_tail` to the user with one sentence framing what failed (use "install+build" or "test-harness" depending on which sub-step broke):

```
✗ Scaffold <install+build|test-harness> smoke failed for <subsystem> (<stack>).
  Command: <cmd>
  Exit:    <N>
  Last 40 lines of stderr:
    <…>

The subsystem is left in `in_progress`. Fix the generated files (or the recipe in skills/scaffold/SKILL.md) and re-run /web-modernize:scaffold to retry.
```

Then **stop** — do NOT proceed to the next subsystem and do NOT advance `state.status` to `scaffolded`. Re-running `/web-modernize:scaffold` from `status == "planned"` (or from a partially-`scaffolded` re-run) will pick up where it left off.

If the chosen stack has no entry in the table (custom/other), set `"smoke": "n/a"` and proceed — the gate degrades gracefully and never blocks unknown stacks.

## Copy legacy assets

Migrated pages will reference images, fonts, and favicons from the legacy app. Without this step those references 404. Run this **after** the UI scaffold (so `<scaffold.ui.path>/public/` exists) but before declaring the scaffold complete.

This step also runs as the only action when `--assets-only` is passed.

### 1. Determine the source list

If `migration.md §3` contains a non-empty **"Asset directories"** field (one path per bullet), treat that list as authoritative — use exactly the declared paths and skip the heuristic scan below. Print a one-line note: `Using migration.md §3 asset declarations: <list>`.

Otherwise, scan the working directory for these patterns (case-insensitive). Match directories first, then top-level files:

- `Pics/`, `pics/`
- `images/`, `Images/`, `img/`
- `Content/` and any sub-directories under it (ASP.NET MVC convention) — typically `Content/images/`, `Content/Pics/`, `Content/fonts/`, `Content/css/`
- `wwwroot/` and any sub-directories (ASP.NET Core static files) — typically `wwwroot/images/`, `wwwroot/css/`, `wwwroot/lib/`, `wwwroot/fonts/`
- `assets/`, `assets/img/`, `assets/images/`, `assets/fonts/`
- `fonts/`, `font/`
- `static/` (Django, Jekyll, Hugo)
- `public/` (some older Express / Node legacy apps — careful not to confuse with the target's `public/`)
- `src/main/webapp/resources/` (Java)
- Top-level files: `favicon.ico`, `favicon.png`, `apple-touch-icon.png`, `robots.txt`, `sitemap.xml`

Skip these directories entirely (they are output / dependency / plugin-managed): `.git/`, `node_modules/`, `bin/`, `obj/`, `dist/`, `build/`, `out/`, `target/`, `.next/`, `.svelte-kit/`, `__pycache__/`, `.venv/`, `vendor/`, `.claude/`, `packages/`, `.idea/`, `.vscode/`, and the existing target scaffold directories (`apps/web-new/`, `apps/api-new/`, `db/`).

### 2. Copy each discovered directory or file into the target's `public/`

Use the target UI's `public/` directory (typically `<scaffold.ui.path>/public/` — Vite, Next.js, Astro, SvelteKit, etc.). For Angular, use `<scaffold.ui.path>/src/assets/` instead — Angular's static asset convention differs.

Preserve sub-structure under the destination:

- `<legacy>/Pics/` → `<scaffold.ui.path>/public/Pics/`
- `<legacy>/wwwroot/images/` → `<scaffold.ui.path>/public/images/`
- `<legacy>/Content/images/` → `<scaffold.ui.path>/public/images/`
- `<legacy>/fonts/` → `<scaffold.ui.path>/public/fonts/`
- `<legacy>/favicon.ico` → `<scaffold.ui.path>/public/favicon.ico`

Use `cp -r` (or platform-equivalent) — do **not** move or delete the source. The legacy tree is still the source-of-truth for units that haven't migrated yet.

### 3. Idempotency

If a destination file already exists in `public/`, **skip it** and add a one-line "(exists, skipped: `<path>`)" to the summary. Do not overwrite — the team may have manually adjusted assets after a previous scaffold run.

If a destination directory exists but contains different files than the source, copy only the missing ones; don't synchronize deletions.

### 4. Detect absolute-URL references in the legacy CSS

Grep the legacy CSS/SCSS/LESS files (use the same set this skill found in step 1 of the scan) for `url('/...')` patterns — absolute URLs starting with `/`. If any are found, print a warning naming the affected stylesheet(s) and lines:

```
WARNING: legacy CSS uses absolute URLs that may not resolve under the target framework:
  Content/site.css:42:   url('/Content/Pics/promo.png')
  Content/site.css:118:  url('/fonts/icons.woff2')

After this asset copy, the files exist at <scaffold.ui.path>/public/Content/Pics/promo.png
and <scaffold.ui.path>/public/fonts/icons.woff2.

Confirm your target framework serves /public/ at the URL root:
  - Next.js: respect `basePath` in next.config.js
  - Vite: confirm `base: '/'` in vite.config.ts
  - Angular: assets live at /assets/, NOT /public/ — see below

If the target uses a different base path, the migration agent (/next, /migrate)
will need to rewrite these references when porting each affected unit. The
agent reads this warning from the unit's notes file when planning translations.
```

Also append the warning verbatim to `.claude/modernize/notes/__scaffold__.md` (create the file if missing) so the migration agent can read it later.

### 5. Print a summary

```
✓ Copied legacy assets to <scaffold.ui.path>/public/:
  - Pics/ (47 files, 12.3 MB)
  - Content/images/ (18 files, 2.1 MB)
  - fonts/ (3 files, 240 KB)
  - favicon.ico

  Skipped (already exists in target):
  - public/robots.txt

  Absolute URL references in legacy CSS: 2 (see notes/__scaffold__.md)
```

If no assets were discovered (no matching directories, no `migration.md §3` declarations, no top-level favicon), print:

```
(no legacy asset directories detected — nothing to copy)
```

and continue. This is normal for some legacy stacks (e.g., a pure API).

## Update verify.config.json

Now that target paths exist, update `.claude/modernize/verify.config.json`:
- Replace `${ui_root}` defaults with the actual UI path (e.g., `apps/web-new`).
- Replace `${api_root}` with actual API path or `null` if skipped.
- Keep the user's manual edits if they edited the file already — diff and ask.

## Commit suggestion

After a full scaffold, suggest (but do not execute) a commit:

```
Suggested commit:
  git add apps/ .claude/modernize/ db/ verify.config.json
  git commit -m "scaffold: target project skeleton via web-modernize"
```

For `--assets-only`, suggest a narrower commit:

```
Suggested commit:
  git add apps/<ui-path>/public/ .claude/modernize/notes/__scaffold__.md
  git commit -m "scaffold: backfill legacy assets via web-modernize"
```

## After writing

For a **full scaffold**, print:

```
✓ Scaffold complete.

  UI:  <ui.status> at <ui.path>
  API: <api.status> at <api.path or "(skipped)">
  DB:  <db.status>
  Assets: <count of directories copied>, <count of files skipped> (see notes/__scaffold__.md if any warnings)

Verification config updated. Edit .claude/modernize/verify.config.json if your scripts differ.

Next: /web-modernize:auth   (migrates the auth provider before any feature units)
```

For **`--assets-only`**, print:

```
✓ Asset backfill complete.

  Copied: <count of files> across <count of directories>
  Skipped: <count> (already present)
  CSS absolute-URL warnings: <count> (see notes/__scaffold__.md)

Top-level state.status unchanged (<state.status>). Re-run /web-modernize:verify on any
recently-migrated unit to confirm asset references now resolve.
```

## State transition

- **Full scaffold**:
  - Pre: `state.status` == `planned` (or `scaffolded` for a re-run of an incomplete scaffold).
  - Post: `state.status` = `scaffolded` (only when all non-skipped subsystems are `done`).
- **`--assets-only`**:
  - Pre: `state.status >= "scaffolded"` (any phase from `scaffolded` onward).
  - Post: top-level `state.status` unchanged. Only `state.updated_at` is bumped. No per-subsystem scaffold block is touched.
