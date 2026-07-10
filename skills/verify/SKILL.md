---
description: "Run lint/typecheck/tests plus a behavioural-parity check (and an advisory migration-quality review), then transition a unit from 'migrated' to 'verified'. Use when at least one unit is in 'migrated' status. Triggers: 'verify', 'run tests', 'check the migration', 'is it passing', 'verify this unit', 'run verification', 'check parity', 'quality review'."
disable-model-invocation: false
---

# `/web-modernize:verify [unit-id] [--no-parity] [--no-quality] [--dynamic] [--capture-baseline]`

You are the **verify** skill. Your job is to prove (or disprove) that a migrated unit meets the team's bar.

## Plugin-version skew check

Read `${CLAUDE_PLUGIN_ROOT}/skills/_shared/plugin-version-check.md` and perform the check it describes before proceeding.

## Preflight

1. Read `.claude/modernize/state.json`. Require at least `status == "scaffolded"` (i.e., target project exists).
2. Read `.claude/modernize/verify.config.json`. Required.
3. Parse `$ARGUMENTS`:
   - `--no-parity` (flag, anywhere in the args) → skip the behavioural-parity gate (step 5) for this run; record `verification.parity = "skipped"` on each unit touched. For fast iteration when you already know parity is fine.
   - `--no-quality` (flag, anywhere in the args) → skip the advisory migration-quality review (step 5b) for this run; record `verification.quality = "skipped"` on each unit touched. Quality is advisory, so this never affects the verified decision — it just suppresses the extra agent run.
   - `--dynamic` (flag) → ALSO run the opt-in dynamic testing tier (step 5c: API replay + Playwright E2E). Off by default; advisory — never blocks. Requires `verify.config.json.dynamic.enabled == true` (set up by `/scaffold` when enabled in `migration.md §12`); otherwise prints setup guidance and skips.
   - `--capture-baseline` (flag, mutually exclusive with normal verification) → run the **baseline-capture** mode instead of verifying: record the legacy app's responses into `verify.config.json.dynamic.baseline_dir` so Phase-A API replay has something to diff against. Requires the legacy app to be runnable; see "Capture baseline" below.
   - The remaining non-flag token, if any, is `<unit-id>` → read `.claude/modernize/units/<unit-id>.json`. If the file does not exist, list valid ids (`ls .claude/modernize/units/*.json`) and stop.
   - No `<unit-id>` → verify ALL units currently in status `migrated`. Iterate `state.unit_ids[]`, read each `units/<id>.json`, filter to `status == "migrated"`.

## Verification strategy

Steps 1 through 5c below compute each unit's results (thresholds + the three independent reviewer dimensions). The output is the same per-unit shape either way — pick the method by what's available. Once computed (by either method), "Finalize each unit" (steps 6-8) always runs the same way, inline, regardless of which method produced the inputs.

### Method A — Workflow orchestration (preferred when the Workflow tool is available)

Running `/web-modernize:verify` is your authorization to use the **Workflow tool**. When available, invoke it instead of looping yourself:

```
Workflow({ scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/verify-run.js", args: {
  units: [<each unit object to verify>],
  verifyConfig: <verify.config.json>,
  flags: { noParity: <bool>, noQuality: <bool>, dynamic: <bool> },
  targetStack: <state.target_stack>
} })
```

