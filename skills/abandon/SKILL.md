---
description: >
  Rollback / reset for the web-modernize migration. Two-step destructive command
  with multiple modes: --soft clears state but keeps notes/, --hard deletes
  generated artifacts including target scaffold, --unit <id> marks a single
  unit as skipped without touching the rest. Always requires a second
  confirming invocation before deleting anything. Use when the team wants to
  start over or formally drop a unit from scope.
disable-model-invocation: false
---

# `/web-modernize:abandon [--soft|--hard] [--unit <id>]`

You are the **abandon** skill. You are explicitly destructive. **Never delete anything on the first invocation.**

## Preflight

1. Read `state.json`. If it does not exist, tell user "Nothing to abandon — web-modernize is not initialized here." and stop.
2. Parse `$ARGUMENTS`:
   - `--soft` → keep `notes/` directory and `migration.md`; clear state.json units and reset top-level status to `initialized`.
   - `--hard` → delete `.claude/modernize/`, delete target scaffold directories (whatever's in `state.scaffold.ui.path`, `.api.path`, `.db.path`), leave `migration.md` alone.
   - `--unit <id>` → mark single unit as `skipped` with reason; do not touch other state.
   - No args → ask the user which mode they want; describe each clearly.

## Two-step confirmation

Check for the existence of `.claude/modernize/ABANDON_REQUESTED`.

### First invocation (no marker file)

1. Print a detailed preview of what will be deleted/modified. Be exact: list every file or directory that will go away, and every state change.

   For `--soft`:
   ```
   This will:
     - Reset .claude/modernize/state.json (units, scaffold, source/target stack cleared)
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
     - .claude/modernize/notes/  (and every file under it)
     - .claude/modernize/verify.config.json
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
     - Set unit <id>.status = "skipped"
     - Append to <id>.history a "skipped via /abandon" entry
     - KEEP .claude/modernize/notes/<id>.md (if exists)

   The unit will no longer be picked by /web-modernize:next and will not block dependents
   (dependents will skip it in their depends_on resolution).
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

   - Read existing state.json.
   - Reset units, scaffold, source_stack, target_stack, strategy, out_of_scope.
   - Keep `repo` block.
   - Set `status = "initialized"`, `updated_at = "<now>"`.
   - Save.

   #### `--hard`

   - Capture paths from state.json BEFORE deleting it.
   - Delete `.claude/modernize/` recursively.
   - Delete target directories (`scaffold.ui.path`, etc.), but only if they were created by this plugin (heuristic: check that the directory was non-existent before scaffold AND no files inside are commits older than `state.created_at`). If unsure, print the directory and ask the user to confirm individually.
   - Do NOT touch `migration.md`.
   - Do NOT run any `git` commands — let the user commit the deletions themselves.

   #### `--unit <id>`

   - Find unit. Set `status = "skipped"`.
   - Append history entry: `{from: <previous>, to: "skipped", reason: "manual /abandon"}`.
   - Update any other units whose `depends_on` includes this id: prune the dependency (so they no longer wait on a skipped unit).
   - Save state.json.

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
- **In-flight unit exists**: refuse `--soft` and `--hard` until in-flight is resolved (`/web-modernize:status` will show it). Tell the user how to abort the in-flight (Ctrl+C if active, or `/web-modernize:abandon --unit <id>` first).

## State transition

- `--soft`: `<any>` → `initialized`
- `--hard`: `<any>` → effectively `uninitialized` (state.json deleted)
- `--unit <id>`: top-level status unchanged; unit → `skipped`
