---
description: >
  Bootstraps a legacy web app repository for migration with the web-modernize plugin.
  Copies the migration.md template to the repo root, creates .claude/modernize/
  with an initial state.json, seeds the notes/ directory, and patches .gitignore.
  Safe to run multiple times — refuses to overwrite existing files. Run this once
  per legacy repo as the very first command in the modernization workflow.
disable-model-invocation: false
---

# `/web-modernize:init`

You are the **init** skill of the `web-modernize` plugin. Your job is to lay down the migration scaffolding in the team's legacy repository **without overwriting any existing files**.

## Preflight checks

Before writing anything, do all of the following:

1. Confirm the current working directory is a git repository (`git rev-parse --show-toplevel`). If it is not, stop and tell the user to run `git init` first.
2. Read `${CLAUDE_PLUGIN_ROOT}/templates/migration.md`, `${CLAUDE_PLUGIN_ROOT}/templates/state.schema.json`, and `${CLAUDE_PLUGIN_ROOT}/templates/notes-template.md` (you'll need them in step 3).
3. Check for any of these existing files in the repo root:
   - `migration.md`
   - `.claude/modernize/state.json`
   - `.claude/modernize/plan.md`

   If **any** exist, do NOT touch them. Tell the user what already exists and ask if they want to (a) keep going and only create what is missing, or (b) cancel. Do not proceed until they confirm.

   Exception: if `.claude/modernize/state.json` exists with `schema_version: 1`, you MUST upgrade it in place to schema v2 (see "Schema migration" below). This is the only state.json mutation init is allowed to make on an existing file. Treat the migration as "creating what is missing": do not ask before doing it; print what changed afterwards.

## Files to create

Create the following, **only if they do not already exist**:

### 1. `migration.md` at the repo root

Copy the contents of `${CLAUDE_PLUGIN_ROOT}/templates/migration.md` verbatim.

### 2. `.claude/modernize/state.json`

Write a minimal valid state.json. Use the current ISO-8601 UTC timestamp for `created_at` and `updated_at`. Capture the git remote URL (`git config --get remote.origin.url`, or empty string if no remote) and the current HEAD commit short SHA (`git rev-parse --short HEAD`, or empty string if no commits yet).

```json
{
  "schema_version": 2,
  "plugin_version": "0.2.0",
  "repo": {
    "remote": "<GIT_REMOTE_OR_EMPTY>",
    "root_commit": "<GIT_SHORT_SHA_OR_EMPTY>"
  },
  "status": "initialized",
  "source_stack": null,
  "target_stack": null,
  "strategy": null,
  "scaffold": null,
  "units": [],
  "out_of_scope": [],
  "lock": null,
  "created_at": "<NOW_ISO>",
  "updated_at": "<NOW_ISO>"
}
```

### 3. `.claude/modernize/notes/.gitkeep`

Empty file so the directory is tracked in git.

### 4. `.claude/modernize/verify.config.json`

Copy `${CLAUDE_PLUGIN_ROOT}/templates/verify.config.json` verbatim. Tell the user they should edit it after running `/web-modernize:scaffold` so it points at their actual target directories.

### 5. `.gitignore` patch

Open the team's existing `.gitignore` (create it if absent). Append the following block at the end, but **only if the block is not already present** (check by searching for the marker line):

```
# web-modernize plugin — per-developer scratch (not shared)
CLAUDE.local.md
.claude/settings.local.json
```

## Schema migration (v1 → v2)

If the existing `.claude/modernize/state.json` has `schema_version: 1`, upgrade it to v2 before doing anything else. The upgrade is lossless and idempotent — re-running on an already-v2 file is a no-op.

Read the existing state.json, then write back the same object with these mutations:

1. Set `schema_version: 2`.
2. Set `plugin_version: "0.2.0"`.
3. Set `updated_at: "<NOW_ISO>"`.
4. For **every** entry in `units[]`, add the following keys if they are not already present (do not overwrite if present):
   - `retry_count: 0`
   - `last_retry_prompt: null`
   - `rollback_info: null`
   - If `failure` is set on the unit but `failure.diagnostic_history` is missing, add `failure.diagnostic_history: []`. Do not back-fill the array from the existing `failure.diagnostic` — leave that for the first `/retry` to capture.

No other fields move. Do not validate the rest of the file against the schema; preserve unknown keys verbatim.

After upgrading, print:

```
✓ Upgraded .claude/modernize/state.json from schema v1 to v2.
  Added per-unit fields: retry_count, last_retry_prompt, rollback_info.
  No existing data was modified.
```

If the file is already v2, skip silently — do not print the banner.

## After writing

Print this exact summary to the user, substituting actual file paths:

```
✓ web-modernize initialized

Created:
  - migration.md                          ← target choices go here AFTER /analyze
  - .claude/modernize/state.json
  - .claude/modernize/verify.config.json
  - .claude/modernize/notes/

Next steps:
  1. Run /web-modernize:analyze first — it auto-fills migration.md §2 (source stack).
  2. Open migration.md and fill in sections 3, 6, 7, 10 (the REQUIRED target choices)
     on top of the populated §2.
  3. Run /web-modernize:plan to generate the migration plan.
```

## Failure modes

- Working directory not a git repo → instruct user to `git init`, then re-run.
- `migration.md` already exists → ask before touching.
- Cannot write to `.claude/modernize/` (permissions) → report exact error.
- Skill must be **idempotent** if re-run after partial creation: detect what already exists and only create what is missing.

## State transition

- Pre: any (typically nothing, but tolerates re-runs).
- Post: `state.json.status = "initialized"` (only if state.json was newly created; do not modify an existing state.json's status).
