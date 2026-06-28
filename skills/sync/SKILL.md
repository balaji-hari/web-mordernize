---
description: "Reconcile local and remote state.json + per-unit files for multi-developer workflows. Use when the team works in parallel and git shows merge churn on state files. Triggers: 'sync state', 'pull teammates changes', 'reconcile state', 'merge state files', 'after git pull'."
disable-model-invocation: false
---

# `/web-modernize:sync`

You are the **sync** skill. Your job is to reconcile the team's `state.json` plus per-unit files after concurrent work, without forcing the user to hand-resolve JSON merge conflicts.

In schema v3, each unit lives in its own file at `.claude/modernize/units/<id>.json`. Two devs editing different units touch completely different files, so git merges them trivially — there is nothing for `/sync` to do in that common case. The work of `/sync` reduces to:
- Reconciling top-level `state.json` (which both devs touch on phase transitions, `unit_ids` updates, etc.).
- Per-file merging of the rare case where two devs edited the **same** unit's file.

## Preflight

1. Confirm the current directory is a git repo with a remote. `git config --get remote.origin.url` must return non-empty. If not:
   ```
   /web-modernize:sync only works when there is a git remote. No remote.origin
   configured — your state files are the only ones. Nothing to sync.
   ```
   Stop.

2. Read `.claude/modernize/state.json`. Required. If absent: "No local state.json — run /web-modernize:init first." Stop.

3. Determine the current branch (`git rev-parse --abbrev-ref HEAD`).

4. **Refuse to sync** if any of these conditions hold:
   - The working tree has uncommitted changes to `.claude/modernize/state.json` OR any file under `.claude/modernize/units/` (`git diff --quiet -- .claude/modernize/state.json .claude/modernize/units/` is non-zero). In that case:
     ```
     You have uncommitted changes under .claude/modernize/. Commit or stash them
     before syncing, so the merge has a clean base. Run:
       git status -- .claude/modernize/
       git diff -- .claude/modernize/
     to see what's pending.
     ```
     Stop.
   - There is an in-flight unit currently held by the current user (iterate `units/*.json`; find one with `in_flight.by == <user>` and fresh heartbeat). Syncing in the middle of your own active migration is risky.
     ```
     You have an in-flight migration of <unit.id> (started <N> min ago). Finish or
     pause it before syncing — /web-modernize:sync may otherwise overwrite your
     in_flight progress with a stale remote copy.
     ```
     Default to refusal; allow override only with explicit user confirmation.

## Fetch the remote view

Run `git fetch origin --quiet` first (the only network call; do not pull any files into the working tree).

Then read the remote top-level state.json without checking it out:

```sh
git show origin/<branch>:.claude/modernize/state.json
```

If this fails:
- File missing on remote: "Remote `origin/<branch>` has no state.json — nothing to sync. (Likely the team's first push.)" Stop.
- Branch missing: "Remote `origin/<branch>` doesn't exist yet. Push your local branch first: `git push -u origin <branch>`." Stop.

Parse as JSON. On parse failure: print the parser error and tell the user "Remote state.json appears corrupt; resolve manually with `git diff origin/<branch> -- .claude/modernize/state.json`." Stop.

Also list remote per-unit files:

```sh
git ls-tree --name-only origin/<branch> .claude/modernize/units/
```

This gives the set of remote unit file paths. Strip the prefix to get the set of remote ids.

If the remote top-level state.json is **byte-identical** to local AND the set of remote unit ids matches local AND every same-id file is byte-identical (`git diff --quiet origin/<branch> -- .claude/modernize/units/`), print:

```
✓ Already in sync. Local matches origin/<branch>.
```

and stop.

## Merge rules — top-level state.json

Apply these rules in order to produce the merged top-level state.

### Top-level `status`

Order: `complete > in_progress > foundation_done > scaffolded > planned > analyzed > initialized > uninitialized`.

Take the **higher** of `local.status` and `remote.status`.

### `repo`, `source_stack`, `target_stack`, `strategy`, `out_of_scope`

These are write-once fields set by `/init`, `/analyze`, `/plan`. If they differ:

- If one side is `null` and the other is set: take the non-null side.
- If both are set but differ: take the one with the more recent `updated_at`. As a fallback, take the one with more populated sub-fields. Print a warning if neither dominates clearly.

### `scaffold`

Per-subsystem (ui / api / db). If both sides have a populated `scaffold.<sys>` block, take the one with the later `completed_at`. If one side is null on a subsystem, take the other side's value.

### `unit_ids`

Build the union, preserving order. Algorithm:
1. Start with the **remote** `unit_ids` array (treated as the canonical plan order).
2. Append any ids present in local but not in remote, at the end, preserving local relative order.
3. The resulting array becomes the merged `unit_ids`.

### `lock`

- If both are `null`: `null`.
- If one is `null` and the other has `expires_at` in the future: take the active lock.
- If both have `expires_at` in the future: take the one with the **earlier** `expires_at` — that's the lock that was acquired first.
- If both are expired: `null`.

