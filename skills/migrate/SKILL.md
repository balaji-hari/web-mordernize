---
description: >
  Migrates a specifically named unit, bypassing /web-modernize:next's automatic
  selection. The escape hatch for senior developers who want to jump to a
  specific page/controller/component (e.g., to debug a problem unit out of
  dependency order). Otherwise behaves identically to /web-modernize:next.
  For retrying a previously failed unit, prefer /web-modernize:retry.
disable-model-invocation: false
---

# `/web-modernize:migrate <unit-id>`

You are the **migrate** skill. You take an explicit unit id as `$ARGUMENTS` and migrate it, overriding the dependency-aware picking that `/web-modernize:next` does.

The translation work itself is shared with `/web-modernize:next` and `/web-modernize:retry` and lives in `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md`. This skill handles **explicit selection** and **status-specific gating**; the migration body is delegated.

## Preflight

1. Parse `$ARGUMENTS` as the unit id. If empty, print:
   ```
   Usage: /web-modernize:migrate <unit-id>

   Example: /web-modernize:migrate LoginController
   To see available units: /web-modernize:status
   ```
   and stop.

2. Read `state.json`. Require `status` ∈ {`auth_done`, `in_progress`}. Otherwise redirect.

3. Find the unit: `unit = state.units.find(u => u.id == $ARGUMENTS)`.
   - If not found, print: "No unit named `<id>` in the plan. Run `/web-modernize:status` to list units." and stop.

## Dependency check (warn, don't block)

Inspect `unit.depends_on`. If any dependency is not in `{"migrated", "verified"}`:

```
WARNING: Unit <id> has unmet dependencies: <list of dep_ids and their statuses>.

Migrating out of order risks broken references (the unit may import symbols
from a not-yet-migrated dependency). Continue anyway? (yes/no)
```

If the user says yes, the shared procedure will stub the missing deps with TODO comments. If no, stop.

## Status-based gating

Decide whether to invoke the shared agent based on `unit.status`:

| Current status | Action |
|----------------|--------|
| `pending` | Proceed straight to the shared agent. |
| `in_progress` | Proceed; the shared agent's Case A/B/C handling will sort out the collision. |
| `migrated` | Ask: "Already migrated. (a) reset to pending and re-migrate, (b) view current state and skip, (c) cancel?" On (a), set unit back to `pending` (append history `{from: migrated, to: pending, reason: "manual re-migrate"}`) then proceed. On (b)/(c), stop. |
| `verified` | Same as migrated, but extra warning: "Re-migrating will reset verification status." Clear `verification` if user confirms. |
| `failed` | Print the prior diagnostic and redirect: "Use `/web-modernize:retry <id>` to re-attempt — it preserves the diagnostic history and supports `--with-prompt` for guidance overrides." Stop unless the user explicitly forces with a confirmation. |
| `blocked` / `skipped` | Ask the user to confirm they want to take this unit out of that state. On confirm, set to `pending` and proceed. |

## Run the shared migration procedure

Load `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator.md` and follow it with:

- `mode = "migrate"`
- `unit = <the unit named by the user>`
- `retry_prompt = null`

If `depends_on` were unmet and the user confirmed override, pass a flag to the agent so it stubs missing dep imports rather than failing.

## Closing message

On success:

```
✓ Migrated <unit.id> (out of dependency order: <yes|no>)
  Source: <source_paths>
  Target: <target_paths>
  Notes:  .claude/modernize/notes/<unit.id>.md

Suggested next steps:
  1. Review the diff: git diff --stat
  2. Run /web-modernize:verify <unit.id>
  3. Commit when satisfied.
```

On failure: the agent already printed the diagnostic and the recovery options (including `/web-modernize:retry`). Do not add a second banner.

## State transitions

- Top-level: `auth_done` → `in_progress` (if first migration), unchanged otherwise.
- Unit: `pending` (or whatever the user opted out of) → `in_progress` → `migrated` (or `failed`).
