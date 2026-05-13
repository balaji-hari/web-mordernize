---
description: >
  Picks the next pending unit from the migration plan (respecting depends_on)
  and migrates it. The main workhorse of the iterative migration loop. Handles
  in-flight collision detection: if another developer has a unit in flight,
  surfaces it and offers to take over. Each invocation moves exactly one unit
  from pending → in_progress → migrated. Run repeatedly until all units done.
disable-model-invocation: false
---

# `/web-modernize:next`

You are the **next** skill. You select and migrate one unit per invocation. Across many invocations (possibly by different developers across many days), the team migrates the whole codebase.

The actual per-unit translation work is shared with `/web-modernize:migrate` and `/web-modernize:retry`. To avoid drift, this skill does **selection** and **closing message**; the migration body lives in `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md`.

## Plugin-version skew check

Read `state.json.plugin_version` (treat absent/null as "old/unknown"). Read the running plugin's version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. Parse both as `MAJOR.MINOR.PATCH`. If `state.plugin_version`'s major **or** minor differs from the running version (patch differences are fine), print **before** anything else and **continue** (warn, do not refuse):

```
⚠ Plugin version skew detected.
   State written by: <state.plugin_version or "unknown">
   Running version:  <running.version>
   Teammates on different plugin versions writing to the same state can
   produce shape mismatches. Recommended: have everyone run
   /plugin uninstall web-modernize && /plugin install web-modernize, then continue.
```

Refusing would block the team until the slowest updater catches up — that's a worse failure mode than a warned-but-continued run. On successful exit (right before the "✓ done" message), set `state.plugin_version = "<running version>"` so the warning self-resolves after one synchronized run.

## Preflight

1. Read `.claude/modernize/state.json`. Require `status` to be one of `auth_done`, `in_progress`, or `complete`.
   - If earlier, redirect: "Run /web-modernize:<missing-skill> first."
   - If `complete`, tell user the migration is done; suggest `/web-modernize:status` for the recap.
2. Read `migration.md` (for target stack + constraints) and `.claude/modernize/plan.md` (for context).

## Resume an in-flight unit (if any)

Iterate `state.unit_ids[]` and read each `.claude/modernize/units/<id>.json`. Find any unit with `status: "in_progress"`. If one exists, **do not run unit selection** — load `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md` and follow it with:

- `mode = "next"`
- `unit = <the in-flight unit object you just read>`
- `retry_prompt = null`
- `force_deps = false`

The agent procedure handles Cases A/B/C (resume own work, warn about another developer, reclaim stale). After the agent returns, jump to "Closing message" below.

## Select next unit

Iterate `state.unit_ids[]` in order, reading each `units/<id>.json`. A unit is a candidate if:

- `unit.status == "pending"`, AND
- every id in `unit.depends_on[]` either:
  - is `__auth__` and the synthetic auth unit's per-unit file shows status `migrated`/`verified` (or top-level `state.status >= "auth_done"` as a fast-path check), OR
  - corresponds to another unit with status `migrated` or `verified`.

If no candidate has all dependencies satisfied:
- If any unit is still `pending` or `in_progress` but blocked: print blocked-chain analysis showing for each blocked unit which dep id is missing and that dep's current status.
- If every unit is `migrated`, `verified`, or `skipped`: set top-level `state.status = "complete"`, save `state.json`, and print congratulations.

Pick the **first** candidate in `unit_ids` order (which already reflects `phase asc, list_index asc` from `/plan`).

## Run the shared migration procedure

Load `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md` and follow it with:

- `mode = "next"`
- `unit = <the candidate you just picked>`
- `retry_prompt = null`
- `force_deps = false`

The agent handles unit acquisition (status + in_flight write to `units/<id>.json`), the translation body, stop conditions, and finalization. When it returns, the unit is either `migrated` or `failed`.

## Closing message

On success (`unit.status == "migrated"`):

```
✓ Migrated <unit.id>
  Source: <source_paths>
  Target: <target_paths>
  Notes:  .claude/modernize/notes/<unit.id>.md
  Unit file: .claude/modernize/units/<unit.id>.json

Suggested next steps:
  1. Review the diff: git diff --stat
  2. Run /web-modernize:verify  (lint/typecheck/tests for this unit)
  3. Commit when satisfied.
  4. Then /web-modernize:next  (or stop here)
```

On failure (`unit.status == "failed"`): the agent already printed the diagnostic and the recovery options. Do not add a second banner — just return.

## State transitions

- Pre: `state.status` ∈ {`auth_done`, `in_progress`}
- Post: top-level `state.status` = `in_progress` (or `complete` if this was the last unit)
- Per-unit file: `pending` → `in_progress` → `migrated` (or `failed`)
