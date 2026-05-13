---
name: unit-migrator
description: >
  Shared procedure for porting a single unit from legacy source to the target
  stack. Loaded inline by /web-modernize:next, /web-modernize:migrate, and
  /web-modernize:retry — they all do the same translation work, only the
  unit-selection step and the dep-policy flag differ. This file is the single
  source of truth for the migration loop; do not duplicate it elsewhere.

  NOTE: Despite living under agents/, this is NOT launched as a separate
  subagent (unlike legacy-analyzer). It is read inline by the calling skill
  so that file mutations, user prompts, and identity all stay in the same
  conversation.

  Storage convention (schema v3): each unit lives in its own file at
  .claude/modernize/units/<unit-id>.json. Top-level workflow status lives in
  .claude/modernize/state.json. Unit mutations always write the per-unit
  file; only top-level transitions touch state.json.
---

# `unit-migrator` — shared per-unit migration procedure

You are executing the unit-migration procedure. The calling skill has already done these things and is passing you the result:

- **Picked a unit** to migrate. The unit object is referred to below as `unit`. It was read from `.claude/modernize/units/<unit.id>.json`.
- **Read** `state.json`, `migration.md`, `.claude/modernize/plan.md`.
- **Verified** the top-level workflow status is one of `auth_done` / `in_progress`.

The calling skill also passes a **mode** and an optional **force_deps** flag:

| Mode | Set by | Meaning |
|------|--------|---------|
| `next` | `/web-modernize:next` | Auto-selected the next eligible pending unit. Caller has already verified deps are met. |
| `migrate` | `/web-modernize:migrate` | User named the unit explicitly. By default, caller blocks on unmet deps and never reaches this agent. With `--force`, caller sets `force_deps=true` and you may proceed with stubs. |
| `retry` | `/web-modernize:retry` | Unit was `failed`; we are re-attempting. `retry_prompt` may be set. |

Optional inputs:

- `retry_prompt` (retry mode only) — free-text override the user provided via `/web-modernize:retry --with-prompt="…"`. When set, treat it as **additional guidance** layered on top of `migration.md`. Record it in `unit.last_retry_prompt`.
- `force_deps` (migrate mode only) — boolean. When `true`, proceed even if `depends_on` is unsatisfied; stub the missing dep imports with TODO comments. When `false` or absent, the caller would have blocked already; assume deps are met.

## 1. In-flight collision handling

If `unit.status == "in_progress"`, run the three-case logic. Skip this section if the unit is `pending` / `failed` / etc.

Determine **current user identity** (`git config user.email`, fall back to hostname or "unknown") and **current host** (`hostname` or equivalent).

### Case A — you are the holder, heartbeat fresh

`unit.in_flight.by == <current user>` AND `last_heartbeat` is < 15 min old.

Print:

```
Resuming <unit.id> — you started it <N> min ago at step "<in_flight.current_step>".
Files touched so far: <count> (<list first 3>).
```

Re-read the files in `in_flight.files_touched_so_far[]` plus all `source_paths`. Resume from `in_flight.current_step`. Skip to §3 ("Migrate body").

### Case B — different user, heartbeat fresh

Print:

```
WARNING: <in_flight.by> on <in_flight.host> is currently migrating <unit.id>.
  Heartbeat last bumped <N> min ago — they may be actively working.

  Options:
    [w] Wait and check status later
    [o] Override (take over). They may lose work if they push first.
    [d] Pick a different unit instead.
```

Default to `w` on unclear input. On `o`, treat the in-flight block as stale (proceed to §2 and overwrite); on `d`, return control to the caller with an indication that this unit was skipped.

### Case C — stale heartbeat (>15 min) or missing heartbeat block

Print:

```
A previously in-flight unit <unit.id> appears stalled (last heartbeat <N> min ago, started by <in_flight.by>).

  [r] Reclaim and resume
  [s] Skip — leave as in_progress, return to caller
  [a] Abort — reset to pending so it can be re-picked from scratch
```

