---
description: "Start a brand-new modernization in this repo: create migration.md and the .claude/modernize/ scaffolding. Use when no .claude/modernize/ directory exists. Triggers: 'start a migration', 'set up the project', 'modernize this app', 'begin', 'bootstrap modernize'."
disable-model-invocation: false
---

# `/web-modernize:init`

You are the **init** skill of the `web-modernize` plugin. Your job is to lay down the migration scaffolding in the team's legacy repository **without overwriting any existing files**.

## Preflight checks

Before writing anything, do all of the following:

1. Confirm the current working directory is a git repository (`git rev-parse --show-toplevel`). If it is not, stop and tell the user to run `git init` first.
2. Read `${CLAUDE_PLUGIN_ROOT}/templates/migration.md`, `${CLAUDE_PLUGIN_ROOT}/templates/state.schema.json`, `${CLAUDE_PLUGIN_ROOT}/templates/unit.schema.json`, and `${CLAUDE_PLUGIN_ROOT}/templates/notes-template.md` (you'll need them in step 3).
3. Check for any of these existing files in the repo root:
   - `migration.md`
   - `.claude/modernize/state.json`
   - `.claude/modernize/plan.md`

   If **any** exist, do NOT touch them. Tell the user what already exists and ask if they want to (a) keep going and only create what is missing, or (b) cancel. Do not proceed until they confirm.

4. **Schema-version check.** If `.claude/modernize/state.json` exists, read its `schema_version`. If it is anything other than `3`, refuse and print:

   ```
   ✗ state.json has schema_version: <N>, but this plugin version expects 3.

   The web-modernize plugin does not ship schema-migration scripts. To proceed:

     1. Back up .claude/modernize/ if you want to keep notes or history.
     2. Delete the .claude/modernize/ directory entirely.
     3. Re-run /web-modernize:init.

   You will need to re-run /web-modernize:analyze and /web-modernize:plan to
   rebuild state. Per-unit notes under .claude/modernize/notes/ are safe to
   copy back after re-init.
   ```

   Stop without mutating anything.

## Files to create

Create the following, **only if they do not already exist**:

### 1. `migration.md` at the repo root

Copy the contents of `${CLAUDE_PLUGIN_ROOT}/templates/migration.md` verbatim.

### 2. `.claude/modernize/state.json`

Write a minimal valid state.json. Use the current ISO-8601 UTC timestamp for `created_at` and `updated_at`. Capture the git remote URL (`git config --get remote.origin.url`, or empty string if no remote) and the current HEAD commit short SHA (`git rev-parse --short HEAD`, or empty string if no commits yet). Read the running plugin's version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` and write that into `plugin_version` — do NOT hardcode a literal version here, or every fresh init will trigger a version-skew warning on the next skill run.

```json
{
  "schema_version": 3,
  "plugin_version": "<RUNNING_PLUGIN_VERSION>",
  "repo": {
    "remote": "<GIT_REMOTE_OR_EMPTY>",
    "root_commit": "<GIT_SHORT_SHA_OR_EMPTY>"
  },
  "status": "initialized",
  "source_stack": null,
  "target_stack": null,
  "strategy": null,
  "scaffold": null,
  "unit_ids": [],
  "out_of_scope": [],
  "lock": null,
  "created_at": "<NOW_ISO>",
  "updated_at": "<NOW_ISO>"
}
```

### 3. `.claude/modernize/units/.gitkeep`

Empty file so the per-unit directory is tracked in git even before any units are seeded.

### 4. `.claude/modernize/notes/.gitkeep`

Empty file so the directory is tracked in git.

### 5. `.claude/modernize/verify.config.json`

Copy `${CLAUDE_PLUGIN_ROOT}/templates/verify.config.json` verbatim. Tell the user they should edit it after running `/web-modernize:scaffold` so it points at their actual target directories.

### 6. `.gitignore` patch

Open the team's existing `.gitignore` (create it if absent). Append the following block at the end, but **only if the block is not already present** (check by searching for the marker line):

```
# web-modernize plugin — per-developer scratch (not shared)
CLAUDE.local.md
.claude/settings.local.json
# web-modernize plugin — quarantined secrets discovered in legacy code (never commit raw values)
.claude/modernize/SECRETS.local.md
.claude/modernize/**/SECRETS.local.md
```

The `SECRETS.local.md` lines keep raw credentials the agents discover in legacy source out of git. The agents (`legacy-analyzer`, `unit-migrator`, `parity-reviewer`, `migration-critic`) mask secret **values** in everything they write to tracked artifacts; if a raw value must be recorded for the team to rotate, it goes only to this gitignored file.

## After writing

Print this exact summary to the user, substituting actual file paths:

```
✓ web-modernize initialized (schema v3)

Created:
  - migration.md                          ← target choices filled via /analyze interview
  - .claude/modernize/state.json
  - .claude/modernize/units/              (per-unit state will land here)
  - .claude/modernize/notes/              (per-unit design notes)
  - .claude/modernize/verify.config.json

Next steps:
  1. Run /web-modernize:analyze — it auto-fills migration.md §2 (source stack) AND
     interactively walks you through filling the REQUIRED target choices
     (§3 UI framework, §4 API framework, §6 strategy, §7 auth, §12 testing) with
     stack-aware recommendations. No manual migration.md editing required for the
     common case.
  2. Run /web-modernize:plan to generate the migration plan and seed units.
```

## Failure modes

- Working directory not a git repo → instruct user to `git init`, then re-run.
- `migration.md` already exists → ask before touching.
- `state.json` exists with `schema_version != 3` → refuse with the message above; do not migrate.
- Cannot write to `.claude/modernize/` (permissions) → report exact error.
- Skill must be **idempotent** if re-run after partial creation: detect what already exists and only create what is missing.

## State transition

- Pre: any (typically nothing, but tolerates re-runs against a v3 state).
- Post: `state.json.status = "initialized"` (only if state.json was newly created; do not modify an existing state.json's status).
