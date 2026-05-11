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

## Preflight

1. Read `state.json`. Require `status` to be one of `auth_done`, `in_progress`, or `complete`.
   - If earlier, redirect: "Run /web-modernize:<missing-skill> first."
   - If `complete`, tell user the migration is done; suggest `/web-modernize:status` for the recap.
2. Read `migration.md` (for target stack + constraints) and `.claude/modernize/plan.md` (for context).

## Handle in-flight units

Scan `state.json.units[]` for any unit with `status: "in_progress"`. There are three sub-cases:

### Case A: in-flight unit, current user is the holder

`in_flight.by == <current user identity>` AND `last_heartbeat` is fresh (< 15 min).

Continue migrating it. Print:

```
Resuming <unit.id> — you started it <N> min ago at step "<in_flight.current_step>".
Files touched so far: <count> (<list first 3>).
```

Then re-read those files and the source files, identify what's left, and continue the migration. Skip the "select next unit" step below.

### Case B: in-flight unit, different user (or different host), fresh heartbeat

Print:

```
⚠ <in_flight.by> on <in_flight.host> is currently migrating <unit.id>.
  Heartbeat last bumped <N> min ago — they may be actively working.

  Options:
    [w] Wait and check status later
    [o] Override (take over). They may lose work if they push first.
    [d] Pick a different unit instead (one whose dependencies don't conflict).
```

Default to `w` if user is unclear. If `o`, proceed; if `d`, skip this unit and find the next eligible one whose `depends_on` doesn't include the in-flight unit.

### Case C: in-flight unit, stale heartbeat (>15 min) OR no heartbeat block

This unit was abandoned mid-flight. Print:

```
A previously in-flight unit <unit.id> appears stalled (last heartbeat <N> min ago, started by <in_flight.by>).

  [r] Reclaim and resume — read its in-flight state and continue.
  [s] Skip — leave as in_progress, pick another.
  [a] Abort — reset to pending so it can be picked from scratch by /web-modernize:next.
```

If `r`, treat as Case A (current user becomes holder). If `a`, update history with a "reset by stalled-recovery" entry.

## Select next unit (only if not resuming)

Filter `state.json.units[]` to candidates:
- `status == "pending"`
- All `depends_on` ids exist and have `status` in `{"migrated", "verified"}`

If candidates is empty:
- If any units are still `in_progress` or `pending` but blocked: print blocked-chain analysis (which dep is missing for each).
- If all units are `migrated` or `verified` or `skipped`: set `state.status = "complete"` and print congratulations.

Sort candidates by `(phase asc, list_index asc)`. Pick the first.

## Acquire the unit

Update the unit in `state.json`:

```json
{
  "status": "in_progress",
  "history": [...existing, {
    "at": "<now>", "by": "<user>", "from": "pending", "to": "in_progress", "session_id": "<sid>"
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

Also set top-level `state.status = "in_progress"` if not already.

Save state.json immediately so any concurrent `/web-modernize:status` sees the new in-flight.

## Migrate

This is the main work. The exact steps depend on `unit.kind` and the source/target stacks.

### General algorithm

1. **Read all `source_paths`** in full.
2. **Read related target context**: existing target_paths for migrated dependencies, the target framework's conventions, any existing shared utilities under `apps/web-new/src/lib/` etc.
3. **Update `in_flight.current_step` = "designing target structure"** and write to state.json.
4. **Decide target file layout**:
   - React/Vue/Svelte component: place under `apps/web-new/src/features/<feature>/` or `apps/web-new/src/pages/` per framework convention.
   - API endpoint: `apps/api-new/src/routes/<area>/<verb>.ts` or framework equivalent.
   - Shared utility: `apps/web-new/src/lib/`.
5. **Create a feature branch** (recommended): `git checkout -b modernize/<unit.id>` — but only if the team's git is in a clean state and this command works locally. If git is dirty or the team uses a different branching strategy (signaled by §8 constraints), skip the branch and migrate on the current branch.
6. **Write target files**. Update `in_flight.files_touched_so_far` and `current_step` as you go. The heartbeat hook will keep `last_heartbeat` fresh automatically.
7. **Translate semantics, not syntax**:
   - WebForms event handlers → React event handlers + useState/useReducer.
   - Server-side controls (`<asp:GridView>`) → modern data table component (`<DataGrid>`, table + map).
   - ViewState → component state or query string, depending on intent.
   - Server-side validators → client + server validation (modern API checks).
   - JSP scriptlets → typed view models + template logic.
   - AngularJS controllers → modern composables / hooks.
8. **Add a placeholder test** for the unit (smoke test at minimum). Pass acceptance criteria from `migration.md §10` should drive what's tested.
9. **Append to `notes/<unit.id>.md`**: design decisions, source-code map (legacy symbol → target symbol), gotchas.

### Stop conditions

You **must stop** and set unit status to `failed` if:
- A required source file is missing or unreadable.
- The target framework cannot represent something critical (e.g., a custom WebForms control with no obvious equivalent — flag for human design review).
- A test that should pass is failing in a way that suggests the migration is incorrect (not just a missing fixture).

On stop:

```json
{
  "status": "failed",
  "in_flight": null,
  "failure": { "diagnostic": "<one paragraph>", "branch": "modernize/<unit.id>" }
}
```

Append history entry. Print the diagnostic to the user. Do not auto-advance.

## Finalize successful migration

Update unit:

```json
{
  "status": "migrated",
  "target_paths": [<actual paths written>],
  "in_flight": null,
  "history": [...existing, { "at": "<now>", "by": "<user>", "from": "in_progress", "to": "migrated", "session_id": "<sid>" }]
}
```

Update `state.json.updated_at`.

## After writing

Print:

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

## State transitions

- Pre: `state.status` ∈ {`auth_done`, `in_progress`}
- Post: `state.status` = `in_progress` (or `complete` if this was the last unit)
- Unit: `pending` → `in_progress` → `migrated` (or `failed`)
