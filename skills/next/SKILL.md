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

## Preflight

1. Read `state.json`. Require `status` to be one of `auth_done`, `in_progress`, or `complete`.
   - If earlier, redirect: "Run /web-modernize:<missing-skill> first."
   - If `complete`, tell user the migration is done; suggest `/web-modernize:status` for the recap.
2. Read `migration.md` (for target stack + constraints) and `.claude/modernize/plan.md` (for context).

## Resume an in-flight unit (if any)

Scan `state.json.units[]` for any unit with `status: "in_progress"`. If one exists, **do not run unit selection** — load `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md` and follow it with:

- `mode = "next"`
- `unit = <the in-flight unit>`
- `retry_prompt = null`

The agent procedure handles Cases A/B/C (resume own work, warn about another developer, reclaim stale). After the agent returns, jump to "Closing message" below.

## Select next unit

Filter `state.json.units[]` to candidates:

- `status == "pending"`
- All `depends_on` ids exist and have `status` in `{"migrated", "verified"}` (the synthetic `__auth__` is satisfied once `state.status == "auth_done"`).

If candidates is empty:
- If any units are still `in_progress` or `pending` but blocked: print blocked-chain analysis (which dep is missing for each).
- If all units are `migrated` or `verified` or `skipped`: set `state.status = "complete"` and print congratulations.

Sort candidates by `(phase asc, list_index asc)`. Pick the first.

## Run the shared migration procedure

Load `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md` and follow it with:

- `mode = "next"`
- `unit = <the candidate you just picked>`
- `retry_prompt = null`

The agent handles unit acquisition (status + in_flight write), the translation body, stop conditions, and finalization. When it returns, the unit is either `migrated` or `failed`.

## Closing message

On success (`unit.status == "migrated"`):

```
✓ Migrated <unit.id>
  Source: <source_paths>
  Target: <target_paths>
  Notes:  .claude/modernize/notes/<unit.id>.md

Suggested next steps:
  1. Review the diff: git diff --stat
  2. Run /web-modernize:verify  (lint/typecheck/tests for this unit)
  3. Commit when satisfied.
  4. Then /web-modernize:next  (or stop here)
```

On failure (`unit.status == "failed"`): the agent already printed the diagnostic and the recovery options. Do not add a second banner — just return.

## State transitions

- Pre: `state.status` ∈ {`auth_done`, `in_progress`}
- Post: `state.status` = `in_progress` (or `complete` if this was the last unit)
- Unit: `pending` → `in_progress` → `migrated` (or `failed`)
