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

## Files to create

Create the following, **only if they do not already exist**:

### 1. `migration.md` at the repo root

Copy the contents of `${CLAUDE_PLUGIN_ROOT}/templates/migration.md` verbatim.

### 2. `.claude/modernize/state.json`

Write a minimal valid state.json. Use the current ISO-8601 UTC timestamp for `created_at` and `updated_at`. Capture the git remote URL (`git config --get remote.origin.url`, or empty string if no remote) and the current HEAD commit short SHA (`git rev-parse --short HEAD`, or empty string if no commits yet).

```json
{
  "schema_version": 1,
  "plugin_version": "0.1.0",
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

## After writing

Print this exact summary to the user, substituting actual file paths:

```
✓ web-modernize initialized

Created:
  - migration.md                          ← FILL THIS IN before running /analyze
  - .claude/modernize/state.json
  - .claude/modernize/verify.config.json
  - .claude/modernize/notes/

Next steps:
  1. Open migration.md and fill in at least sections 3, 6, 7, 10 (the REQUIRED ones).
  2. Run /web-modernize:analyze to auto-detect your source stack.
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
