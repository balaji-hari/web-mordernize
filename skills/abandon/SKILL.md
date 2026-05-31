---
description: "Roll back the migration in part or whole (destructive; two-step confirmation). Use only when the user wants to stop or restart the migration. Triggers: 'abandon the migration', 'start over', 'wipe everything', 'cancel migration', 'reset everything', 'throw it away'."
disable-model-invocation: false
---

# `/web-modernize:abandon [--soft|--hard] [--unit <id>]`

You are the **abandon** skill. You are explicitly destructive. **Never delete anything on the first invocation.**

## Preflight

1. Read `.claude/modernize/state.json`. If it does not exist, tell user "Nothing to abandon — web-modernize is not initialized here." and stop.
2. Parse `$ARGUMENTS`:
   - `--soft` → keep `notes/` directory and `migration.md`; clear `units/*.json` files; reset `state.unit_ids = []`, scaffold, source/target stack; reset top-level status to `initialized`.
   - `--hard` → delete `.claude/modernize/` (which includes `units/` and `notes/`); delete target scaffold directories (whatever's in `state.scaffold.ui.path`, `.api.path`, `.db.path`); leave `migration.md` alone.
   - `--unit <id>` → mark single unit's per-unit file as `skipped` with reason; prune the dep from every other per-unit file's `depends_on`; do not touch top-level state otherwise.
   - No args → ask the user which mode they want; describe each clearly.

## In-flight refusal

For `--soft` and `--hard`, iterate `units/*.json` to look for any unit with `status == "in_progress"`. If one exists, refuse:

```
✗ Cannot abandon — unit <id> is currently in-flight (started by <in_flight.by>, <N> min ago).

Resolve first by:
  - Letting the migration finish (re-run /web-modernize:next to resume it), or
  - /web-modernize:abandon --unit <id>  (skip just that unit), then re-run /web-modernize:abandon.
```

Then stop.

## Two-step confirmation

Check for the existence of `.claude/modernize/ABANDON_REQUESTED`.

### First invocation (no marker file)

1. Print a detailed preview of what will be deleted/modified. Be exact: list every file or directory that will go away, and every state change.

   For `--soft`:
   ```
   This will:
     - Delete every .claude/modernize/units/<id>.json (<count> files)
     - Reset .claude/modernize/state.json (unit_ids=[], scaffold, source/target stack cleared)
     - Reset state.status from <current> back to "initialized"
     - KEEP migration.md
     - KEEP .claude/modernize/notes/ (postmortem-friendly)
     - KEEP target project scaffold under <ui.path> etc.
   ```

   For `--hard`:
   ```
   This will DELETE:
     - .claude/modernize/state.json
     - .claude/modernize/plan.md
     - .claude/modernize/analysis.json
     - .claude/modernize/units/  (and every per-unit file under it)
     - .claude/modernize/notes/  (and every file under it)
     - .claude/modernize/verify.config.json
     - .claude/modernize/reports/  (if exists)
     - <ui.path>/   <- target UI scaffold directory
     - <api.path>/  <- target API scaffold directory (if applicable)
     - <db.path>/   <- DB migrations directory (if applicable)

   This will KEEP:
     - migration.md  (your configuration, in case you want to start over with the same target)
     - .gitignore patches

   Files already committed to git are NOT removed from history — you'll need to commit the deletions yourself.
   ```

   For `--unit <id>`:
   ```
   This will:
     - Set .claude/modernize/units/<id>.json: status = "skipped"
     - Append a "skipped via /abandon" history entry to that file
     - Prune <id> from depends_on in every other units/*.json that depends on it
     - KEEP .claude/modernize/notes/<id>.md (if exists)

   The unit will no longer be picked by /web-modernize:next and will not block dependents.
   ```

2. Write a marker file `.claude/modernize/ABANDON_REQUESTED` containing JSON:

   ```json
   { "mode": "<soft|hard|unit>", "unit_id": "<if applicable>", "requested_at": "<now>", "requested_by": "<user>" }
   ```

3. Print:
   ```
   Confirmation required. Re-run the exact same command within 10 minutes to proceed:

     /web-modernize:abandon <same flags>

   To cancel, delete .claude/modernize/ABANDON_REQUESTED or just don't re-run.
   ```

4. **Stop without deleting anything.**

### Second invocation (marker exists)

1. Read marker. Check:
   - `requested_at` is within last 10 minutes — else delete marker and treat this invocation as a fresh first invocation (print preview, write new marker, stop).
   - `mode` and `unit_id` match the current `$ARGUMENTS` — else mismatch warning and ask user to clarify; do not proceed.

2. Perform the operation:

   #### `--soft`

   - Delete every file in `.claude/modernize/units/` (keep the directory and `.gitkeep`).
   - Read existing state.json.
   - Reset `unit_ids = []`, `scaffold = null`, `source_stack = null`, `target_stack = null`, `strategy = null`, `out_of_scope = []`.
   - Keep `repo` block.
   - Set `status = "initialized"`, `updated_at = "<now>"`.
   - Save state.json.

   #### `--hard`

   - Capture paths from state.json BEFORE deleting it.
   - Delete `.claude/modernize/` recursively.
   - Delete target directories (`scaffold.ui.path`, etc.), but only if they were created by this plugin (heuristic: check that the directory was non-existent before scaffold AND no files inside are commits older than `state.created_at`). If unsure, print the directory and ask the user to confirm individually.
   - Do NOT touch `migration.md`.
   - Do NOT run any `git` commands — let the user commit the deletions themselves.

   #### `--unit <id>`

   - Read `.claude/modernize/units/<id>.json`. If missing, list available unit ids and stop.
   - Set `status = "skipped"`.
   - Append history entry: `{from: <previous>, to: "skipped", reason: "manual /abandon"}`.
   - Save the per-unit file.
   - For every OTHER unit file in `units/*.json`, if its `depends_on[]` includes the skipped id, prune it and save that file too.
   - Do NOT touch top-level `state.json` apart from bumping `updated_at`.

3. Delete the marker file.

4. Print confirmation:

   ```
   ✓ Abandon (<mode>) complete.

   Files removed: <count>
   State reset to: <new status>

   Run /web-modernize:init to re-initialize, or /web-modernize:status to see what remains.
   ```

## Edge cases

- **Marker exists but user invokes with different flags**: treat as ambiguous; print both the marker contents and the new args, ask user which they meant.
- **`--hard` without target scaffold paths in state.json** (state.json corrupt or pre-scaffold): only delete `.claude/modernize/`, warn the user that target directories might exist but the plugin doesn't know their paths.
- **`--unit <id>` against a unit currently in_progress**: refuse with "Cannot skip an in-flight unit. Either let the in-flight finish or take it over with /web-modernize:next first."

## State transition

- `--soft`: `<any>` → `initialized`
- `--hard`: `<any>` → effectively `uninitialized` (state.json deleted)
- `--unit <id>`: top-level status unchanged; per-unit file → `skipped`
