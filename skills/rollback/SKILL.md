---
description: "Revert one unit's target files and reset it to 'pending'. Soft inverse of /migrate. Use to undo a single unit. Triggers: 'rollback <unit>', 'undo this unit', 'revert the migration of <unit>', 'unroll <unit>', 'reset this unit'."
disable-model-invocation: false
---

# `/web-modernize:rollback --unit <unit-id> [--force-shared]`

You are the **rollback** skill. You undo a single unit's migration so the team can re-attempt it cleanly. You do NOT delete the design notes (`notes/<unit-id>.md`) — those are useful as a record of the previous attempt.

Because the migration model isn't truly per-unit-isolated — the first unit writes the shared layout + global CSS, units extract shared utilities, and `kind: shared` / `cross-cutting` units are depended on by many — a naive rollback can revert a shared file out from under every dependent. This skill runs a **shared-file safety check** and refuses by default when a rollback would break live dependents (override with `--force-shared`).

## Preflight

1. Parse `$ARGUMENTS`. Expect `--unit <unit-id>`. Optional `--force-shared` — proceed even when the shared-file safety check (below) finds shared files with live dependents. If `--unit` is missing or no id follows, print:
   ```
   Usage: /web-modernize:rollback --unit <unit-id> [--force-shared]

   Example: /web-modernize:rollback --unit LoginController

   This reverts the unit's target files via git and resets its status to "pending".
   Refuses by default if the unit owns shared files other units rely on; re-run
   with --force-shared to override (you'll see the blast radius first).
   For re-attempting after rollback, follow up with /web-modernize:migrate <unit-id>
   or /web-modernize:retry <unit-id> --with-prompt="<guidance>".
   ```
   and stop.

2. Read `.claude/modernize/state.json`. Require `status >= "in_progress"`. If earlier, redirect: "Nothing to rollback — no units have been migrated yet."

3. Read `.claude/modernize/units/<unit-id>.json`. If the file does not exist, list valid ids (`ls .claude/modernize/units/*.json`) and stop.

4. Check `unit.status`:
   - `migrated`, `verified`, or `failed` → proceed.
   - `pending` → "Unit is already pending; nothing to rollback."
   - `in_progress` → "Unit is currently in-flight. Either wait for it to finish, or use /web-modernize:abandon --unit to abort it first."
   - `blocked` / `skipped` → "Unit is `<status>`; use /web-modernize:abandon --unit to clear the marker, or edit units/<id>.json manually if you want to roll back a previously-completed migration that was later marked skipped."

## Discover what to revert

Inspect:

1. **Feature branch** — if `unit.failure.branch` or the conventional name `modernize/<unit.id>` exists locally:
   ```sh
   git branch --list modernize/<unit.id>
   ```
   Note whether it exists and whether it has commits beyond the merge-base with the current branch.

2. **Target paths** — `unit.target_paths[]` (and `unit.in_flight.files_touched_so_far[]` if `in_flight` is still populated — possible if the unit is `failed`). For each path:
   - Does it exist on disk?
   - Is it tracked in git? (`git ls-files --error-unmatch <path>`)
   - Was it tracked **before** the migration started? Compare against `state.repo.root_commit` if recorded — `git cat-file -e <root_commit>:<path>` returns 0 if the path existed at root.

3. **Commits on current branch** — find any commits whose message mentions the unit id since `state.created_at` (`git log --grep=<unit.id> --since=<state.created_at>`). These may already be merged.

## Plan the revert

Categorize each target path into one of:

| Category | Action |
|----------|--------|
| New file, uncommitted | Delete the file. |
| New file, committed to local feature branch only | Will be discarded with the branch. |
| New file, committed to current branch | Run `git rm <path>` and stage the deletion (do not auto-commit). |
| Pre-existing file, modified | `git checkout HEAD~<n> -- <path>` to the pre-migration revision (find n via the unit.history first→in_progress timestamp). If ambiguous, `git checkout <root_commit> -- <path>` is the safe fallback. |
| Pre-existing file, deleted by migration | Restore via the same `git checkout <root_commit> -- <path>`. |

## Shared-file safety check

Before confirming, decide whether the revert plan would touch **shared** files that other units rely on. Classification is **data-driven — never path-pattern or filename matching** (no assuming `src/lib/` or a layout named `App.tsx`). Read all `units/*.json` once. A path in the revert plan is **shared** if ANY of:

