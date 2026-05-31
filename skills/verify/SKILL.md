---
description: "Run lint/typecheck/tests and transition a unit from 'migrated' to 'verified'. Use when at least one unit is in 'migrated' status. Triggers: 'verify', 'run tests', 'check the migration', 'is it passing', 'verify this unit', 'run verification'."
disable-model-invocation: false
---

# `/web-modernize:verify [unit-id]`

You are the **verify** skill. Your job is to prove (or disprove) that a migrated unit meets the team's bar.

## Plugin-version skew check

Read `state.json.plugin_version` (treat absent/null as "old/unknown"). Read the running plugin's version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. Parse both as `MAJOR.MINOR.PATCH`. If `state.plugin_version`'s major **or** minor differs from the running version (patch differences are fine), print **before** anything else and **continue** (warn, do not refuse):

```
⚠ Plugin version skew detected.
   State written by: <state.plugin_version or "unknown">
   Running version:  <running.version>
   Teammates on different plugin versions writing to the same state can
   produce shape mismatches. Recommended: have everyone run
   /plugin uninstall web-modernize && /plugin install web-modernize, then continue.
```

Refusing would block the team until the slowest updater catches up — that's a worse failure mode than a warned-but-continued run. On successful exit (right before the "✓ done" message), set `state.plugin_version = "<running version>"` so the warning self-resolves after one synchronized run.

## Preflight

1. Read `.claude/modernize/state.json`. Require at least `status == "scaffolded"` (i.e., target project exists).
2. Read `.claude/modernize/verify.config.json`. Required.
3. Parse `$ARGUMENTS`:
   - Empty → verify ALL units currently in status `migrated`. Iterate `state.unit_ids[]`, read each `units/<id>.json`, filter to `status == "migrated"`.
   - `<unit-id>` → read `.claude/modernize/units/<unit-id>.json`. If the file does not exist, list valid ids (`ls .claude/modernize/units/*.json`) and stop.

## Per-unit verification

For each unit to verify:

1. **Check status**. Unit must be in status `migrated` (or `verified` for re-runs). If in some other status, print:
   - `pending` / `in_progress` → "Cannot verify — unit has not been migrated yet."
   - `failed` → "Cannot verify — unit migration failed. Fix and re-migrate first."
   - `skipped` / `blocked` → "Cannot verify — unit is <status>."

2. **Resolve verification commands**. Pick the subsystem-appropriate block from verify.config.json:
   - If `unit.target_paths` mostly under `<ui_root>` → use `verify.config.ui`.
   - If mostly under `<api_root>` → use `verify.config.api`.
   - If both (cross-cutting) → run both blocks.

   Substitute placeholders:
   - `${target_path}` = unit's target_paths joined by space
   - `${ui_root}`, `${api_root}` = paths from `state.json.scaffold`

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

5. **Decide unit status transition** and write `.claude/modernize/units/<unit-id>.json`:
   - All `tests_must_pass`, `lint_must_pass`, `typecheck_must_pass` thresholds met → set `status = "verified"`.
   - Otherwise → keep `status = "migrated"` but record the failure detail in `verification.failures[]` and in the unit's `notes_path`.

6. **Append history** to the per-unit file:
   ```json
   { "at": "<now>", "by": "<user>", "from": "migrated", "to": "verified" (or unchanged), "session_id": "..." }
   ```

7. **Update `notes/<unit-id>.md`** — fill in the "Verification" section with the actual command output (trimmed to relevant lines if too long).

## Project-wide post-checks

If `verify.config.json` has `global_post_checks[]`, evaluate each:
- `run_when: "every_unit"` → run after every successful unit verification.
- `run_when: "every_5_units"` → run only if `(verified count) % 5 == 0`.
- `run_when: "before_complete"` → run only when this verification would tip top-level `state.status` to `complete`.

Common post-check: a full `npm run build` to catch cross-unit type errors that per-unit lint missed.

### Built-in aggregate coverage post-check (soft)

In addition to whatever the team configured in `verify.config.json`, automatically run an aggregate coverage check at `run_when: "before_complete"` if `state.testing.target_pct` is set and at least one unit has a `tests.coverage` block.

1. Pick the runner-wide coverage command from `state.testing` (mirror the per-unit commands in `agents/unit-migrator.md` §3 step 7c, but without `target_paths` scoping — measure the whole project):

   | Runner | Project-wide coverage command (working dir = scaffold path) |
   |---|---|
   | `vitest` | `npx vitest run --coverage` |
   | `jest` | `npx jest --coverage` |
   | `karma-jasmine` | `ng test --watch=false --code-coverage` |
   | `pytest` | `pytest --cov=app --cov-report=json:.coverage.json` |
   | `xunit` / `nunit` / `mstest` | `dotnet test --collect:"XPlat Code Coverage"` then parse the Cobertura XML |
   | `junit5` | `./mvnw -q test jacoco:report` then parse `target/site/jacoco/jacoco.xml` |
   | `manual` / `n/a` | skip this post-check entirely |

2. Parse the aggregate `pct` and the per-unit breakdown (map file paths back to units via each unit's `target_paths`).

3. **Soft-fail behaviour.** Whichever way it goes, this post-check **does not block** the flip to `state.status = "complete"`. It informs.

   - If aggregate `pct >= state.testing.target_pct`: print one green line, no further action.
   - If aggregate `pct < state.testing.target_pct`: print a yellow warning:

     ```
     ⚠ Project-wide coverage below target.
       Aggregate: <pct>%  (target: <target_pct>%)
       Units below threshold:
         - <unit.id>: <pct>%
         - ...
       Soft-fail policy: state.status will still flip to "complete". To enforce a hard bar,
       raise coverage on the listed units and re-run /web-modernize:verify.
     ```

4. **Update per-unit `tests.coverage`** for each unit whose measurement just changed. If a previously-below-threshold unit is now at or above target, set `below_threshold = false` and clear `uncovered_regions`. If a previously-above-threshold unit slid below (cross-unit regression), set `below_threshold = true` and re-populate `uncovered_regions`.

5. Record the aggregate result on `state.json.testing.last_aggregate_check`:
   ```json
   "last_aggregate_check": {
     "at": "<now>",
     "aggregate_pct": <integer>,
     "target_pct": <integer>,
     "below_threshold": <bool>,
     "units_below": ["<unit.id>", "..."]
   }
   ```

This post-check is part of `/verify`'s normal flow whenever it would tip top-level status to `complete`. It is not surfaced as a separate command.

## Project-wide complete check

After this run, iterate `state.unit_ids[]`, read each `units/<id>.json`, and check if every non-skipped unit has `status == "verified"`. If yes:

- Iterate `migration.md §10` acceptance criteria. For each unchecked `- [ ]` item, ask the user "Is this met? (yes/no/n/a)" and if yes, change to `- [x]` in migration.md.
- Once all required acceptance criteria are checked: set `state.json.status = "complete"`, save `state.json`, and print a closing message.

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
- Post: top-level unaffected unless this was the last verification → `complete`
- Per-unit file: `migrated` → `verified` (on pass) or unchanged