On `r`: treat as Case A (you become the new holder; bump `last_heartbeat`). On `a`: reset `unit.status = "pending"`, clear `in_flight`, append history `{from: "in_progress", to: "pending", reason: "stalled-recovery"}`, save `.claude/modernize/units/<unit.id>.json`, return to caller. On `s`: return to caller.

## 2. Acquire the unit

Only run this if you are starting fresh (not Case A resume).

For `retry` mode, the unit's pre-retry status is `failed`. Before acquiring:

1. Move the existing `failure.diagnostic` (if any) into `failure.diagnostic_history[]` as `{ at: <unit's last history entry's at, or now>, diagnostic: <existing diagnostic>, retry_count: <current retry_count> }`.
2. Increment `unit.retry_count` by 1.
3. If `retry_prompt` was passed, set `unit.last_retry_prompt = <retry_prompt>`. Otherwise leave it as it was.
4. Clear `unit.failure.diagnostic` and `unit.failure.branch` (the old branch is preserved in `diagnostic_history`; new attempt gets a new branch if applicable).

Then for all modes, update `unit`:

```json
{
  "status": "in_progress",
  "history": [...existing, {
    "at": "<now>", "by": "<user>", "from": "<previous status>", "to": "in_progress", "session_id": "<sid>"
  }],
  "in_flight": {
    "started_at": "<now>",
    "by": "<user>",
    "host": "<hostname>",
    "session_id": "<sid>",
    "last_heartbeat": "<now>",
    "current_step": "reading source",
    "files_touched_so_far": []
  }
}
```

**Save the per-unit file immediately**: write the mutated unit object back to `.claude/modernize/units/<unit.id>.json`. This is what concurrent `/web-modernize:status` and the heartbeat hook read.

If top-level `state.status` is `auth_done` (i.e., this is the first feature unit), also flip it to `in_progress` and save `state.json`. This is the only top-level mutation this agent makes during normal operation.

## 3. Migrate body

This is the actual translation work.

### General algorithm

