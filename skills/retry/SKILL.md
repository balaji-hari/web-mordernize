---
description: "Re-attempt a failed unit, optionally with extra guidance via --with-prompt. Use when a unit is in 'failed' status. Triggers: 'retry <unit>', 'try again', 'fix the failed unit', 'redo', 'retry the migration', 'attempt again'."
disable-model-invocation: false
---

# `/web-modernize:retry <unit-id> [--with-prompt="<guidance>"] [--plan | --no-plan]`

You are the **retry** skill. You re-attempt a failed unit migration with the same algorithm as `/web-modernize:next`, but the unit is named explicitly and the prior failure context is preserved.

## Preflight

1. Parse `$ARGUMENTS`:
   - First token is `<unit-id>` (required).
   - Optional flag `--with-prompt="<text>"` (quoted; spaces allowed inside). Strip the quotes when capturing the value.
   - Optional plan-gate override (default: none): `--plan` → `plan_override = "on"` (force the per-unit plan gate even when `review_mode` is `auto`); `--no-plan` → `plan_override = "off"` (skip the gate even when `review_mode` is `plan-first`); neither → `plan_override = null` (use the migration-wide `state.review_mode` default).
   - If `<unit-id>` is missing or only the flag is provided, print usage and stop:
     ```
     Usage: /web-modernize:retry <unit-id> [--with-prompt="<guidance>"] [--plan | --no-plan]

     Examples:
       /web-modernize:retry LoginController
       /web-modernize:retry LoginController --with-prompt="Use cookie session, not JWT — backend already sets HTTP-only session cookies."

     The unit must currently be in status `failed`. To revert a unit's target
     files before retrying, run /web-modernize:rollback --unit <id> first.
     ```

2. Read `.claude/modernize/state.json`. Require `status ∈ {foundation_done, in_progress}`. Otherwise redirect to the missing skill.

3. Read `.claude/modernize/units/<unit-id>.json`. If the file does not exist, list valid ids (`ls .claude/modernize/units/*.json`) and stop.

4. Check `unit.status`:
   - `failed` → proceed.
   - `pending` → "Unit is `pending`; just use /web-modernize:next or /web-modernize:migrate."
   - `in_progress` → "Unit is currently in-flight. Wait or use /web-modernize:next to take over."
   - `migrated` / `verified` → "Unit has already been migrated. Use /web-modernize:rollback --unit <id> first if you want to redo it."
   - `blocked` / `skipped` → "Unit is `<status>`. Use /web-modernize:abandon --unit to clear the marker first."

5. If `unit.target_paths` is non-empty and any of those files still exist on disk, **warn**:

   ```
   WARNING: Unit <id> has leftover target files from the failed attempt:
     <list>

   Retrying without first rolling back may cause the new attempt to fight with
   the old files (duplicate exports, stale imports, etc.).

   Continue anyway? (yes/no)
     Tip: cancel and run /web-modernize:rollback --unit <id> first.
   ```

   Default to `no` on unclear input.

## Show the prior failure

Before retrying, print the prior diagnostic and the retry count so the user remembers what they are getting into:

```
Retrying <unit.id>  (retry #<retry_count + 1>)

Prior failure diagnostic:
  <unit.failure.diagnostic>

Prior diagnostic history (last 3):
  <each entry from unit.failure.diagnostic_history, most recent first>

Retry-prompt override: <"<text>" | "(none — using migration.md as-is)">
```

If the user provided `--with-prompt`, repeat their override back to them verbatim. They will see how the shared agent interprets it.

## Run the shared migration procedure

Follow `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator-caller.md`, inline, starting at §A1, with:

- `mode = "retry"`
- `unit = <the failed unit object you just read from units/<id>.json>`
- `retry_prompt = <the --with-prompt value, or null>`
- `force_deps = false`
- `plan_override = <the value parsed in Preflight step 1>`

Part A will:

1. Move the current `unit.failure.diagnostic` into `unit.failure.diagnostic_history[]` (preserving the prior `retry_count` on that entry) — §A2.
2. Increment `unit.retry_count`.
3. Set `unit.last_retry_prompt = retry_prompt` (or leave unchanged if null).
4. Reset `unit.failure.diagnostic` and `unit.failure.branch` to empty.
5. Acquire the unit (status → `in_progress`, populate `in_flight`) and write `units/<unit.id>.json`.
6. Launch `agents/unit-migrator-subagent.md` (once, or twice around a plan-gate approval) to bias the migration design by `retry_prompt` and either finish as `migrated` or stop as `failed`.
7. At §A7, write the final record — the new diagnostic in `failure.diagnostic` if it failed again, the old one already preserved in `failure.diagnostic_history`.

## Closing message

On success (`unit.status == "migrated"`):

```
✓ Retry #<retry_count> succeeded — <unit.id> migrated.

Source: <source_paths>
Target: <target_paths>
Notes:  .claude/modernize/notes/<unit.id>.md  (see "Retry #<n>" section)
Unit file: .claude/modernize/units/<unit.id>.json

The prior failure diagnostics are preserved in units/<unit.id>.json under
unit.failure.diagnostic_history (use /web-modernize:status or read the file
to inspect).

Next:
  1. Review the diff: git diff --stat
  2. Run /web-modernize:verify <unit.id>
  3. Commit when satisfied.
```

On failure (`unit.status == "failed"` again):

```
✗ Retry #<retry_count> also failed.

New diagnostic:
  <unit.failure.diagnostic>

Diagnostic history now has <n> entries — inspect units/<unit.id>.json to see
the pattern across attempts. Possible next steps:

  - Try another /web-modernize:retry with a more specific --with-prompt.
  - /web-modernize:rollback --unit <id> to clean up partial files first.
  - /web-modernize:abandon --unit <id> to declare this unit out of scope.
  - Edit units/<id>.json directly to set status `blocked` and document why a
    human needs to migrate this unit manually.
```

On cancel at the plan gate (the user chose `[c]` in `agents/unit-migrator-caller.md` §A6 — `unit.status` is now `pending`, no new files written):

```
○ Retry cancelled at the plan gate — <unit.id> is back to `pending`; nothing was written.
  The prior failure diagnostics are still preserved in units/<unit.id>.json.
  Re-run /web-modernize:retry <unit.id> when ready (add --no-plan to skip the gate).
```

## Edge cases

- **`--with-prompt` value contains newlines or quotes**: encourage single-line, but accept multi-line. Capture verbatim — do NOT collapse whitespace; the model will read it as-is.
- **Same `--with-prompt` as a previous retry** (already in `last_retry_prompt`): warn "you used the same guidance last time — this is likely to fail the same way" and ask the user to confirm.
- **`unit.retry_count` is high (≥ 3)**: print a soft hint suggesting the user consider `/web-modernize:abandon --unit <id>` or a human pass.

## State transitions

- Pre: `state.status ∈ {foundation_done, in_progress}`, `unit.status == "failed"`.
- Post: top-level status unchanged. Per-unit file: `failed` → `in_progress` → `migrated` (or `failed` again with bumped retry_count and appended diagnostic_history).