### `created_at`, `updated_at`

- `created_at`: take the **earlier**.
- `updated_at`: set to **now** (after the merge).

### `schema_version`, `plugin_version`

These should match in normal operation. If they differ, take the higher and add a warning to the report.

## Merge rules — per-unit files

For each id in the union of local and remote `unit_ids`:

### Case 1 — id present only on remote

The unit is new to local. Fetch it:

```sh
git show origin/<branch>:.claude/modernize/units/<id>.json > .claude/modernize/units/<id>.json
```

No merge needed. Note in the report as "added from remote".

### Case 2 — id present only on local

Keep the local file as-is. Note in the report as "kept local (will go to remote on your next push)".

### Case 3 — id present on both sides

If the two files are byte-identical (`git diff --quiet origin/<branch> -- .claude/modernize/units/<id>.json`), no action; do not list in the report (uninteresting).

Otherwise, apply per-field merge rules to produce the merged per-unit file and write it to `.claude/modernize/units/<id>.json`:

- **Status**: take the most-advanced. Order: `verified > migrated > in_progress > failed > blocked > skipped > pending`. The choice of `failed` over `skipped` is intentional — a failure with diagnostic carries more information than a passive skip.
- **`history[]`**: concatenate both arrays. De-duplicate by `(at, by, from, to)`. Sort ascending by `at`.
- **`in_flight`**:
  - If both are `null`: keep `null`.
  - If one is `null` and the other set: take the set one **only if** its `last_heartbeat` is fresh (<15 min). Otherwise discard.
  - If both are set: take the one with the more recent `last_heartbeat`. If both are stale (>15 min), discard both and set to `null`.
- **`target_paths[]`**: union (de-duplicated, preserve order from the "most-advanced status" side).
- **`verification`**: take the one tied to the side whose status was selected. If both sides have `verified` status, take the more recent `verified_at`.
- **`failure`**: take the one tied to the most-recent `from -> failed` history entry. Merge `diagnostic_history[]` from both sides (concat, sort by `at`).
- **`retry_count`**: take the **max**.
- **`last_retry_prompt`**: take the one tied to the higher `retry_count`. If tied, prefer the local one.
- **`rollback_info`**: take the one with the more recent `at`. Older `rollback_info` is overwritten — the unit might have been rolled back multiple times; only the most recent matters.
- **`source_paths`, `kind`, `depends_on`, `phase`, `effort`**: these are plan-defined. Take the one whose side has the more recent top-level `updated_at` (i.e., whichever was last `/plan`-ed).
- **`notes_path`**: should be deterministic from `id`; if they differ, log a warning and take the most-advanced side.

## Apply the merge and report

Write all merged files to disk:
- `.claude/modernize/state.json` (always, after the top-level merge).
- `.claude/modernize/units/<id>.json` for every id in Case 1 or Case 3.

Do NOT commit — let the user review with `git diff` first.

Print a plain-language reconciliation report:

```
✓ Synced with origin/<branch>.

Top-level state.json:
  status:  local=<local.status>  remote=<remote.status>  → kept <chosen>
  unit_ids: <N> local, <M> remote → <K> merged

Per-unit files:
  <K> total units across both sides
  <X> identical (no change)
  <Y> updated from remote (you were behind):
    - <unit.id>: <local.status> → <remote.status>
    ...
  <Z> added from remote (new units in plan):
    - <unit.id>
    ...
  <W> kept local (remote was behind):
    - <unit.id>: <remote.status> ← yours: <local.status>
    ...

In-flight reconciliation:
  - <unit.id>: kept <whose> in-flight block (<reason: fresher heartbeat / only side with one>)
  - <unit.id>: discarded stale in-flight (both sides >15 min old)

Review and commit:
  git status -- .claude/modernize/
  git diff -- .claude/modernize/
  git add .claude/modernize/
  git commit -m "sync: merge state with origin/<branch>"
```

If any warnings were collected during the merge (write-once field divergence, notes_path mismatch, version skew, etc.), print them as a `WARNINGS:` block before the final commit instructions.

## What sync does NOT do

- Does not run `git pull` — that could change other files. Sync only touches `.claude/modernize/state.json` and `.claude/modernize/units/*.json`.
- Does not push. After the merge, the user reviews and commits manually.
- Does not resolve conflicts on `migration.md`, `plan.md`, `analysis.json`, `notes/<id>.md`, `verify.config.json`, or `reports/`. Those follow ordinary git workflow.
- Does not merge across **branches**. If the team is on a feature-branch workflow, run sync after each fetch/rebase and let git handle the cross-branch reconciliation.

## State transitions

- Pre: `state.status >= "initialized"` (anything except no state.json at all).
- Post: top-level status may advance (never rewind) per the rules above. Per-unit statuses may advance per the same logic.
