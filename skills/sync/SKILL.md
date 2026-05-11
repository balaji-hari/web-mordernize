---
description: >
  Pulls the latest .claude/modernize/state.json from the git remote and merges
  it with the local copy using deterministic rules ("most-advanced unit status
  wins", "freshest heartbeat wins", "highest top-level workflow status wins").
  Replaces what would otherwise be a manual git merge conflict on state.json
  with a plain-language reconciliation report. Read-only on remote — does not
  push, commit, or fetch other files. Run before starting a new unit if other
  developers have been working in parallel.
disable-model-invocation: false
---

# `/web-modernize:sync`

You are the **sync** skill. Your job is to reconcile the team's `state.json` after concurrent work, without forcing the user to hand-resolve a JSON merge conflict.

## Preflight

1. Confirm the current directory is a git repo with a remote. `git config --get remote.origin.url` must return non-empty. If not:
   ```
   /web-modernize:sync only works when there is a git remote. No remote.origin
   configured — your state.json is the only one. Nothing to sync.
   ```
   Stop.

2. Read `.claude/modernize/state.json`. Required. If absent: "No local state.json — run /web-modernize:init first." Stop.

3. Determine the current branch (`git rev-parse --abbrev-ref HEAD`).

4. **Refuse to sync** if any of these conditions hold:
   - The working tree has uncommitted changes to `.claude/modernize/state.json` (`git diff --quiet -- .claude/modernize/state.json` is non-zero AND the file is tracked). In that case:
     ```
     You have uncommitted changes to state.json. Commit or stash them before syncing,
     so the merge has a clean base. Run:
       git diff .claude/modernize/state.json
     to see what's pending.
     ```
     Stop.
   - There is an in-flight unit currently held by the current user (`unit.in_flight.by == <user>` with fresh heartbeat). Syncing in the middle of your own active migration is risky — you might overwrite your `in_flight` block.
     ```
     You have an in-flight migration of <unit.id> (started <N> min ago). Finish or
     pause it before syncing — /web-modernize:sync may otherwise overwrite your
     in_flight progress with a stale remote copy.
     ```
     Default to refusal; allow override only with explicit user confirmation.

## Fetch the remote state.json

Run `git fetch origin --quiet` first (the only network call; do not pull any files into the working tree).

Then read the remote copy without checking it out:

```sh
git show origin/<branch>:.claude/modernize/state.json
```

If this fails (file does not exist on origin's branch, branch missing, etc.):

- If file is missing on remote: "Remote `origin/<branch>` has no state.json — nothing to sync. (Likely the team's first push.)" Stop.
- If branch is missing: "Remote `origin/<branch>` doesn't exist yet. Push your local branch first: `git push -u origin <branch>`." Stop.

Parse the remote copy as JSON. If parsing fails: print the parser error and tell the user "Remote state.json appears corrupt; resolve manually with `git diff origin/<branch> -- .claude/modernize/state.json`." Stop.

If the remote copy is **byte-identical** to the local one, print:

```
✓ Already in sync. Local state.json matches origin/<branch>.
```

and stop.

## Merge rules

The merge is mechanical — apply these rules in order. Always favour preserving forward progress; never silently overwrite work.

### Top-level status

Order: `complete > in_progress > auth_done > scaffolded > planned > analyzed > initialized > uninitialized`.

Take the **higher** of `local.status` and `remote.status`.

### `repo`, `source_stack`, `target_stack`, `strategy`, `out_of_scope`

These are write-once fields set by `/init`, `/analyze`, `/plan`. If they differ:

- If one side is `null` and the other is set: take the non-null side.
- If both are set but differ: take the one with the more recent `updated_at` on its source-of-truth skill. As a fallback, take the one with more entries / more populated sub-fields. Print a warning if neither dominates clearly.

### `scaffold`

Same as `target_stack` — write-once per subsystem. If both sides have a populated `scaffold.ui` block, take the one with the later `completed_at`. Same for `.api` and `.db`.

### `units[]`

Build a union by `id`. For each `id`:

- **Status**: take the most-advanced. Order: `verified > migrated > in_progress > complete > blocked > failed > skipped > pending`. The choice of `failed` over `skipped` is intentional — a failure with diagnostic carries more information than a passive skip.
- **`history[]`**: concatenate both arrays. De-duplicate by `(at, by, from, to)`. Sort ascending by `at`.
- **`in_flight`**: tricky.
  - If both are `null`: keep `null`.
  - If one is `null` and the other set: take the set one **only if** its `last_heartbeat` is fresh (<15 min). Otherwise treat it as stale and discard it.
  - If both are set: take the one with the more recent `last_heartbeat`. If both are stale (>15 min), discard both and set to `null`.
- **`target_paths[]`**: union (de-duplicated, preserve order from "most-advanced status" side).
- **`verification`**: take the one tied to the side whose status was selected. If both sides have `verified` status, take the more recent `verified_at`.
- **`failure`**: take the one tied to the most-recent `from -> failed` history entry. Merge `diagnostic_history[]` from both sides (concat, sort by `at`).
- **`retry_count`**: take the **max**.
- **`last_retry_prompt`**: take the one tied to the higher `retry_count`. If tied, prefer the local one.
- **`rollback_info`**: take the one with the more recent `at`. Older `rollback_info` is overwritten — the unit might have been rolled back multiple times; only the most recent matters.
- **`source_paths`, `kind`, `depends_on`, `phase`, `effort`**: these are plan-defined. Take the one whose side has the more recent `updated_at` at top level (i.e., whichever was last `/plan`-ed).
- **`notes_path`**: should be deterministic from `id`; if they differ, log a warning and take the most-advanced side.

If a unit exists on **only one** side: include it. It is a new unit added by one developer that the other has not pulled yet.

### `lock`

- If both are `null`: `null`.
- If one is `null` and other has `expires_at` in the future: take the active lock.
- If both have `expires_at` in the future: take the one with the **earlier** `expires_at` — that's the lock that was acquired first. The other dev should have seen the warning.
- If both are expired: `null`.

### `created_at`, `updated_at`

- `created_at`: take the **earlier**.
- `updated_at`: set to **now** (after the merge).

## Apply the merge and report

Write the merged state.json to disk. Do NOT commit — let the user review with `git diff` first.

Print a plain-language reconciliation report:

```
✓ Synced state.json with origin/<branch>.

Top-level workflow:
  local:  <local.status>
  remote: <remote.status>
  → kept: <chosen>

Units reconciled:
  <N> total
  <K> identical (no change)
  <M> updated from remote (you were behind):
    - <unit.id>: <local.status> → <remote.status>
    ...
  <P> added from remote (new units in plan):
    - <unit.id>
    ...
  <Q> kept local (remote was behind):
    - <unit.id>: <remote.status> ← yours: <local.status>
    ...

In-flight reconciliation:
  - <unit.id>: kept <whose> in-flight block (<reason: fresher heartbeat / only side with one>)
  - <unit.id>: discarded stale in-flight (both sides >15 min old)

History entries merged: <count>
Failure diagnostic_history entries merged: <count>

Review and commit:
  git diff -- .claude/modernize/state.json
  git add .claude/modernize/state.json
  git commit -m "sync: merge state.json with origin/<branch>"
```

If any warnings were collected during the merge (write-once field divergence, notes_path mismatch, etc.), print them as a `WARNINGS:` block before the final commit instructions.

## What sync does NOT do

- Does not run `git pull` — that could change other files. Sync only touches state.json.
- Does not push. After the merge, the user reviews and commits manually.
- Does not resolve conflicts on `migration.md`, `plan.md`, `analysis.json`, `notes/<id>.md`, or `verify.config.json`. Those follow ordinary git workflow.
- Does not merge across **branches**. If the team is on a feature-branch workflow, run sync after each fetch/rebase and let git handle the cross-branch reconciliation.

## State transitions

- Pre: `state.status >= "initialized"` (anything except no state.json at all).
- Post: top-level status may advance (never rewind) per the rules above. Unit statuses may advance per the same logic.