1. **Read all `source_paths`** in full, plus **every stylesheet they depend on** — sibling files in the same directory (`<source>.css`, `<source>.scss`, `<source>.less`), stylesheets referenced from the source markup via `<link rel="stylesheet">` or `@import`, and project-wide style files (`site.css`, `app.scss`, anything under `Content/`, `wwwroot/css/`, `src/main/webapp/resources/css/`, `assets/styles/`, etc.). The legacy visual design lives in those files; missing them produces "looks-nothing-like-the-original" output.
2. **Read related target context**: existing `target_paths[]` of migrated dependencies (read each dep's `units/<dep_id>.json` if you need their paths), the target framework's conventions, and any existing shared utilities under `apps/web-new/src/lib/` etc.

2b. **First-unit-only: translate cross-cutting chrome and wire global CSS.** If no feature unit has been migrated yet (the only `migrated`/`verified` units in `state.unit_ids[]` are `__auth__` or none), check the legacy tree for page-wrapping templates (master pages, layout files, includes, tiles — see `agents/permanent-gotchas.md` "Page-wrapping chrome and global stylesheets aren't 'units'") and the global stylesheets they reference. Translate them into the target's root layout file, import the legacy CSS from the entry, preserve the body wrapper class, and record the work in `notes/__layout__.md`. **Skip on subsequent units** — once chrome + CSS are in place, every feature unit inherits them by being rendered inside the layout.
3. **Update `in_flight.current_step = "designing target structure"`** and save the per-unit file.
4. **Decide target file layout** based on `unit.kind` and `state.target_stack.ui`/`.api`:
   - React/Vue/Svelte component → `apps/web-new/src/features/<feature>/` or `apps/web-new/src/pages/`.
   - API endpoint → `apps/api-new/src/routes/<area>/<verb>.ts` or framework equivalent.
   - Shared utility → `apps/web-new/src/lib/`.
5. **Create a feature branch** (recommended): `git checkout -b modernize/<unit.id>` — only if git is clean and the team allows. For `retry` mode, prefer a fresh branch name (e.g., suffix with `-retry-<retry_count>`) to keep failed-attempt history reviewable.
6. **Write target files**. Update `in_flight.files_touched_so_far` and `current_step` as you go and save the per-unit file periodically; the heartbeat hook keeps `last_heartbeat` fresh on every Write tool call.
7. **Translate semantics, not syntax** (data and logic):
   - WebForms event handlers → React event handlers + useState/useReducer.
   - Server-side controls (`<asp:GridView>`) → modern data table component.
   - ViewState → component state or query string, depending on intent.
   - Server-side validators → client + server validation.
   - JSP scriptlets → typed view models + template logic.
   - AngularJS controllers → modern composables / hooks.

7b. **Translate visuals, not just logic — preserve the legacy design.** This is as important as step 7. The user expectation is "the new page looks like the old page", not a clean-room re-design. A migration that produces correct data and broken-looking pages is a half-done migration.

   - **Detect the legacy design system.** Scan the stylesheets you read in step 1 for class-name prefix patterns. If a custom prefix appears in more than three distinct class names, treat it as a load-bearing design system. Common signals:
     - `esh-*` (Microsoft eShop reference apps)
     - `app-*`, `acme-*` (custom in-house BEM)
     - `btn-`, `card-`, `form-` (Bootstrap-derived but customised — check the rules)
     - `mat-`, `mdc-` (Material Design)
     - Framework defaults like `ng-`, `v-`, `data-bind` are NOT design-system classes; skip those.
   - **Honor `migration.md §3` declarations when present.** If the team has filled in "Legacy design system / custom CSS" in §3, that is authoritative — read it first, use it as the primary guide, and prefer it over heuristics.
   - **Match visual fidelity, not just functional fidelity.** When translating to the target styling system:
     - **Tailwind / utility-first**: do NOT silently flatten the legacy custom classes to generic utilities. For each custom class that encapsulates a repeated decorative pattern (padding + shadow + border-radius + bg-color, etc.), produce either (a) a `@apply`-style component class in the project's main CSS that maps to the utility combination, or (b) keep the legacy class name and add a corresponding rule in the global stylesheet. The visual definition can move to utilities; the *semantic name and visual result* should survive.
     - **CSS Modules / styled-components / Vue scoped styles**: prefer preserving the semantic class names from the legacy as the new component's style boundaries. The definition moves into the component file; the name stays.
     - **Material UI / Chakra / ready-made design libraries**: pick the closest library equivalent for each custom class. Write a brief mapping note in `notes/<unit.id>.md` so reviewers see the translation table.
   - **Verify asset references resolve.** For every `<img src="...">`, `background-image: url(...)`, `<link rel="icon">`, or `@font-face src="..."`:
     - If the path points at a directory under the legacy `Pics/`, `images/`, `Content/`, `wwwroot/`, `fonts/`, etc., the file should already exist in the target's `public/` (copied by `/web-modernize:scaffold`'s asset-copy step).
     - If the asset is missing, do NOT silently break the reference. Add a `// TODO: asset missing — copy from <legacy path>` comment near the reference and add a "Gotchas — missing assets" note in `notes/<unit.id>.md` with the expected target path.
     - If the legacy uses absolute URLs like `/Content/Pics/foo.png` and the target framework serves `public/` at a different base path (e.g., Next.js basePath, Vite base config, custom prefix), surface the discrepancy in the unit's notes.
   - **Record the design translation in notes.** Append to `notes/<unit.id>.md` a "Design translation" section. Format: a short table mapping each legacy custom class used in this unit to its target translation (Tailwind utilities, CSS module class, component library equivalent), plus any rules that ended up in shared CSS rather than per-component styles.