Per unit, it runs the lint/typecheck/test thresholds first; **only if those pass** (and the corresponding flag wasn't set), it fans out the three independent, disjoint-write reviewer dimensions — `parity-reviewer`, `migration-critic`, and (when `flags.dynamic`) the dynamic tier — **concurrently**, since none of them depend on each other's output. Across multiple units, one unit's reviewers can be running while another unit is still running its test suite (no barrier between units) — this is the wall-clock win for `--all`/multi-unit runs; the parallel reviewer fan-out is a win even for a single unit. The workflow's `parity-reviewer`/`migration-critic` agents are **read-only** (same as everywhere else they're used) — the workflow only **returns** data; it never writes `units/<id>.json` itself. Tell the user the unit count before launching. Surface its `log()` lines.

It returns `{ results: [{ unit_id, thresholds_met, verification, raw_output_tail, parity_findings, parity_summary, blocking_parity_count, quality_findings, quality_headline, dynamic_findings, e2e_results }] }` — one entry per unit. Workflow scripts cannot generate timestamps, so `parity_reviewed_at`/`quality_reviewed_at`/`dynamic_reviewed_at`/`verified_at` are **not** in the returned object — stamp them yourself with "now" when you write each unit's file in "Finalize each unit" below, exactly as Method B already does inline. If the Workflow tool is NOT available (older Claude Code build, headless run), fall through to Method B automatically.

### Method B — sequential fallback

For each unit to verify, run steps 1 through 5c yourself, in order, exactly as below:

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

5. **Behavioural-parity gate** — skip if `--no-parity` was passed, OR if step 3's lint/typecheck/test thresholds were NOT met (a unit that already can't reach `verified` doesn't need a parity run).

   Parity proves what lint/typecheck/tests cannot: that the migrated unit *behaves like* the legacy one — same validation, same response shape/field names, same sort order, same error handling, same UI fields/states. **Tests passing ≠ behaviour preserved.**

   a. **Launch the `parity-reviewer` subagent** (Agent tool, `subagent_type: parity-reviewer`). Pass a prompt containing the unit's `id`, `kind`, `source_paths[]`, `target_paths[]`, the `notes_path` (`.claude/modernize/notes/<unit-id>.md`), and the relevant `migration.md §10` acceptance-criteria lines. It is read-only and returns a single JSON block: `{ parity_findings[], summary, warnings }`.

   b. **Graceful degrade.** If the agent errors, times out, or returns malformed JSON, do NOT block — set `verification.parity = "review-unavailable"`, print a one-line warning, and proceed to step 6 as if there were no findings. An agent hiccup must never trap a working migration in `migrated`.

   c. **Persist findings.** Write the returned array to `unit.parity_findings` (replace wholesale) and set `unit.parity_reviewed_at = <now>`. **Leave `unit.parity_acknowledged_diffs[]` untouched** — acknowledgements persist across runs and match by finding `id`.

   d. **Compute blocking findings**: every finding with `severity == "high"` whose `id` is NOT present in `unit.parity_acknowledged_diffs[]`. Medium/low findings never block — surface them as info only. (Security-kind findings — `security_authz_dropped`, `security_injection`, `security_output_encoding`, `security_secret_exposure`, `security_csrf` — are ordinary `parity_findings`; a `high` one blocks exactly like any other high and is acknowledged the same way via `/web-modernize:parity-check`. No separate handling.)

5b. **Migration-quality review** (advisory, non-blocking) — skip if `--no-quality` was passed, OR if step 3's lint/typecheck/test thresholds were NOT met (a unit that can't reach `verified` doesn't need a quality review yet).

   Orthogonal to parity: parity asks *did behaviour change?*; quality asks *is the migrated code idiomatic and maintainable, or is it the legacy paradigm in new clothes?* (WebForms-in-React, jQuery-in-a-reactive-framework, scriptlet-shaped controllers). The `migration-critic` also covers **static performance regressions** (N+1 queries, unbounded fetches, request waterfalls, blocking I/O, bundle bloat — `perf_*` finding kinds). It **never blocks** — it informs.

   a. **Launch the `migration-critic` subagent** (Agent tool, `subagent_type: migration-critic`). Pass a prompt containing the unit's `id`, `kind`, `target_paths[]`, `source_paths[]`, the `notes_path` (`.claude/modernize/notes/<unit-id>.md`), and `state.target_stack` (so it judges against the right idiom). It is read-only and returns a single JSON block: `{ quality_findings[], headline, summary, warnings }`.

   b. **Graceful degrade.** If the agent errors, times out, or returns malformed JSON, do NOT block or fail — set `verification.quality = "review-unavailable"`, print a one-line warning, and continue. Quality is advisory; an agent hiccup is a non-event.

   c. **Persist.** Write the returned array to `unit.quality_findings` (replace wholesale), set `unit.quality_reviewed_at = <now>` and `unit.quality_headline = <returned headline>`. There is no acknowledgement list — quality findings don't block, so nothing to suppress.

   d. **Quality does NOT affect the transition.** Step 6 depends ONLY on lint/typecheck/tests + parity. Quality findings — even `blocker` ones — are reported as information (see "After writing"), never as a gate.

5c. **Dynamic testing tier** (advisory, non-blocking) — run ONLY when `--dynamic` was passed AND step 3's thresholds were met. This is the higher-fidelity, runtime counterpart to the static parity/quality reviews; it **never blocks** the transition (E2E flakiness must not gate a migration). Read `verify.config.json.dynamic`:

   - If `dynamic.enabled != true` (not set up), print: `Dynamic tier not configured — enable "Dynamic testing" in migration.md §12 and re-run /web-modernize:scaffold, or add verify.config.json.dynamic.{e2e,api_replay}. Skipping.` and continue. Do not fail.
   - **Phase A — API replay** (when `dynamic.api_replay` is set and the unit touches the API): if `dynamic.baseline_dir` has recorded legacy fixtures, run the `api_replay` command (substitute `${target_path}`, `${api_root}`, `${baseline_dir}`) — a harness that replays the recorded legacy requests against the new API and diffs responses. Each diff becomes a finding `{ kind: "dynamic_api_replay", severity, observation, recommendation }`. If `baseline_dir` is empty/missing, **skip Phase A** with: `No baseline fixtures — run /web-modernize:verify --capture-baseline first. Skipping API replay.`
   - **Phase B — E2E** (when `dynamic.e2e` is set and the unit touches the UI): run the `e2e` command (Playwright) scoped to this unit's routes/flows — prefer the unit's authored spec (`unit.e2e.spec_path`, written by `unit-migrator` §7d) when present. A failing step becomes a finding `{ kind: "dynamic_e2e", severity, observation }`. **Also parse the Playwright run summary and record the pass/fail/skip counts** into `unit.e2e.e2e_results = { passed, failed, skipped, ran_at: <now> }` (create the `e2e` object if the unit predates §7d authoring). This is what `/web-modernize:report` surfaces as real run results.
   - **Graceful degrade:** any harness error/timeout → record `verification.dynamic = "unavailable"`, warn, continue. Never fail the run.
   - **Persist:** write the findings to `unit.dynamic_findings` (replace wholesale), set `unit.dynamic_reviewed_at = <now>`, `unit.e2e.e2e_results` (per above, when Phase B ran), and `verification.dynamic = "clean" | "<H> high · <M> medium · <L> low" | "skipped" | "unavailable"`. Phase C (visual diff) is out of scope.
   - **Does NOT affect the transition** (step 6 depends only on lint/typecheck/tests + parity).

## Finalize each unit

Runs the same way regardless of which method (A or B) produced the per-unit results — for Method A, once per entry in the returned `results[]`; for Method B, inline as you finish each unit's steps 1-5c.

6. **Decide unit status transition** and write `.claude/modernize/units/<unit-id>.json`:
   - lint/typecheck/test thresholds (`lint_must_pass`, `typecheck_must_pass`, `tests_must_pass`) NOT met → keep `status = "migrated"`, record the detail in `verification.failures[]` and `notes_path`. (Parity was skipped per step 5.)
   - Thresholds met AND no blocking parity findings → set `status = "verified"`. Record `verification.parity` as `"clean"` (zero findings) or `"<A> acknowledged / <I> info"`.
   - Thresholds met BUT one or more **blocking** parity findings → **keep `status = "migrated"`**. Set `verification.parity = "blocked: <N> high-severity unacknowledged difference(s)"`. This is the gate doing its job: the code compiles and tests pass, but it does not yet behave like the legacy unit. Print the blocking findings (see "After writing") and the two ways forward — fix the code and re-verify, or, if a difference is intentional, acknowledge it via `/web-modernize:parity-check <unit-id>` then re-verify.

7. **Append history** to the per-unit file:
   ```json
   { "at": "<now>", "by": "<user>", "from": "migrated", "to": "verified" (or unchanged), "session_id": "..." }
   ```

8. **Update `notes/<unit-id>.md`** — fill in the "Verification" section with the actual command output (trimmed to relevant lines if too long). When parity findings exist, append a "Behavioural parity" subsection listing each finding (`severity` · `kind` · legacy → migrated · recommendation) so reviewers see them in the diff.

## Project-wide post-checks

If `verify.config.json` has `global_post_checks[]`, evaluate each:
- `run_when: "every_unit"` → run after every successful unit verification.
- `run_when: "every_5_units"` → run only if `(verified count) % 5 == 0`.
- `run_when: "before_complete"` → run only when this verification would tip top-level `state.status` to `complete`.

Common post-check: a full `npm run build` to catch cross-unit type errors that per-unit lint missed.

### Built-in aggregate coverage post-check (soft)

In addition to whatever the team configured in `verify.config.json`, automatically run an aggregate coverage check at `run_when: "before_complete"` if `state.testing.target_pct` is set and at least one unit has a `tests.coverage` block.

1. Pick the runner-wide coverage command from `state.testing` (mirror the per-unit commands in `agents/unit-migrator-subagent.md` step 7c, but without `target_paths` scoping — measure the whole project):

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
  parity:    <clean | <I> info | <A> acknowledged | BLOCKED: <N> high-severity | skipped | review-unavailable>
  quality:   <clean | <B> blocker · <H> high · <M> medium · <N> nit | skipped | review-unavailable>   (advisory; incl. static perf)
  dynamic:   <clean | <H> high · <M> medium · <L> low | not-run | skipped | unavailable>   (advisory; only with --dynamic)
  → <verified | still-migrated, see notes/<unit.id>.md>
```

(Omit the `dynamic:` line entirely when `--dynamic` was not passed.)

When parity **blocked** the transition, follow the per-unit line with the offending findings so the user can act without opening the JSON:

```
  ⚠ Parity blocked verified — <N> high-severity difference(s):
    [<finding-id>] <kind>
       legacy:   <legacy behaviour>
       migrated: <migrated behaviour>
       fix:      <recommendation>            (file: <file>)
    ...
  To resolve: fix the code and re-run /web-modernize:verify <unit.id>,
  or if the change is intentional: /web-modernize:parity-check <unit.id>  (acknowledge it), then re-verify.
```

When the migration-quality review returned `blocker`/`high` findings, list them as **advisory** — they did NOT affect the verified decision:

```
  ℹ Migration-quality (advisory — did not block verified):
    [<finding-id>] <kind> · <severity>
       <observation>
       fix: <suggestion>            (file: <file>)
    ...
  Headline: <quality_headline>
  Re-review any time with /web-modernize:quality-check <unit.id>.
```

All-units mode output: per-unit lines plus a summary:

```
Summary: <verified count>/<migrated count> passed.

  Failed:
    <unit.id>: <one-line reason>

Next: address failures, then re-run /web-modernize:verify <unit.id>.
   Or: /web-modernize:next  to migrate more units.
```

## Capture baseline (`--capture-baseline`)

Phase-A API replay needs a recording of the **legacy** app's responses to diff against. When invoked with `--capture-baseline`, do NOT verify units — instead:

1. Require `verify.config.json.dynamic.enabled == true`; require a way to run the legacy app and a request set. If the legacy app isn't runnable in this environment, print guidance (how to record fixtures by hand into `baseline_dir`) and stop — never fabricate a baseline.
2. Run the configured capture command (the `api_replay` harness in its record mode, or a documented per-stack recorder from the framework's `## Dynamic tests` section), exercising the legacy endpoints (sourced from `analysis.json.entry_points` / migrated units' `source_paths`).
3. Write the recorded request/response fixtures into `verify.config.json.dynamic.baseline_dir` (gitignored under `.claude/modernize/`). Print a summary: `<N> legacy endpoints recorded to <baseline_dir>. Run /web-modernize:verify --dynamic to replay against the new API.`

Baseline capture is a prerequisite for Phase A only; Phase B (E2E) does not need it.

## State transitions

- Pre: `state.status` ≥ `scaffolded`
- Post: top-level unaffected unless this was the last verification → `complete`
- Per-unit file: `migrated` → `verified` (on pass) or unchanged. The `migrated → verified` flip is gated on BOTH the lint/typecheck/test thresholds AND the behavioural-parity check (no unacknowledged high-severity findings), unless `--no-parity` is passed. The migration-quality review (step 5b) is **advisory and never affects this transition** — it only writes `quality_findings` and prints them as info.
