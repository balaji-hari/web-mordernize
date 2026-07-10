---
description: "Pick the next pending unit (respecting depends_on) and migrate it. Workhorse of the iteration loop. Use when state.status is 'foundation_done' or 'in_progress'. Triggers: 'what's next', 'continue', 'keep going', 'migrate the next one', 'next page', 'next unit', 'next iteration'."
disable-model-invocation: false
---

# `/web-modernize:next [--plan | --no-plan]`

You are the **next** skill. You select and migrate one unit per invocation. Across many invocations (possibly by different developers across many days), the team migrates the whole codebase.

The actual per-unit translation work is shared with `/web-modernize:migrate` and `/web-modernize:retry`. To avoid drift, this skill does **selection** and **closing message**; the migration body lives in `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator-caller.md` (collision handling, acquisition, the plan gate, open-decisions), which you run yourself, inline, right now; it launches `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator-subagent.md` as a real subagent via the `Agent` tool (`subagent_type: unit-migrator`), once or twice per unit depending on the plan gate. See those files for the full procedure — don't duplicate it here.

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

0. Parse `$ARGUMENTS` for an optional plan-gate override (default: none):
   - `--plan` → `plan_override = "on"` (force the per-unit plan gate for this unit, even when `review_mode` is `auto`).
   - `--no-plan` → `plan_override = "off"` (skip the gate for this unit, even when `review_mode` is `plan-first`).
   - neither → `plan_override = null` (use the migration-wide `state.review_mode` default).
1. Read `.claude/modernize/state.json`. Require `status` to be one of `foundation_done`, `in_progress`, or `complete`.
   - If earlier, redirect: "Run /web-modernize:<missing-skill> first."
   - If `complete`, tell user the migration is done; suggest `/web-modernize:status` for the recap.
2. Read `migration.md` (for target stack + constraints) and `.claude/modernize/plan.md` (for context).

## Resume an in-flight unit (if any)

Iterate `state.unit_ids[]` and read each `.claude/modernize/units/<id>.json`. Find any unit with `status: "in_progress"`. If one exists, **do not run unit selection** — go straight to "Run the shared migration procedure" below with:

- `mode = "next"`
- `unit = <the in-flight unit object you just read>`
- `retry_prompt = null`
- `force_deps = false`
- `plan_override = <the value parsed in Preflight step 0>`

`agents/unit-migrator-caller.md`'s §A1 handles Cases A/B/C (resume own work, warn about another developer, reclaim stale) before anything is launched. After §A7 finishes, jump to "Closing message" below.

## Select next unit

Iterate `state.unit_ids[]` in order, reading each `units/<id>.json`. A unit is a candidate if:

- `unit.status == "pending"`, AND
- every id in `unit.depends_on[]` either:
  - is `__auth__` and the synthetic auth unit's per-unit file shows status `migrated`/`verified` (or top-level `state.status >= "foundation_done"` as a fast-path check), OR
  - corresponds to another unit with status `migrated` or `verified`.

If no candidate has all dependencies satisfied:
- If any unit is still `pending` or `in_progress` but blocked: print blocked-chain analysis showing for each blocked unit which dep id is missing and that dep's current status.
- If every unit is `migrated`, `verified`, or `skipped`: set top-level `state.status = "complete"`, save `state.json`, and print congratulations.

Pick the **first** candidate in `unit_ids` order (which already reflects `phase asc, list_index asc` from `/plan`).

## Run the shared migration procedure

Follow `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator-caller.md`, inline, starting at §A1, with:

- `mode = "next"`
- `unit = <the candidate you just picked>`
- `retry_prompt = null`
- `force_deps = false`
- `plan_override = <the value parsed in Preflight step 0>`

It handles unit acquisition (§A2), the optional plan gate (§A3/§A6 — launching `agents/unit-migrator-subagent.md` as a subagent via the `Agent` tool, once if not gated, twice if gated with a human approval step in between), open-decisions resolution (§A4), and finalizing the unit record (§A7). When §A7 finishes, the unit is `migrated`, `failed`, or — if you cancelled at the plan gate — back to `pending`.

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

On cancel at the plan gate (`unit.status == "pending"`, no files written):

```
○ <unit.id> not migrated — cancelled at the plan gate. The unit is back to `pending`; no files were written.
  Re-run /web-modernize:next when ready (add --no-plan to skip the gate for it).
```

## State transitions

- Pre: `state.status` ∈ {`foundation_done`, `in_progress`}
- Post: top-level `state.status` = `in_progress` (or `complete` if this was the last unit)
- Per-unit file: `pending` → `in_progress` → `migrated` (or `failed`)
