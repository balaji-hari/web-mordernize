---
description: >
  Reverts a single migrated, verified, or failed unit back to "pending" so it
  can be re-migrated cleanly. Restores target files via git (checks out the
  legacy state on tracked paths, removes the feature branch if one exists),
  clears the unit's verification record, and stamps rollback_info on the unit
  for audit. Per-unit and recoverable: this is the soft inverse of
  /web-modernize:migrate, not the nuclear reset that /web-modernize:abandon is.
disable-model-invocation: false
---

# `/web-modernize:rollback --unit <unit-id>`

You are the **rollback** skill. You undo a single unit's migration so the team can re-attempt it cleanly. You do NOT delete the design notes (`notes/<unit-id>.md`) — those are useful as a record of the previous attempt.

## Preflight

1. Parse `$ARGUMENTS`. Expect `--unit <unit-id>`. If `--unit` is missing or no id follows, print:
   ```
   Usage: /web-modernize:rollback --unit <unit-id>

   Example: /web-modernize:rollback --unit LoginController

   This reverts the unit's target files via git and resets its status to "pending".
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
       "reason": "manual /web-modernize:rollback"
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
