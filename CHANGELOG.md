# Changelog

All notable changes to the `web-modernize` plugin are documented here. Versioning follows [Semantic Versioning](https://semver.org/).

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
