---
description: >
  Runs target-stack lint, typecheck, and tests for a migrated unit (or for the
  whole project) and records the evidence in state.json + notes/<unit-id>.md.
  Reads verification commands from .claude/modernize/verify.config.json so the
  team can tune to their stack. Transitions units from migrated → verified
  (when everything passes) or back to migrated with annotations if failures.
disable-model-invocation: false
---

# `/web-modernize:verify [unit-id]`

You are the **verify** skill. Your job is to prove (or disprove) that a migrated unit meets the team's bar.

## Preflight

1. Read `state.json`. Require at least `status == "scaffolded"` (i.e., target project exists).
2. Read `.claude/modernize/verify.config.json`. Required.
3. Parse `$ARGUMENTS`:
   - Empty → verify ALL units currently in status `migrated`.
   - `<unit-id>` → verify just that unit.

## Per-unit verification

For each unit to verify:

1. **Look up the unit**. Must exist and be in status `migrated` (or `verified` for re-runs). If in some other status, print:
   - `pending` / `in_progress` → "Cannot verify — unit has not been migrated yet."
   - `failed` → "Cannot verify — unit migration failed. Fix and re-migrate first."
   - `skipped` / `blocked` → "Cannot verify — unit is <status>."

2. **Resolve verification commands**. Pick the subsystem-appropriate block from verify.config.json:
   - If `unit.target_paths` mostly under `<ui_root>` → use `verify.config.ui`.
   - If mostly under `<api_root>` → use `verify.config.api`.
   - If both (cross-cutting) → run both blocks.

   Substitute placeholders:
   - `${target_path}` = unit's target_paths joined by space
   - `${ui_root}`, `${api_root}` = paths from state.json.scaffold

3. **Run the commands** in order: lint → typecheck → tests. For each:
   - Run via Bash with appropriate working directory.
   - Capture stdout, stderr, exit code.
   - Record result in a working map.

4. **Build a results record** for the unit:

   ```json
   "verification": {
     "lint":      "<pass|fail|n/a>",
     "typecheck": "<pass|fail|n/a>",
     "tests":     "<X/Y pass>",
     "verified_at": "<now>",
     "verified_by": "<user>"
   }
   ```

   Use `n/a` if a command was not defined for this subsystem.

5. **Decide unit status transition**:
   - All `tests_must_pass`, `lint_must_pass`, `typecheck_must_pass` thresholds met → set unit `status = "verified"`.
   - Otherwise → keep `status = "migrated"` but record the failure detail in `verification.failures[]` and in the unit's `notes_path`.

6. **Append history**:
   ```json
   { "at": "<now>", "by": "<user>", "from": "migrated", "to": "verified" (or unchanged), "session_id": "..." }
   ```

7. **Update `notes/<unit-id>.md`** — fill in the "Verification" section with the actual command output (trimmed to relevant lines if too long).

## Project-wide post-checks

If `verify.config.json` has `global_post_checks[]`, evaluate each:
- `run_when: "every_unit"` → run after every successful unit verification.
- `run_when: "every_5_units"` → run only if `(verified count) % 5 == 0`.
- `run_when: "before_complete"` → run only when this verification would tip `state.status` to `complete`.

Common post-check: a full `npm run build` to catch cross-unit type errors that per-unit lint missed.

## Project-wide complete check

If, after this run, every non-skipped unit has `status == "verified"`:

- Iterate `migration.md §10` acceptance criteria. For each unchecked `- [ ]` item, ask the user "Is this met? (yes/no/n/a)" and if yes, change to `- [x]` in migration.md.
- Once all required acceptance criteria are checked: set `state.status = "complete"` and print a closing message.

## After writing

Per-unit output:

```
verify <unit.id>:
  lint:      <result>
  typecheck: <result>
  tests:     <result>
  → <verified | still-migrated, see notes/<unit.id>.md>
```

All-units mode output: per-unit lines plus a summary:

```
Summary: <verified count>/<migrated count> passed.

  Failed:
    <unit.id>: <one-line reason>

Next: address failures, then re-run /web-modernize:verify <unit.id>.
   Or: /web-modernize:next  to migrate more units.
```

## State transitions

- Pre: `state.status` ≥ `scaffolded`
- Post: unaffected at top level (unless this was the last verification → `complete`)
- Unit: `migrated` → `verified` (on pass) or unchanged
