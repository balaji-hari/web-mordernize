---
description: >
  Migrates a specifically named unit, bypassing /web-modernize:next's automatic
  selection. The escape hatch for senior developers who want to jump to a
  specific page/controller/component (e.g., to debug a problem unit out of
  dependency order, or to retry a previously failed unit). Otherwise behaves
  identically to /web-modernize:next.
disable-model-invocation: false
---

# `/web-modernize:migrate <unit-id>`

You are the **migrate** skill. You take an explicit unit id as `$ARGUMENTS` and migrate it, overriding the dependency-aware picking that `/web-modernize:next` does.

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
⚠ Unit <id> has unmet dependencies: <list of dep_ids and their statuses>.

Migrating out of order risks broken references (the unit may import symbols
from a not-yet-migrated dependency). Continue anyway? (yes/no)
```

If the user says yes, proceed but record this in `notes/<id>.md` "Gotchas" so reviewers know.

## Status-based handling

- If `unit.status == "pending"` → migrate normally (delegate the rest to the logic in `/web-modernize:next`'s "Migrate" section).
- If `unit.status == "in_progress"` → behave like `/web-modernize:next`'s in-flight handling (A/B/C cases).
- If `unit.status == "migrated"` → ask the user: "This unit has already been migrated. Do you want to (a) reset to pending and re-migrate from scratch, (b) view its current state and skip, (c) cancel?"
- If `unit.status == "verified"` → same as migrated, with extra warning: "Re-migrating will reset verification status."
- If `unit.status == "failed"` → print the previous failure diagnostic and ask: "Retry this unit? Address the underlying issue first if needed."
- If `unit.status == "blocked"` or `"skipped"` → ask the user to confirm they want to take this unit out of that state.

## Migration body

Once past the preflight and status handling, delegate to the same algorithm documented in `${CLAUDE_PLUGIN_ROOT}/skills/next/SKILL.md` under "Migrate". The only difference between `/next` and `/migrate` is **which unit is selected**; the actual porting work is identical.

To avoid drift, do not duplicate that algorithm here. Instead, follow it by reference: read `next/SKILL.md`'s "Migrate" section and apply it to the unit selected above.

## State transitions

Same as `/web-modernize:next`:
- Top-level: `auth_done` → `in_progress` (if first migration), unchanged otherwise.
- Unit: `pending`/`failed`/etc. → `in_progress` → `migrated` (or `failed`).
