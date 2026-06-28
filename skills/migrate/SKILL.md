---
description: "Migrate a specifically named unit, bypassing automatic selection. Optional --force skips dependency checks. Use when state.status is 'foundation_done' or 'in_progress' AND the user names a unit. Triggers: 'migrate <unit>', 'do the login page', 'translate <component>', 'migrate the OrderController', 'work on <name>'."
disable-model-invocation: false
---

# `/web-modernize:migrate <unit-id> [--force] [--plan | --no-plan]`

You are the **migrate** skill. You take an explicit unit id as `$ARGUMENTS` and migrate it, overriding the dependency-aware picking that `/web-modernize:next` does.

The translation work itself is shared with `/web-modernize:next` and `/web-modernize:retry` and lives in `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md`. This skill handles **explicit selection**, **dependency gating**, and **status-specific gating**; the migration body is delegated.

## Preflight

1. Parse `$ARGUMENTS`:
   - First token is `<unit-id>` (required).
   - Optional flag `--force` — override the dependency block.
   - Optional plan-gate override (default: none): `--plan` → `plan_override = "on"` (force the per-unit plan gate even when `review_mode` is `auto`); `--no-plan` → `plan_override = "off"` (skip the gate even when `review_mode` is `plan-first`); neither → `plan_override = null` (use the migration-wide `state.review_mode` default).
   - If `<unit-id>` is missing, print usage and stop:
     ```
     Usage: /web-modernize:migrate <unit-id> [--force] [--plan | --no-plan]

     Examples:
       /web-modernize:migrate LoginController
       /web-modernize:migrate PaymentProcessor --force   (allow unmet deps; stubs them)
       /web-modernize:migrate Dashboard --no-plan        (skip the plan-approval gate)

     To see available units: /web-modernize:status
     ```

2. Read `.claude/modernize/state.json`. Require `status ∈ {foundation_done, in_progress}`. Otherwise redirect to the missing skill.

3. Read `.claude/modernize/units/<unit-id>.json`. If the file does not exist:
   ```
   ✗ No unit named `<id>` in the plan. Available units:
     <ls .claude/modernize/units/*.json, stripped of path and .json>
   ```
   Stop.

## Dependency check (block by default, --force overrides)

Inspect `unit.depends_on`. For each dependency, determine its current status:

- `__auth__` — satisfied if top-level `state.status >= "foundation_done"`.
- Other ids — read `units/<dep-id>.json` and check its `status`. Satisfied if `status ∈ {migrated, verified}`.

If any dependency is **not** satisfied, build a list of `(dep_id, dep_status)` pairs.

### Default (no `--force`) — refuse

Print and stop:

```
✗ Unit <id> has unmet dependencies:

  - <dep_id_1>: <status>
  - <dep_id_2>: <status>
  ...

Migrate the dependencies first (via /web-modernize:next or by name), then re-run.

To override and migrate out of order anyway, re-run with --force:
  /web-modernize:migrate <id> --force

Forcing will leave `// TODO: provided by <dep.id>` stubs in the target code for
every missing dep symbol. The override is recorded in
.claude/modernize/notes/<id>.md so reviewers see it.
```

Make no mutations.

### With `--force` — warn but proceed

Print:

```
WARNING: Migrating <id> out of dependency order. The following deps are unmet:

  - <dep_id_1>: <status>
  - <dep_id_2>: <status>

Missing symbols will be stubbed with `// TODO: provided by <dep.id>` comments.
This override will be recorded in .claude/modernize/notes/<id>.md "Gotchas".

Proceeding in 3 seconds... (Ctrl+C to cancel)
```

Then proceed.

## Status-based gating

Decide whether to invoke the shared agent based on `unit.status`:

| Current status | Action |
|----------------|--------|
| `pending` | Proceed straight to the shared agent. |
| `in_progress` | Proceed; the shared agent's Case A/B/C handling will sort out the collision. |
| `migrated` | Ask: "Already migrated. (a) reset to pending and re-migrate, (b) view current state and skip, (c) cancel?" On (a), set unit back to `pending` in `units/<id>.json` (append history `{from: migrated, to: pending, reason: "manual re-migrate"}`) then proceed. On (b)/(c), stop. |
| `verified` | Same as migrated, but extra warning: "Re-migrating will reset verification status." Clear `verification` if user confirms. |
| `failed` | Print the prior diagnostic and redirect: "Use `/web-modernize:retry <id>` to re-attempt — it preserves the diagnostic history and supports `--with-prompt` for guidance overrides." Stop unless the user explicitly forces with a confirmation. |
| `blocked` / `skipped` | Ask the user to confirm they want to take this unit out of that state. On confirm, set to `pending` in the per-unit file and proceed. |

## Run the shared migration procedure

Load `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md` and follow it with:

- `mode = "migrate"`
- `unit = <the unit object you just read from units/<id>.json>`
- `retry_prompt = null`
- `force_deps = <true if --force was passed, else false>`
- `plan_override = <the value parsed in Preflight step 1>`

The agent reads and writes only `units/<unit.id>.json` for unit-level state and `state.json` only for the top-level `foundation_done → in_progress` transition. With the plan gate active, the agent presents a plan (§3.5) and waits for approval before writing; cancelling there returns the unit to `pending` with nothing written.

## Closing message

On success:

```
✓ Migrated <unit.id> (out of dependency order: <yes|no>)
  Source: <source_paths>
  Target: <target_paths>
  Notes:  .claude/modernize/notes/<unit.id>.md
  Unit file: .claude/modernize/units/<unit.id>.json

Suggested next steps:
  1. Review the diff: git diff --stat
  2. Run /web-modernize:verify <unit.id>
  3. Commit when satisfied.
```

On failure: the agent already printed the diagnostic and the recovery options (including `/web-modernize:retry`). Do not add a second banner.

On cancel at the plan gate (`unit.status == "pending"`, no files written):

```
○ <unit.id> not migrated — cancelled at the plan gate. The unit is back to `pending`; no files were written.
  Re-run /web-modernize:migrate <unit.id> when ready (add --no-plan to skip the gate).
```

## State transitions

- Top-level: `foundation_done` → `in_progress` (if first migration), unchanged otherwise.
- Per-unit file: `pending` (or whatever the user opted out of) → `in_progress` → `migrated` (or `failed`).