1. It is a `target_paths[]` entry of a unit whose `kind` is `shared`, `cross-cutting`, or whose id is synthetic (`__…__`). The **first-unit layout + global CSS** are identified via the `notes/__layout__.md` record of what the migrator actually wrote (and/or a `__layout__` unit's `target_paths`) — not by guessing filenames.
2. It appears in any unit's `extracted_shared[].path` (emergent shared code promoted by `/plan`).
3. It appears in **more than one** unit's `target_paths[]`.
4. The unit being rolled back is itself `kind: shared` / `kind: cross-cutting` / a synthetic `__…__` id (then all of its target paths are treated as shared).

For each shared path, compute its **live dependents** — units with status `migrated` / `verified` / `in_progress` that:
- list this unit's id (or the shared unit owning that path) in their `depends_on[]`, OR
- reference the path in their own `target_paths` / `extracted_shared`, OR
- for the layout / global-CSS case (per the `__layout__` record): **all other migrated/verified feature units** (they all render inside the layout).

**If ownership is ambiguous** (a path looks reused but you can't confidently attribute it), ask the developer rather than silently treating it as owned.

**Decision:**
- **No shared path with live dependents** → continue to "Confirm with the user" unchanged.
- **Shared path(s) with live dependents AND `--force-shared` NOT passed** → **refuse**. Make no mutations. Print the blast radius and the escape:
  ```
  ✗ Refusing to roll back <unit.id> — it owns shared files that other units rely on:

    <shared-path-1>   ← depended on by: <depA>, <depB>, …
    <shared-path-2>   ← depended on by: <all feature units render inside this layout>

  Rolling these back would break those units. Safer options:
    - Roll back the dependents first, then this unit.
    - Or edit the shared file directly instead of rolling the whole unit back.
    - Or, if you accept the breakage, re-run with --force-shared:
        /web-modernize:rollback --unit <unit.id> --force-shared
  ```
- **Shared path(s) with live dependents AND `--force-shared` passed** → proceed, but carry the shared paths + impacted dependents into the confirmation summary and the `rollback_info.shared_impact` write.

## Confirm with the user

Print the plan **before** doing anything:

```
Rollback plan for unit <unit.id> (status: <current status>):

Files to revert:
  - <path1>  (new, uncommitted)       → delete
  - <path2>  (new, on current branch) → git rm (you'll commit the deletion)
  - <path3>  (pre-existing, modified) → restore to <root_commit>

Feature branch:
  - modernize/<unit.id>  (exists, 4 commits ahead) → will be deleted locally
    (Pushed to origin? Run `git push origin --delete modernize/<unit.id>` yourself.)

Per-unit file changes (.claude/modernize/units/<unit.id>.json):
  - status: <current> → pending
  - target_paths: cleared
  - verification: cleared
  - rollback_info: populated

Proceed? (yes/no)
```

When `--force-shared` was used to override the safety check, add a prominent block above `Proceed?`:

```
  ⚠ SHARED FILE — forcing this rollback will break:
    <shared-path>  →  <depA>, <depB>, … (these units depend on it)
  Consider rolling those back or re-migrating them afterward.
```

Wait for explicit `yes`. Anything else → stop with no changes.

## Execute the revert

In this order:

1. **Files**: for each target path, run the categorized action. Capture stdout/stderr. If any action fails (e.g., `git checkout` complains about a dirty working tree), stop and print the error verbatim. Do not partially complete.

2. **Branch**: if a `modernize/<unit.id>` branch exists locally and is not the current branch, run `git branch -D modernize/<unit.id>`. If it IS the current branch, refuse to delete and tell the user to `git checkout <main-branch>` first, then re-run rollback. Do NOT touch the remote.

3. **Per-unit file mutations** — write to `.claude/modernize/units/<unit.id>.json`:

   ```json
   {
     "status": "pending",
     "target_paths": [],
     "verification": <omitted>,
     "in_flight": null,
     "rollback_info": {
       "at": "<now>",
       "by": "<git user.email or 'unknown'>",
       "branch": "modernize/<unit.id>",
       "restored_paths": [<every path you reverted>],
       "reason": "manual /web-modernize:rollback",
       "shared_impact": <omit unless --force-shared was used; then {
         "forced": true,
         "shared_paths": [<the shared paths reverted>],
         "impacted_dependents": [<unit ids that depend on them>]
       }>
     },
     "history": [...existing, {
       "at": "<now>",
       "by": "<user>",
       "from": "<previous status>",
       "to": "pending",
       "session_id": "<sid>"
     }]
   }
   ```

   Do NOT clear `unit.history` or `unit.notes_path` — they are the audit trail for the next attempt. Do NOT clear `unit.failure.diagnostic_history` either — the next `/retry` will append to it.

4. Bump `state.json.updated_at` (only the timestamp; do not touch top-level `status` or any other field). Save `state.json`.

## After writing

Print:

```
✓ Rolled back <unit.id>.

Files reverted: <count>
Feature branch deleted: <yes|no — branch name>
Unit status: <previous> → pending
Unit file: .claude/modernize/units/<unit.id>.json

The unit's design notes are preserved at .claude/modernize/notes/<unit.id>.md
(append a "Rollback #<retry_count + 1>" section before retrying so the
next attempt can read your reasoning).

Next:
  - /web-modernize:retry <unit.id> --with-prompt="<corrective guidance>"
  - or just /web-modernize:next  (will pick this unit again if eligible)
```

## Edge cases

- **Working tree dirty with unrelated changes**: refuse to proceed; print `git status` output and ask the user to stash/commit first. Rollback must not collide with the user's other work.
- **Unit was never committed (still on a dirty working tree)**: skip the branch logic; just delete/restore files. Mention this in the closing summary.
- **No feature branch existed**: skip step 2 entirely. Closing summary says "no feature branch to delete".
- **Some target_paths missing from disk**: log a note, continue with the others. The unit may have been partially-migrated.
- **Pre-existing file was modified by other commits since the migration**: the `git checkout <root_commit> -- <path>` will obliterate those changes. Detect this case (commits to that path after `state.created_at`), refuse, and tell the user to resolve manually.

## State transitions

- Pre: `state.status >= "in_progress"`, `unit.status ∈ {migrated, verified, failed}`.
- Post: top-level status unchanged. Per-unit file: `<previous>` → `pending`, `rollback_info` populated.

## Out of scope

This skill rolls back **one unit at a time**. Multi-unit rollback (e.g., "roll back the whole phase 2") is intentionally not supported — chain `/web-modernize:rollback --unit <id>` calls if you need it. For a global reset, use `/web-modernize:abandon --soft` or `--hard`.
