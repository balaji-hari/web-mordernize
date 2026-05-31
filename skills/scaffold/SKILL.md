---
description: "Create the target project skeleton (UI/API/DB) by reading frameworks/<name>.md recipes and copying legacy assets into public/. Use when state.status is 'planned'. Triggers: 'scaffold the new project', 'create the target app', 'set up the new codebase', 'let's scaffold', 'build the skeleton'."
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

### Stack defaults (cross-cutting; per-framework details live in frameworks/*.md)

Dev port, Node minimum, and the per-stack scaffold recipe are stored in each `frameworks/<name>.md` (`role: target-ui` or `role: target-api`). The scaffold skill reads them on demand — do not duplicate them in this skill.

The shared dev CORS allow-list (used by every API scaffold) is:
- `http://localhost:5173` (Vite-based UIs)
- `http://localhost:3000` (Next.js)
- `http://localhost:4200` (Angular)

Every API scaffold must write a permissive-for-dev / locked-down-for-prod CORS configuration using this allow-list, and every UI scaffold must write the API base URL into the UI's env file (the exact var name + file path is in the UI framework's `## Scaffold > Wire to API` section).

### UI scaffold

1. Read `state.target_stack.ui` from `state.json` (or `migration.md §3 Framework` if state hasn't yet recorded it).
2. Try to Read `${CLAUDE_PLUGIN_ROOT}/frameworks/<state.target_stack.ui>.md`.
3. **If the file exists**: Verify its frontmatter `role: target-ui`. Read its `## Scaffold` section. Preflight Node ≥ the version stated in its `## Dev server` table. Run the scaffold command (substituting `<api-port>` from the matching API framework's `## Dev server` table, if any). Wire the env file per the framework's `### Wire to API` block. Then proceed to the Test harness step.
4. **If the file does NOT exist** (unknown target UI): run the **Unknown-target follow-up** below, then proceed.

### API scaffold

Only run if `state.target_stack.api != "none"` AND `!= "reuse-existing"`. Otherwise set `scaffold.api = {"status": "skipped", "reason": "target API = <value>"}` and move to DB.

1. Read `state.target_stack.api`.
2. Try to Read `${CLAUDE_PLUGIN_ROOT}/frameworks/<state.target_stack.api>.md`.
3. **If the file exists**: Verify its frontmatter `role: target-api`. Read its `## Scaffold` section and execute it. The file's `## Scaffold` section already encodes the per-stack `/health`, CORS, port, and load-bearing rules (e.g., `reflect-metadata` first-import for Nest, `only-include` for FastAPI hatchling, `partial class Program` for .NET). **Also read `agents/permanent-gotchas.md`** — its entries are cross-cutting rules the agent must honor regardless of what current docs suggest.
4. **If the file does NOT exist** (unknown target API): run the **Unknown-target follow-up** below, then proceed.

### Unknown-target follow-up

When `frameworks/<name>.md` is missing for either UI or API target, the plugin doesn't have a built-in recipe — but the scaffold lifecycle continues. Ask the user via `AskUserQuestion` (three single-select prompts in sequence; record each answer in `verify.config.json` for retry idempotency):

1. **Scaffold command** — *"I don't have a built-in recipe for `<name>`. Paste the shell command to scaffold a new project, or pick a fallback."*
   - Options: paste-command (Other / free text), `manual` (you'll scaffold yourself; I'll proceed once you confirm completion), `abort` (stop scaffold; rerun with a supported target).
2. **Test framework** — *"What test runner should the scaffold install?"*
   - Options: `vitest`, `jest`, `pytest`, `manual` (you'll set it up). Free text via Other for anything else.
3. **Verify commands** — *"What lint / typecheck / test commands should /verify run for this stack?"*
   - Three follow-up free-text fields. Defaults from `verify.config.json` are offered as starting points.

Persist answers to `.claude/modernize/verify.config.json` under a new top-level key per subsystem:
```json
{
  "ui_root": "apps/web-new",
  "api_root": "apps/api-new",
  "custom_recipes": {
    "<framework-name>": {
      "scaffold_command": "<user input>",
      "test_framework": "<user input>",
      "verify_commands": { "lint": "...", "typecheck": "...", "test": "..." }
    }
  }
}
```

On retry/re-run, the scaffold skill first checks `verify.config.json.custom_recipes.<name>` before re-prompting — if present, reuse the saved values silently.

**Optionally** offer to save a stub `frameworks/<name>.md` at `.claude/modernize/frameworks/<name>.md` (under the user's repo, not the plugin) so future migrations of the same stack inherit the recipe. Use a minimal template:
```markdown
---
name: <name>
display_name: <user-supplied display name>
role: target-ui  # or target-api
---

## Scaffold
```sh
<user's scaffold command>
```

## Test framework
<user's test framework>

## Dev server
<best-guess from verify.config.json>
```

After running the scaffold command (or recording `manual` and waiting for user confirmation), proceed to the Test harness step.

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

1. Verify that `karma.conf.js` and `tsconfig.spec.json` exist (older Angular versions had `ng new` generate them automatically). If `karma.conf.js` is missing (Angular 18+ in some configurations no longer generates it), install Karma manually: `npm i -D karma karma-jasmine karma-chrome-launcher karma-coverage jasmine-core @types/jasmine`, then run `npx karma init karma.conf.js` (accept defaults) or write a minimal `karma.conf.js`. Karma itself is on Angular's long deprecation runway — for greenfield Angular migrations the team should consider `other: web-test-runner` or `other: vitest` in §12 instead.
2. Add `coverageReporter` to `karma.conf.js`:
   ```js
   coverageReporter: { dir: require('path').join(__dirname, './coverage/'), reporters: [{ type: 'html' }, { type: 'text-summary' }, { type: 'json-summary' }] }
   ```
   Add `karma-coverage` to `plugins` if not present.
3. Leave the CLI-generated `src/app/app.component.spec.ts` in place as the sample.
4. Add scripts: `"test": "ng test --watch=false --browsers=ChromeHeadless"`, `"test:coverage": "ng test --watch=false --code-coverage --browsers=ChromeHeadless"`. Tell the user that headless Chrome must be installed on the CI runner.

#### `pytest` (API: FastAPI)

The pyproject from `templates/permanent-gotchas/fastapi/pyproject.toml` already declares pytest/httpx in `[project.optional-dependencies].dev`, `[tool.pytest.ini_options]`, and `[tool.coverage.run]`. Re-run `pip install -e ".[dev]"` so the dev deps land in the venv. Then write:

- `apps/api-new/tests/__init__.py` (empty)
- `apps/api-new/tests/conftest.py` — exports a `client` fixture wrapping the FastAPI app in `httpx.AsyncClient` (or the sync `TestClient`) bound to the in-process ASGI transport.
- `apps/api-new/tests/test_health.py` — single test that calls `client.get("/health")` and asserts `200` + `{"status": "UP"}`.

#### `xunit` (API: .NET minimal API)

**Run all commands from the repo root** (not from `apps/`). Substitute the real project name (the directory under `apps/`) for `<project>` below — e.g., `api-new`:

1. `dotnet new xunit -o tests/<project>.Tests` (default to xUnit v2 + `coverlet.collector` / VSTest unless the team has explicitly opted into xUnit v3 / Microsoft Testing Platform).
2. `dotnet add tests/<project>.Tests reference apps/<project>/<project>.csproj`
3. In the test project: `dotnet add tests/<project>.Tests package coverlet.collector` and `dotnet add tests/<project>.Tests package Microsoft.AspNetCore.Mvc.Testing`.
4. Make `Program.cs` discoverable for `WebApplicationFactory<Program>` by adding `public partial class Program { }` at the bottom of `apps/<project>/Program.cs`. (This is also done in the API scaffold step — if both ran, leave the single line in place.)
5. Create a solution file so `dotnet build` / `dotnet test` at repo root work without args:
   ```
   dotnet new sln -n <project>
   dotnet sln add apps/<project>/<project>.csproj tests/<project>.Tests/<project>.Tests.csproj
   ```
6. Write `tests/<project>.Tests/HealthTests.cs` using `WebApplicationFactory<Program>` to assert `GET /health` returns 200.
7. Document `dotnet test --collect:"XPlat Code Coverage"` as the coverage command (or add a Makefile target).

#### `nunit` / `mstest` (API: .NET minimal API alternates)

Same as `xunit` but `dotnet new nunit` or `dotnet new mstest`. The `WebApplicationFactory<Program>` pattern is identical; only the attribute syntax differs (`[Test]` for NUnit, `[TestMethod]` for MSTest).

#### `junit5` (API: Spring Boot)

1. `start.spring.io` output already includes `spring-boot-starter-test` which brings JUnit 5. Verify.
2. Add the latest JaCoCo Maven plugin to `pom.xml`. Resolve the current version from Maven Central (`org.jacoco:jacoco-maven-plugin`) at scaffold time — do not hardcode a version, since JaCoCo gates on the bytecode version of analyzed classes and stale pins silently break coverage on newer JDKs. Shape:
   ```xml
   <plugin>
     <groupId>org.jacoco</groupId>
     <artifactId>jacoco-maven-plugin</artifactId>
     <version><!-- latest from Maven Central --></version>
     <executions>
       <execution><goals><goal>prepare-agent</goal></goals></execution>
       <execution><id>report</id><phase>test</phase><goals><goal>report</goal></goals></execution>
     </executions>
   </plugin>
   ```
   (Or the Gradle equivalent: `id 'jacoco'` + `jacocoTestReport` task.)
3. Write `src/test/java/<base-package>/HealthControllerTests.java` using **`@SpringBootTest` + `@AutoConfigureMockMvc` + `MockMvc`** to assert `GET /health` returns 200. `MockMvc` is the right default for Spring Boot 3's MVC (Tomcat) stack — `mockMvc.perform(get("/health")).andExpect(status().isOk())` works with only `spring-boot-starter-test` on the classpath.

   Only use `WebTestClient` if the target is WebFlux (reactive) — it requires adding `spring-boot-starter-webflux` as a test dependency, which pulls in a reactive stack the MVC default doesn't need.

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
| UI `angular` | `<scaffold.ui.path>` | `npm install && npm run build` |
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

### 2. Size guard — prompt before copying very large asset trees

**Before** issuing any `cp`, sum the byte counts of every discovered directory + file from step 1 (use Bash `du -sb` on Linux/macOS, `Get-ChildItem -Recurse | Measure-Object Length -Sum` on Windows, or read sizes via the file APIs and add). If the total is > **500 MB**, stop and prompt the user — large binary assets (especially `.psd`, `.ai`, `.mov`, `.mp4`, `.raw`, `.iso`) often shouldn't be in the migrated tree, and silently copying multi-GB of source files frequently fills the dev's disk mid-`npm install`/`pip install` with cryptic ENOSPC errors elsewhere.

Print:

```
⚠ Legacy assets total <SIZE_HUMAN> across <N> directories/files. Copying
  everything will roughly double the size of your target scaffold and may
  fill your disk during subsequent installs.

How do you want to handle this?
  y — exclude large binary file types (.psd, .ai, .mov, .mp4, .raw, .iso)
      (RECOMMENDED — most migrations don't need design source files in
       the production tree; keep originals in the legacy repo as the
       authoritative copy)
  n — copy everything anyway
  s — show the 10 largest files first, then ask again
```

Accept `y` / `n` / `s` (case-insensitive). `s` prints the 10 largest discovered files with size + path, then re-prompts. `y` copies but skips files whose extension matches the exclude list and records the skip count in the summary. `n` copies everything.

If the total is ≤ 500 MB, skip the prompt and proceed.

### 3. Copy each discovered directory or file into the target's `public/`

Use the target UI's `public/` directory (typically `<scaffold.ui.path>/public/` — Vite, Next.js, Astro, SvelteKit, etc.). For Angular, use `<scaffold.ui.path>/src/assets/` instead — Angular's static asset convention differs.

Preserve sub-structure under the destination:

- `<legacy>/Pics/` → `<scaffold.ui.path>/public/Pics/`
- `<legacy>/wwwroot/images/` → `<scaffold.ui.path>/public/images/`
- `<legacy>/Content/images/` → `<scaffold.ui.path>/public/images/`
- `<legacy>/fonts/` → `<scaffold.ui.path>/public/fonts/`
- `<legacy>/favicon.ico` → `<scaffold.ui.path>/public/favicon.ico`

Use `cp -r` (or platform-equivalent) — do **not** move or delete the source. The legacy tree is still the source-of-truth for units that haven't migrated yet.

### 4. Idempotency

If a destination file already exists in `public/`, **skip it** and add a one-line "(exists, skipped: `<path>`)" to the summary. Do not overwrite — the team may have manually adjusted assets after a previous scaffold run.

If a destination directory exists but contains different files than the source, copy only the missing ones; don't synchronize deletions.

### 5. Detect absolute-URL references in the legacy CSS

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

### 6. Print a summary

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

For a **full scaffold**, print the summary block **and** the run-the-stack instructions so the team can immediately verify the scaffold works end-to-end. The closing message must include an **install/activate step before the dev command** for every terminal — the smoke-build gate already installed once during scaffolding, but a fresh terminal session (especially for Python with a venv) won't have the tools on PATH otherwise, and a teammate who just `git pull`-ed the scaffolded skeleton hasn't installed at all yet. Never print a dev command without the install/activate line directly above it.

Substitute per-stack commands from these tables based on `state.target_stack.ui` / `state.target_stack.api`. The **Install / activate** column is what to print on the line directly before the dev command.

| UI stack | Install / activate | Dev command | URL |
|---|---|---|---|
| `react-vite-ts`, `vue3-vite`, `svelte-kit` | `npm install` | `npm run dev` | http://localhost:5173 |
| `next-app-router` | `npm install` | `npm run dev` | http://localhost:3000 |
| `angular` | `npm install` | `npm start` | http://localhost:4200 |

| API stack | Install / activate | Dev command | URL | Health check |
|---|---|---|---|---|
| `fastapi` | `python -m venv .venv && source .venv/bin/activate` *(Windows PowerShell: `.venv\Scripts\Activate.ps1`; bash-on-Windows / Git Bash: `source .venv/Scripts/activate`)*, then `pip install -e ".[dev]"` | `fastapi dev app/main.py` *(or `uvicorn app.main:app --reload`)* | http://localhost:8000 | `curl http://localhost:8000/health` |
| `spring-boot-3` | `./mvnw -q -DskipTests package` *(Windows: `mvnw.cmd -q -DskipTests package`)* | `./mvnw spring-boot:run` *(Windows: `mvnw.cmd spring-boot:run`)* | http://localhost:8080 | `curl http://localhost:8080/health` |
| `dotnet-minimal-api` | `dotnet restore` | `dotnet run` | http://localhost:5000 *(or as printed in `launchSettings.json`)* | `curl http://localhost:5000/health` |
| `nestjs` | `npm install` | `npm run start:dev` | http://localhost:3001 | `curl http://localhost:3001/health` |

If `state.target_stack.api` is `none` or `reuse-existing`, omit the API rows. If `ui` is `custom`, fall back to a generic "install your UI dependencies, then start the dev server" line.

Closing message — note the explicit "Install dependencies" line **above** every "Start" line. Always `cd` into the subsystem path first; install and dev commands both run from there:

```
✓ Scaffold complete.

  UI:  <ui.status> at <ui.path>
  API: <api.status> at <api.path or "(skipped)">
  DB:  <db.status>
  Assets: <count of directories copied>, <count of files skipped> (see notes/__scaffold__.md if any warnings)

Run the new stack locally — open two terminals. The first time on a fresh
clone you must install dependencies; the scaffold smoke-build installed
once during scaffolding, but a new shell (especially Python venvs) won't
have the tools on PATH until you activate / install again.

  Terminal 1 — API (<api stack>, port <api port>):
    cd <api.path>
    # Install dependencies (first time on this machine, or after pulling
    # the scaffold from git):
    <API install/activate command>
    # Start the dev server:
    <API dev command>

  Terminal 2 — UI (<ui stack>, port <ui port>):
    cd <ui.path>
    # Install dependencies (first time on this machine, or after pulling
    # the scaffold from git):
    <UI install/activate command>
    # Start the dev server:
    <UI dev command>

Smoke-check both:
    <API health curl>         # → {"status":"UP"}
    open <UI URL>             # placeholder page loads

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
