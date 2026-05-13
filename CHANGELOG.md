# Changelog

All notable changes to the `web-modernize` plugin are documented here. Versioning follows [Semantic Versioning](https://semver.org/).

## [0.5.0] - 2026-05-13

Builds on 0.4.0's execution-based gates. Those gates answer "does it run?"; this release answers "does it preserve the legacy behaviour?". The plugin now picks the test framework at `migration.md` time (with per-stack suggestions), scaffolds a working test harness with a sample test at `/scaffold` time, translates legacy unit tests to the target framework at `/migrate` / `/next` / `/retry` time, and generates additional tests to top up to the team's coverage bar (default 80%). Coverage below target is a **soft fail** — the unit still finalises, but with a `below_threshold` flag and a warning listing the uncovered regions, so a flaky coverage measurement never blocks a working migration.

### Added
- **`templates/migration.md §12 "Testing" — REQUIRED** — three new fields (UI test framework, API test framework, target coverage %) with stack-aware suggestions printed inline (vitest for Vite UIs, jest for Next/Nest, karma-jasmine for Angular, pytest for FastAPI, xunit for .NET, junit5 for Spring Boot). `/web-modernize:plan` validates all three before generating the plan; missing → numbered failure report.
- **`state.json.testing` block** — written by `/plan` from §12. Single source of truth for which runner `/scaffold` installs and which coverage bar the migrator and `/verify` measure against. Re-plans overwrite from §12; switching runners mid-migration does not retroactively re-translate already-migrated units.
- **`skills/scaffold/SKILL.md` "Test harness" sub-step** — runs after the framework CLI / API skeleton creation and before the smoke-build gate. Per-runner recipes for vitest, jest, karma-jasmine, pytest, xunit/nunit/mstest, junit5: install the runner + coverage tool, write the config file (`vitest.config.ts`, `pyproject.toml [tool.pytest.ini_options]`, JaCoCo plugin, etc.), create the test directory in the framework's convention (`tests/` with `conftest.py` for pytest, colocated `*.test.tsx` for vitest, `src/test/java/` for junit, etc.), write one passing sample test against `/health` (API) or the placeholder root (UI), and add `test` / `test:coverage` scripts. `manual` / `n/a` runners record `"test_harness": "manual"` and skip auto-install (soft-skip).
- **`skills/scaffold/SKILL.md` smoke-build gate test-harness extension** — in addition to the install+build smoke from 0.4.0, the gate now runs a test-harness smoke (`pytest -q tests/test_health.py`, `npm run test -- --run`, `dotnet test --no-build`, `./mvnw -q test`, etc.) that proves the harness picks up and runs the sample test. Both smokes must exit 0 before the subsystem flips to `done`. Records `scaffold.<subsystem>.smoke.test_harness = { runner, command, exit_code }`.
- **`agents/unit-migrator.md` step 7c "Tests — translate legacy first, then top up to coverage threshold"** — new step in §3 between visuals (7b) and the placeholder-test fallback (8). Scans for legacy tests touching the unit's `source_paths` (NUnit/MSTest, JUnit, Jasmine, pytest conventions per detected source stack); translates enabled tests to the target framework preserving names and assertion intent (mocks/fixtures/parameterised cases included); records disabled tests in `tests.skipped_legacy` and infrastructure-bound tests in `tests.untranslatable`; runs translated tests with scoped coverage; if `pct < target_pct`, generates targeted behavioural tests for uncovered regions using the legacy code's observable behaviour as the spec; iterates up to **2 generation passes** then accepts the result (deliberate ceiling — auto-generation loops can rot context).
- **`agents/unit-migrator.md` §5a smoke gate test+coverage extension** — after boot+curl / build+typecheck, the gate now runs the unit's scoped tests with coverage. Decision tree: tests pass + coverage ≥ target → green. Tests pass + coverage < target → **soft-fail on coverage**, unit still finalises as `migrated` with `tests.coverage.below_threshold = true` and a yellow warning listing the uncovered regions. Test runner errors out (collection/import/config) → **hard fail** via §4 with a runner-specific diagnostic. Test assertions fail (the new implementation doesn't match the legacy behaviour the translated test encodes) → **hard fail** with the first-failing-test + message in the diagnostic so `/retry --with-prompt` can act on it.
- **`templates/unit.schema.json` — optional `tests` block** — additive (no `schema_version` bump). Tracks `framework`, `translated_from[]` (legacy_path → target_path), `translated_count`, `skipped_legacy[]`, `untranslatable[]`, `generated_count`, and `coverage` (pct, target_pct, below_threshold, uncovered_regions).
- **`skills/verify/SKILL.md` aggregate coverage post-check** — built-in `run_when: "before_complete"` post-check that runs project-wide coverage when `state.testing.target_pct` is set. Per-unit `tests.coverage` blocks are refreshed (cross-unit regressions caught: a unit that was above target can be flagged below if other units' changes broke its coverage). The aggregate result is recorded in `state.testing.last_aggregate_check`. **Soft-fail at the aggregate level too** — below-target prints a yellow warning listing the offending units but still flips `state.status` to `complete`.

### Changed
- **`skills/plan/SKILL.md` Preflight validation** — three new required fields (UI test framework, API test framework, target coverage %) added to the validation table. Plan stops with a numbered missing-fields report if §12 is incomplete. `state.json` write now includes a `testing` block; re-plans overwrite it from §12.
- **`agents/unit-migrator.md` §5b migrated record schema** — `smoke` now carries `tests` (runner, passed/total) and `coverage_check` (pct, target_pct, below_threshold) sub-blocks in addition to the 0.4.0 `endpoints_hit` / `build` sub-blocks. The full `unit.tests` block (translated/skipped/generated/coverage) is also written alongside `smoke` on success. `manual` / `n/a` frameworks omit the test+coverage smoke sub-blocks gracefully.
- **`agents/unit-migrator.md` step 8 ("Add a placeholder test")** — now a no-op when 7c already produced real tests (the common case). Only fires when the team is on a `manual` / `n/a` runner and the agent wants to leave a TODO marker.

### Why this isn't a breaking change
No `schema_version` bump (state remains v3; the `tests` block on each unit is additive and ignored by anything that doesn't read it). The new `state.testing` block is new — older `state.json` files predating 0.5.0 will lack it, in which case `/scaffold`, the migrator's 7c, and `/verify`'s aggregate check all detect the absence and degrade to "manual / skip" gracefully. Teams already mid-migration on 0.4.0 can keep working without filling in §12; new units they migrate will skip 7c (recording `tests.skipped_reason = "state.testing not configured"`) until they re-run `/plan` after editing §12. `manual` / `other:` framework values also degrade to skip — never block.

### Out of scope (deferred)
- Mutation testing / property-based testing — overkill for behavioural-parity migration; revisit if a team asks.
- Hard-fail coverage mode — left out per the 0.5.0 soft-fail policy. A future minor could add `coverage_policy: "hard" | "soft"` in §12 if teams want it.
- E2E / browser tests (Playwright, Cypress) — different bar than unit coverage; out of scope for this release.

## [0.4.0] - 2026-05-13

Driven by a real FastAPI migration that surfaced two bugs the plugin should have caught: a hatchling `pyproject.toml` missing `[tool.hatch.build.targets.wheel] packages = ["app"]` (so `pip install -e ".[dev]"` failed), and SQLAlchemy routes using plain `.query()` for models with `relationship()` (so Pydantic serialised nested fields as `null` after the session closed). Common cause in both: the plugin generated artefacts and trusted the LLM that they worked, without ever executing them. This release adds execution-based gates at both production points.

### Added
- **`skills/scaffold/SKILL.md` "Smoke-build the subsystem"** — new mandatory gate between writing each subsystem's files and flipping `state.scaffold.<subsystem>.status` to `"done"`. Runs the install + build command for the chosen stack (e.g., `pip install -e ".[dev]" && python -c "import app.main"` for FastAPI, `dotnet build` for .NET, `./mvnw -q -DskipTests package` for Spring Boot, `npm install && npm run build` for Node-based UIs and NestJS) and records `smoke.command`, `smoke.exit_code`, `smoke.stderr_tail` on the subsystem block. On non-zero exit the subsystem stays `in_progress`, the user sees the captured stderr tail, and scaffold stops — does not advance to the next subsystem or to `state.status = "scaffolded"`. Unknown stacks record `"smoke": "n/a"` and proceed (graceful degrade).
- **`agents/unit-migrator.md` §5a "Smoke-test before finalising"** — new mandatory gate between writing target files and flipping `unit.status = "migrated"`. For API-touching units, boots the dev server (uvicorn for FastAPI, `dotnet run` for .NET, `./mvnw spring-boot:run` for Spring, `npm run start:dev` for NestJS) on a free port, waits for the health probe, hits each endpoint the unit added with a representative request derived from `migration.md §10` acceptance criteria or the schema's example values, and asserts both HTTP 2xx and that the response body conforms to the declared response schema field-for-field (non-Optional nested objects must be non-null with the declared keys — this is what catches lazy-load / serialisation bugs). For UI-touching units, runs `npm run build && npm run typecheck`. Cross-cutting units run both blocks. On any failure, takes the existing §4 failure path with a smoke-specific diagnostic that includes the actual response body or build error (specific enough that `/web-modernize:retry --with-prompt="…"` can paste it back). On success, records a `smoke` block on the unit alongside the migrated status. Unknown stacks record `"smoke": "skipped — no recipe"` and proceed.

### Changed
- **`skills/scaffold/SKILL.md` Per-subsystem checklist intro** — now states explicitly that the smoke-build gate must pass before a subsystem can be marked `done`, and that a failed gate halts scaffold rather than advancing.
- **`agents/unit-migrator.md` §5 structure** — split into §5a (smoke-test gate) and §5b (write the migrated record). A failed smoke test routes through §4's failure path so the user sees the actual reason and gets `/retry` as an option, instead of silently flipping to a status they'd later discover was broken.

### Why this isn't a breaking change
No schema bump (state remains v3). The new `smoke` blocks are additive fields on `scaffold.<subsystem>` and on each unit; existing tooling that doesn't read them is unaffected. No skill renamed or removed. Stacks without recipes degrade to `"smoke": "n/a"` / `"skipped"` rather than blocking — teams using custom or other stacks see no behaviour change. Teams whose scaffold already ran on 0.3.x and is already `scaffolded` keep working as-is; the new gates apply to new scaffold runs and new unit finalisations.

### Out of scope (future work)
This release deliberately does NOT ship per-stack template files (e.g., a tested `pyproject.toml` the scaffold copies verbatim) or a "Backend translation patterns" idioms section in unit-migrator. Both are useful follow-ups but were excluded so the execution-based safety net could ship without expanding scope; the gates will catch a future bad `pyproject.toml` or a missing `joinedload` even before those follow-ups land.

## [0.3.1] - 2026-05-12

Bug-fix patch driven by a real testing session. Migrated pages were looking wrong (custom legacy design system flattened to generic utility classes) and assets (images, favicon, fonts) were missing from the target's `public/` directory because the plugin didn't instruct Claude to handle either concern.

### Added
- **`agents/unit-migrator.md` §3 step 7b "Translate visuals, not just logic — preserve the legacy design"** — new explicit guidance to read adjacent CSS/SCSS/LESS files alongside `source_paths`, detect custom design-system class-name prefixes (e.g., `esh-*`, `app-*`), preserve visual fidelity when translating to Tailwind / CSS Modules / Material UI / etc., verify asset references resolve to the target `public/`, and append a "Design translation" mapping table to `notes/<unit.id>.md`.
- **`skills/scaffold/SKILL.md` "Copy legacy assets" step** — scans the legacy tree for common asset directories (`Pics/`, `images/`, `Content/`, `wwwroot/`, `assets/`, `fonts/`, `static/`, top-level favicons) and copies them into the target UI's `public/` (or `src/assets/` for Angular). Honors `migration.md §3` declared paths as authoritative when present; falls back to heuristics otherwise. Detects absolute-URL references in legacy CSS (e.g., `url('/Content/Pics/foo.png')`) and warns about target framework basePath implications. Idempotent — never overwrites existing target files.
- **`/web-modernize:scaffold --assets-only` flag** — runs ONLY the asset-copy step (skips framework/API/DB scaffolders and `verify.config.json` updates). For teams whose scaffold ran on a pre-0.3.1 plugin and need to backfill missing assets without touching the rest. Precondition: `state.status >= "scaffolded"`. Does not advance top-level status.
- **`templates/migration.md` §3 optional sub-sections** — "Legacy design system / custom CSS" (class-name prefixes, stylesheet locations, notes) and "Asset directories" (explicit list of paths in the legacy tree). If filled, both `/scaffold` and the migrator use them as authoritative; if blank, heuristics apply.

### Changed
- **`agents/unit-migrator.md` §3 step 1** — now also reads stylesheets adjacent to `source_paths` (sibling `*.css`/`*.scss`/`*.less`, files referenced via `<link>` / `@import`, project-wide style files), not just the source files. The legacy visual design lives in those stylesheets; reading them upfront is essential to preserving fidelity in step 7b.

### Why this isn't a breaking change
No schema bump (state remains v3). No skill renamed or removed. No behavior removed — only additive guidance and a new step. Existing scaffolds keep working; teams who hit the asset gap can run `/web-modernize:scaffold --assets-only` to backfill.

## [0.3.0] - 2026-05-12

### Breaking changes
- **`state.schema.json` bumped to v3.** Per-unit state moves out of `state.json.units[]` into one file per unit at `.claude/modernize/units/<unit-id>.json`. Top-level `state.json` now carries only workflow status, stacks, scaffold, lock, and an ordered `unit_ids` array.
- **`/web-modernize:init` no longer migrates older state files.** No schema-migration scripts ship with the plugin (the v1→v2 migrator added in 0.2.0 has been removed). If `state.json` exists with `schema_version != 3`, `/init` refuses with a clear message and asks the user to delete `.claude/modernize/` and re-init.
- **`/web-modernize:migrate <id>` now blocks on unmet dependencies by default.** Pass `--force` to restore the previous warn-and-stub behavior; the agent will stub missing dep imports with `// TODO: provided by <dep.id>` comments and record the override in `notes/<id>.md`.

### Added
- **`templates/unit.schema.json`** — per-unit object schema, referenced by every per-unit file under `.claude/modernize/units/`.
- **`.claude/modernize/units/`** directory created by `/init`. Tracked in git via `.gitkeep`.

### Changed
- **Per-unit file layout for multi-developer concurrency.** Two developers working on different units now edit completely different files; git merges trivially with zero conflicts. The headline win for teams that coordinate offline (standup-style) and pick disjoint units.
- **`/web-modernize:init`** — emits a schema v3 bootstrap state. Creates `.claude/modernize/units/` and `.claude/modernize/notes/` with `.gitkeep` files. Removes the v1→v2 schema migration block.
- **`/web-modernize:plan`** — seeds units by writing one file per unit to `.claude/modernize/units/<id>.json`. Maintains `state.unit_ids` in plan order. The re-runnable history-preservation logic now reads/writes the per-unit file instead of an in-memory array.
- **`/web-modernize:next`, `/migrate`, `/retry`, `/rollback`** — all read/write `.claude/modernize/units/<id>.json` instead of `state.units[]`. `/migrate` adds `--force` and blocks by default on unmet deps.
- **`/web-modernize:verify`, `/status`, `/report`, `/auth`, `/abandon`** — refactored to iterate `units/*.json` or the per-unit file by id. `/auth` now writes the synthetic `__auth__` unit to `units/__auth__.json` and ensures it heads `state.unit_ids`. `/abandon --soft` clears every per-unit file and resets `unit_ids: []`; `--hard` deletes `.claude/modernize/` including `units/`; `--unit <id>` writes one per-unit file and prunes the dep from every other unit's `depends_on`.
- **`/web-modernize:sync`** — per-file merge for `units/*.json` (Cases 1/2/3: only-on-remote → take, only-on-local → keep, both → field-level merge). Top-level `state.json` merge unchanged in spirit but updated for `unit_ids` and the schema v3 shape.
- **`agents/unit-migrator.md`** — all unit mutations write `units/<id>.json`. Top-level `state.json` is touched only for the `auth_done → in_progress` transition. Accepts a `force_deps` flag from `/migrate --force` to enable the stub-with-TODO behavior on demand.
- **`hooks/heartbeat.mjs`** — walks `.claude/modernize/units/*.json` instead of `state.json.units[]`. Heartbeat updates land in the per-unit file only; the hook no longer touches `state.json` at all, keeping the top-level file conflict-free across concurrent edits.

### Removed
- v1→v2 schema-migration block from `skills/init/SKILL.md` (added in 0.2.0). No migration scripts ship with the plugin going forward; schema bumps require a fresh `/init`.

### Versioning
- `state.schema.json` `schema_version` bumped to `3`. No automated migration from v1 or v2. To upgrade an existing repo, delete `.claude/modernize/` and re-run `/web-modernize:init` followed by `/analyze` and `/plan`. Notes under `.claude/modernize/notes/` are safe to copy back after re-init.

## [0.2.0] - 2026-05-11

### Added
- **`/web-modernize:rollback --unit <id>`** — soft inverse of `/migrate`. Reverts a single migrated, verified, or failed unit back to `pending` and restores its target files via git. Preserves design notes and history; populates new `rollback_info` field on the unit.
- **`/web-modernize:retry <unit-id> [--with-prompt="…"]`** — re-attempt a failed unit using the shared migration procedure. Optional `--with-prompt` lets the user steer the re-attempt with guidance the model layers on top of `migration.md`. Increments `retry_count` and preserves prior diagnostics in `failure.diagnostic_history[]`.
- **`/web-modernize:sync`** — pulls latest `state.json` from origin and merges it with the local copy using deterministic rules ("most-advanced unit status wins", "freshest heartbeat wins"). Replaces what would otherwise be a hand-resolved JSON merge conflict.
- **`/web-modernize:report [--format=md|json|html]`** — generates a stakeholder-friendly progress report (burndown, velocity, ETA, risk heat-map, ownership, blockers, acceptance-criteria status) at `.claude/modernize/reports/<date>-<format>`.
- **`agents/unit-migrator.md`** — shared per-unit migration procedure now used by `/next`, `/migrate`, and `/retry`. Consolidates the in-flight collision handling (Case A/B/C) and the translation body in one place, removing the previous "delegate by reference" drift risk between `/next` and `/migrate`.
- **`migration.md §9b Unit rename map`** (optional) — declare `old_id → new_id` mappings so re-running `/web-modernize:plan` carries unit history, notes, and verification forward across renames.
- **`state.schema.json` v2** — adds per-unit fields: `retry_count`, `last_retry_prompt`, `rollback_info`, `failure.diagnostic_history[]`. Required by the new failure-recovery commands.
- **`templates/report.md`** — Markdown template used by `/web-modernize:report`.

### Changed
- **`/web-modernize:init`** — when invoked on an existing `state.json` with `schema_version: 1`, performs an idempotent, lossless v1→v2 upgrade (adds the new per-unit fields). Closing nudge now points at `/analyze` first (auto-fills migration.md §2), then user edits §3–§11 on the populated source-stack section. This fixes the chicken-and-egg of "fill in source stack to run analyze that fills source stack".
- **`/web-modernize:plan`** — re-runnable without losing progress. Existing units are matched by id (with `§9b` rename map support); their `status`, `history`, `notes_path`, `verification`, `failure`, `retry_count`, `last_retry_prompt`, and `rollback_info` carry forward. Top-level `state.status` never rewinds on re-runs (e.g., a re-plan during `in_progress` stays `in_progress`). Existing scaffold blocks are preserved.
- **`/web-modernize:next`** — selection and closing message only; the translation body now lives in `agents/unit-migrator.md`.
- **`/web-modernize:migrate`** — same delegation as `/next`. Failed units now redirect to `/web-modernize:retry` (preserves diagnostic history); explicit override still allowed.

### Versioning
- `state.schema.json` `schema_version` bumped to `2`. `/init` migrates v1 → v2 on first run after upgrade. No team action required beyond running any plugin command.

## [0.1.1] - 2026-05-11

### Fixed
- `hooks/hooks.json` schema: wrap event matchers under a top-level `hooks` key so Claude Code's plugin loader accepts it. Previously installs failed with `Hook load failed: expected record, received undefined`.

## [0.1.0] - 2026-05-11

### Added
- Initial release.
- Plugin manifest and self-referencing marketplace.
- Ten skills: `init`, `analyze`, `plan`, `scaffold`, `auth`, `next`, `migrate`, `verify`, `status`, `abandon`.
- Team-facing `migration.md` template (11 sections).
- `plan.md` and per-unit notes templates.
- `state.schema.json` (schema_version 1) for the git-tracked progress ledger.
- `legacy-analyzer` subagent for source-stack detection.
- Optional `PostToolUse` heartbeat hook for stale-session detection.
- README with install instructions, five-step workflow, multi-developer notes, troubleshooting, and FAQ.