7c. **Tests — translate legacy first, then top up to coverage threshold.** Read `state.testing.ui_framework`, `state.testing.api_framework`, and `state.testing.target_pct` (seeded by `/web-modernize:plan` from `migration.md §12`). Pick the framework that matches this unit's `target_paths` (UI framework if paths fall under `state.scaffold.ui.path`, API framework if under `state.scaffold.api.path`, or run both for cross-cutting units). If the relevant framework is `"manual"` or `"n/a"`, record `unit.tests = { "framework": "<value>", "skipped_reason": "<manual|n/a>" }` and skip the rest of 7c.

   **Step 1 — Scan for legacy tests touching this unit's `source_paths`.** Conventions per detected source stack (`state.source_stack.primary_framework` or analysis.json):
   - **NUnit / MSTest** (.NET legacy): walk sibling `*.Tests/` or `Tests/` directories; match by namespace + the class-under-test name; also grep for `using` directives or constructor references to the unit's source types.
   - **JUnit** (Java legacy): walk `src/test/java/`; match by package + class-under-test name; grep for `@Autowired` / direct imports of the unit's classes.
   - **Jasmine / Karma / Mocha** (AngularJS / classic JS legacy): walk `**/*.spec.js`, `**/*.test.js`; match `describe(...)` titles and `import`/`require` paths against the unit's source files.
   - **pytest / unittest** (Python legacy): walk `tests/test_*.py` and `*_test.py`; match imports of the unit's modules.
   - **Other** (no recognised legacy test stack): skip directly to Step 5 (generation from scratch).

   Collect all matched legacy test files into `legacy_tests[]`.

   **Step 2 — Translate the translatable ones.** For each file in `legacy_tests[]`:
   - **Skip if disabled.** Markers: `[Ignore]`, `[Skip]`, `@Disabled`, `@Ignored`, `xit`, `xdescribe`, `@pytest.mark.skip`, `@pytest.mark.skipif`. Record in `unit.tests.skipped_legacy[]` as `{ "path": "<legacy path>", "reason": "<marker>" }`.
   - **Translate enabled tests** to the target framework chosen in `migration.md §12`. Preserve test names verbatim where the target syntax allows (`should_return_404_when_id_missing` works in pytest, vitest, junit, xunit identically). Translate:
     - Assertions: `Assert.AreEqual(x, y)` → `assert x == y` / `expect(x).toBe(y)` / `assertEquals(x, y)`.
     - Mock libraries: `Moq` (`new Mock<IFoo>()`) → `unittest.mock.MagicMock` / `vi.fn()` / Mockito `@Mock`. Spring `@MockBean` → pytest fixture providing a stub via `app.dependency_overrides[]`. Jasmine `spyOn` → `vi.spyOn` / `jest.spyOn`.
     - Fixtures / setup-teardown: NUnit `[SetUp]` / `[TearDown]` → pytest fixture with `yield` / `@BeforeEach` / `beforeEach`.
     - Parameterised cases: NUnit `[TestCase(...)]` → `pytest.mark.parametrize` / `it.each` / JUnit `@ParameterizedTest`.
     - HTTP test infrastructure: ASP.NET `TestServer` / `WebApplicationFactory` → FastAPI `TestClient`; Spring `MockMvc.perform(get(...))` → equivalent in the target stack's idiomatic client.
   - **Note untranslatable tests** — those depending on legacy infrastructure with no clean target equivalent (e.g., IIS-hosted integration tests against COM components, ColdFusion CFC mocks, ASP.NET server-control state). Record in `unit.tests.untranslatable[]` as `{ "legacy_path": "<path>", "reason": "<one-line reason>" }` and append an "Untranslated legacy tests" subsection to `notes/<unit.id>.md` describing what would be needed to port them.
   - **Write translated tests** to the conventional location for the target framework (e.g., `tests/test_<unit.id>.py` for pytest, `<unit-dir>/<UnitName>.test.tsx` colocated for vitest, `src/test/java/.../<UnitName>Tests.java` for junit, `tests/<Project>.Tests/<UnitName>Tests.cs` for xunit).
   - Add each written path to `unit.tests.translated_from[]` mapping `{ "legacy_path": "<path>", "target_path": "<path>", "tests_in_file": <count> }`.

   **Step 3 — Run translated tests with coverage** scoped to this unit's `target_paths`. Pick the command from `state.testing.<subsystem>_framework`:

   | Runner | Scoped coverage command |
   |---|---|
   | `vitest` | `npx vitest run --coverage --coverage.include='<target_paths joined as glob>'` |
   | `jest` | `npx jest --coverage --collectCoverageFrom='<target_paths>' <test_file_globs>` |
   | `karma-jasmine` | `ng test --watch=false --code-coverage --include='<target_paths>'` |
   | `pytest` | `pytest --cov=<target_paths joined as dotted modules> --cov-report=json:.coverage.json <test_file_paths>` |
   | `xunit` / `nunit` / `mstest` | `dotnet test --collect:"XPlat Code Coverage" /p:Include="<target_paths>"` then parse the Cobertura XML for line coverage |
   | `junit5` | `./mvnw -q test jacoco:report -Djacoco.includes=<target_paths joined>` then parse `target/site/jacoco/jacoco.xml` |

   Parse the report into:
   ```json
   {
     "pct": <integer 0–100, line coverage>,
     "uncovered_regions": [
       { "file": "<target path>", "line_range": "<start-end>", "branch_description": "<one-line summary of the uncovered branch>" }
     ]
   }
   ```

   If the translated tests **fail to run** (compile error, import error, runtime exception that aborts the test runner — not just an assertion failure), surface that as a hard fail via §4 with diagnostic `Translated legacy tests failed to run: <stderr tail>. The translation may have missed a fixture/mock; review tests.translated_from and either fix or move to tests.untranslatable.` Do not proceed to Step 4.

   Assertion failures inside translated tests are also a hard fail (the legacy behaviour you tried to preserve doesn't actually match), with diagnostic `Translated legacy test <test_name> failed: <assertion message>. The new implementation does not match the legacy behaviour the test encodes — fix the implementation or update the test if the change is intentional.`

   **Step 4 — Top up to `target_pct` if below.** If `coverage.pct >= state.testing.target_pct`, skip to Step 5.

   Otherwise, for each entry in `uncovered_regions`:
   - Read the **legacy source** at the corresponding location (use the source-to-target line map you built in step 4, or grep the legacy file for the equivalent branch). Understand what behaviour the uncovered branch encodes.
   - Generate a targeted test that exercises that branch by **observable behaviour** — given input X (or state Y), the unit produces output Z. Avoid asserting on internal implementation (no "this private method was called twice"; that's brittle and tautological against the code you just wrote).
   - Pull additional context from `migration.md §10` acceptance criteria and the request/response schema (for API units) when designing the assertion.
   - Append the new test to the appropriate test file (or create a new `tests/test_<unit.id>_generated.py` / `<UnitName>.generated.test.tsx` if the layout calls for it).
   - Increment `unit.tests.generated_count`.

   Re-run scoped coverage (Step 3). Compare `pct` to `target_pct` again. Iterate up to **2 generation passes total**. After pass 2, take the result as final regardless of whether the threshold was met — do NOT iterate further (auto-generation loops can rot context and produce nonsense; the 2-pass cap is a deliberate ceiling).

   **Step 5 — Record final tests block on the unit.** Build `unit.tests`:
   ```json
   {
     "framework": "<runner>",
     "translated_from": [...],
     "translated_count": <N>,
     "skipped_legacy":   [...],
     "untranslatable":   [...],
     "generated_count":  <N>,
     "coverage": {
       "pct": <final pct after pass 2>,
       "target_pct": <state.testing.target_pct>,
       "below_threshold": <pct < target_pct>,
       "uncovered_regions": [...]   // only present when below_threshold
     }
   }
   ```

   Update `in_flight.current_step = "tests written"` and save the per-unit file. Proceed to step 8.

8. **Add a placeholder test** (smoke test at minimum). The `migration.md §10` acceptance criteria should drive what is asserted. (Step 7c may have already produced this — skip if `unit.tests.translated_count + unit.tests.generated_count > 0`.)
9. **Append to `notes/<unit.id>.md`**: design decisions, source-to-target symbol map, gotchas. For `retry` mode, add a "Retry #<N>" section that records what was different this time and (if `retry_prompt` was set) quote the user's override verbatim. The "Design translation" section from step 7b lives in this same notes file.

### Honor `retry_prompt` when set

If `retry_prompt` is set (retry mode only), it is the **first** thing you should read after the source files, and it should bias every design decision below. Treat it like a senior engineer's design note: "the prior attempt assumed X — try Y instead". Do not silently ignore it; if any part conflicts with `migration.md`, surface the conflict to the user and ask which wins.

### Honor `force_deps` when set

If `force_deps == true` (set by `/migrate --force` after the user explicitly overrode the dependency block), expect symbols imported from unmet deps to be unavailable. Stub them, leave a `// TODO: provided by <dep.id>` comment, and record the workaround in `notes/<unit.id>.md` under "Gotchas — out-of-order migration". Do not fail just because a dep is missing.

If `force_deps` is `false` or absent, assume the caller verified deps are satisfied. If you still discover a missing symbol during translation that should have been provided by a dep, fail in §4 with a diagnostic explaining the discrepancy.

## 4. Stop conditions (failure)

Set `unit.status = "failed"` and stop if:

- A required source file is missing or unreadable.
- The target framework cannot represent something critical (e.g., a custom WebForms control with no obvious equivalent — flag for human design review).
- A test that *should* pass is failing in a way that suggests the migration is incorrect (not just a missing fixture).
- A dep symbol is missing and `force_deps` was not set (unexpected discrepancy with the caller's dep check).

On stop, write to `.claude/modernize/units/<unit.id>.json`:

```json
{
  "status": "failed",
  "in_flight": null,
  "failure": {
    "diagnostic": "<one-paragraph explanation of what stopped you and what you tried>",
    "branch": "modernize/<unit.id>",
    "diagnostic_history": <existing array, possibly populated by retry mode>
  }
}
```

Append a history entry. Print the diagnostic to the user with three suggested recovery paths:

```
✗ Migration of <unit.id> failed.

Diagnostic:
  <one-paragraph>

Recovery options:
  - /web-modernize:retry <unit.id>  (re-attempt, optionally with --with-prompt="…")
  - /web-modernize:rollback --unit <unit.id>  (revert any partial target files first, then retry)
  - /web-modernize:abandon --unit <unit.id>  (declare this unit out of scope)
```

Return control to the caller. Do NOT auto-advance to another unit.

## 5. Finalize successful migration

Finalisation has two parts: a **smoke-test gate** (§5a) that must pass before the unit can be declared migrated, and the **state write** (§5b) that only runs on a green gate. A failed smoke test does NOT silently downgrade — it routes through the §4 failure path so the user sees the actual reason and gets `/retry` as an option.

### 5a. Smoke-test before finalising

After all target files are written but **before** writing `status = "migrated"`, exercise the generated code. Behaviour depends on which subsystem(s) the unit's `target_paths` touched (compare each path against `state.scaffold.ui.path` and `state.scaffold.api.path`):

**API-touching unit.** Boot the dev server in the background, working dir = `state.scaffold.api.path`. Pick the command by `state.target_stack.api`:

| Stack | Boot command | Health probe |
|---|---|---|
| `fastapi` | `uvicorn app.main:app --port <free-port>` | `GET /health` |
| `nestjs` | `npm run start:dev -- --port <free-port>` | `GET /health` |
| `spring-boot-3` | `./mvnw -q spring-boot:run -Dspring-boot.run.arguments=--server.port=<free-port>` | `GET /actuator/health` (fall back to `/health`) |
| `dotnet-minimal-api` | `dotnet run --urls http://localhost:<free-port>` | `GET /health` |
| other | record `"smoke": "skipped — no recipe"`, skip to §5b | — |

Pick a free port (e.g., sample from 50000–60000 and check it's unused). Wait up to 30 seconds polling the health probe; if it never returns 2xx, treat as smoke failure with diagnostic `boot failed: health endpoint did not respond within 30s`.

Once healthy, for **each endpoint this unit added** (parse the route declarations in the files you wrote — e.g., FastAPI `@router.get/post/...`, NestJS `@Get/@Post`, Spring `@GetMapping`, ASP.NET `app.MapGet/MapPost`):

1. Build a representative request. Sources, in order of preference: (a) an example value in the unit's acceptance criteria from `migration.md §10`; (b) the declared request schema's `example`/`examples` field; (c) a parameter-free GET for GETs with no required params; (d) a POST with the schema's example values filled in.
2. Issue the request. Use `curl` from a shell or an in-process HTTP client.
3. Assert **HTTP 2xx** AND the response body conforms to the declared response schema, including: every non-Optional field is present, every non-Optional nested object is non-null and has the keys the schema declares (this is what catches lazy-load / serialisation bugs — the field is in the schema, the JSON has `null`, so the check fails), and array fields are arrays (not `null`).

Tear the server down (kill the background process group) regardless of outcome.

**UI-touching unit.** From `state.scaffold.ui.path`, run `npm run build` and `npm run typecheck`. Both must exit 0. Capture stderr tail on failure.

**Cross-cutting unit** (paths in both UI and API): run both blocks; either failing is a smoke failure.

**No-recipe stack** (custom/other API, or unit touches neither subsystem): record `"smoke": "skipped — no recipe"` on the unit and proceed to §5b. Graceful degrade — never block unknown stacks.

**Run the unit's scoped tests + coverage.** After the boot+curl / build-and-typecheck steps pass, re-run the scoped coverage command from step 7c (the same command that produced `unit.tests.coverage`). The 7c run was a one-shot during the migration body; this re-run is the gate, so it must produce a fresh result the gate can act on.

Decision tree:

| Result | Action |
|---|---|
| Tests pass AND `coverage.pct >= state.testing.target_pct` | Green. Proceed to §5b. |
| Tests pass AND `coverage.pct < state.testing.target_pct` | **Soft-fail on coverage.** Proceed to §5b with `unit.tests.coverage.below_threshold = true`. Print the yellow warning (see below). Do NOT take §4's hard-fail path. |
| Test runner / coverage tool **errors out** (non-zero exit that is not just "some tests failed" — e.g., import error, config error, the binary crashed) | **Hard fail.** Take §4 with diagnostic `<runner> exited with code <N>: <stderr tail>. The test harness itself broke; check tests/conftest.py or the runner config.` |
| Tests **fail** (assertion failures or expected-pass tests reporting red) | **Hard fail.** Take §4 with diagnostic `<X>/<Y> tests failed in <unit>: <first-failing-test-name>: <first-failure-assertion-message>. The new implementation may not preserve the legacy behaviour the failing test encodes — review and fix the implementation, or /retry with --with-prompt explaining the intentional change.` |

Yellow warning for the soft-fail-on-coverage case (printed after §5b writes the migrated record):

```
⚠ Unit <unit.id> migrated, but test coverage below target.
  Coverage: <pct>%  (target: <target_pct>%)
  Uncovered:
    - <file>:<line-range> — <branch_description>
    ...
  The unit is finalised. To raise coverage, edit the tests and re-run /web-modernize:verify <unit.id>
  (verify will re-measure coverage and clear the below_threshold flag once you cross target).
```

If `unit.tests.framework` is `"manual"` or `"n/a"` (the test harness was opted out at scaffold time), skip the test+coverage gate entirely and proceed to §5b. The functional smoke (boot+curl / build/typecheck) still applies — that part never depends on the test runner.

#### On smoke failure

Take the §4 failure path. Write to `.claude/modernize/units/<unit.id>.json`:

```json
{
  "status": "failed",
  "in_flight": null,
  "failure": {
    "diagnostic": "<one-paragraph explanation including the actual response body or build error, not just 'tests failed'>",
    "branch": "modernize/<unit.id>",
    "diagnostic_history": <existing array>,
    "smoke": {
      "kind": "api" | "ui" | "both" | "tests" | "coverage",
      "endpoint": "<method> <path>",                  // when kind includes api
      "response_status": <HTTP code>,                  // when kind includes api
      "response_body_excerpt": "<first ~2KB of body>", // when kind includes api
      "build_command": "<cmd>",                        // when kind includes ui
      "build_stderr_tail": "<last ~40 lines>",         // when kind includes ui
      "test_runner": "<vitest|pytest|...>",            // when kind == "tests"
      "tests_failed": "<X/Y>",                         // when kind == "tests"
      "first_failing_test": "<name>",                  // when kind == "tests"
      "first_failure_message": "<assertion message>"   // when kind == "tests"
    }
  }
}
```

The diagnostic MUST be specific enough that `/web-modernize:retry --with-prompt="…"` can paste it back as the override hint. Example diagnostics:

- `Smoke-test boot+curl: GET /catalog/items returned 200, but response body has "catalog_brand": null for every item — declared schema CatalogItemRead.catalog_brand is non-Optional. Likely cause: SQLAlchemy relationship() lazy-loaded after session close. Try eager loading via .options(joinedload(CatalogItem.catalog_brand), joinedload(CatalogItem.catalog_type)).`
- `Smoke-test UI build: 'npm run typecheck' failed with TS2304: Cannot find name 'useCartContext'. Likely cause: missing import or unmet dependency from <dep.id>.`
- `Smoke-test tests: 2/7 translated legacy tests failed: test_catalog_get_by_id_returns_404_when_missing failed with AssertionError: expected 404, got 500. The new GET /catalog/items/{id} raises instead of returning 404 — wrap the DB lookup and translate NoResultFound to HTTPException(404).`
- `Smoke-test tests: pytest exited with code 4 (collection error): ImportError while importing test module tests/test_catalog.py: cannot import name 'CatalogItemRead' from 'app.schemas'. The translated test references a schema that doesn't exist in the new code — either add the missing export or fix the test's import.`

Append a history entry and print the diagnostic with the existing recovery options banner from §4 (`/retry`, `/rollback`, `/abandon`). Return to caller. Do NOT advance.

### 5b. On smoke success — write the migrated record

Write to `.claude/modernize/units/<unit.id>.json`:

```json
{
  "status": "migrated",
  "target_paths": [<actual paths written>],
  "in_flight": null,
  "smoke": {
    "ran_at": "<now>",
    "kind": "api" | "ui" | "both" | "skipped",
    "endpoints_hit": [{ "method": "GET", "path": "/catalog/items", "status": 200, "schema_ok": true }],
    "build":   { "command": "npm run build && npm run typecheck", "exit_code": 0 },
    "tests":   { "runner": "<vitest|pytest|...>", "passed": <X>, "total": <Y>, "exit_code": 0 },
    "coverage_check": { "pct": <integer>, "target_pct": <integer>, "below_threshold": <bool> }
  },
  "tests": {
    "framework": "<runner>",
    "translated_from": [...],
    "translated_count": <N>,
    "skipped_legacy":   [...],
    "untranslatable":   [...],
    "generated_count":  <N>,
    "coverage": {
      "pct": <integer>,
      "target_pct": <integer>,
      "below_threshold": <bool>,
      "uncovered_regions": [...]  // only when below_threshold
    }
  },
  "history": [...existing, { "at": "<now>", "by": "<user>", "from": "in_progress", "to": "migrated", "session_id": "<sid>" }]
}
```

Omit the irrelevant sub-fields (e.g., `endpoints_hit` for a pure UI unit, `build` for a pure API unit). For a no-recipe functional smoke stack, `smoke.kind = "skipped"` with `smoke.reason = "no recipe for <stack>"`. For a `manual` / `n/a` test framework, omit `smoke.tests` and `smoke.coverage_check`, and set `tests.framework = "<value>"` with `tests.skipped_reason = "<manual|n/a>"`.

If `coverage_check.below_threshold == true`, print the yellow warning from §5a after the §5b write completes. The unit is still finalised as `migrated` — this is the soft-fail policy.

Update `state.json.updated_at`. Do not touch any other top-level field (status stays `in_progress`; transition to `complete` is `/web-modernize:verify`'s job).

## 6. Return to the caller

The caller (`/next`, `/migrate`, or `/retry`) is responsible for the user-facing closing message — they each have slightly different next-step nudges. Hand back:

- The final `unit.status` (`migrated` or `failed`).
- The list of target paths actually written.
- The notes file path.

The caller will print the success/failure banner appropriate to its mode.
