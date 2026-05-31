---
description: "Generate a stakeholder progress/velocity/risk report (md/json/html). Use when state.status is 'in_progress' or 'complete'. Triggers: 'generate a report', 'stakeholder update', 'progress report', 'export progress', 'exec summary', 'report for leadership'."
disable-model-invocation: false
---

# `/web-modernize:report [--format=html|json|md] [--filter=phase|effort|owner]`

You are the **report** skill. You produce a human-readable digest of the migration's current state. You are **read-only on state files** — do not modify them.

## Preflight

1. Read `.claude/modernize/state.json`. Required. If `status` is `uninitialized`, `initialized`, or `analyzed`, reply: "Reporting is not useful before /web-modernize:plan has run. Run /web-modernize:status for the early-stage dashboard." Stop.

2. Read `migration.md`. Required (for §1 project identity and §10 acceptance criteria).

3. Read `.claude/modernize/plan.md` if present (for phase names — fall back to `Phase <N>` if absent).

4. Iterate `state.unit_ids[]`. For each id, read `.claude/modernize/units/<id>.json`. Skip ids whose file is missing (and warn about them in the report footer). The result is the in-memory `units[]` array used by every metric below.

5. Parse `$ARGUMENTS`:
   - `--format=md` (default) | `--format=json` | `--format=html`
   - `--filter=phase` | `--filter=effort` | `--filter=owner` — narrows the burndown/ownership tables to that dimension. Omit for all dimensions.

6. Confirm the output directory exists: `.claude/modernize/reports/`. Create it if missing (this is a generated artifact directory — safe to add).

## Compute metrics

Aggregate the in-memory `units[]` collected in preflight step 4.

### Counts by status

```
total           = len(units)
count_migrated  = count(units, status == "migrated")
count_verified  = count(units, status == "verified")
count_in_flight = count(units, status == "in_progress")
count_pending   = count(units, status == "pending")
count_failed    = count(units, status == "failed")
count_blocked   = count(units, status == "blocked")
count_skipped   = count(units, status == "skipped")

percent_complete = round(100 * (count_migrated + count_verified) / max(1, total - count_skipped))
```

Skipped units do not count toward the denominator — they're explicitly out of scope.

### Burndown tables

**By phase**: group units by `unit.phase`. For each phase, count total / done (verified+migrated) / remaining (everything else except skipped). Percent done = round(100 * done / max(1, total - skipped)).

**By effort tier**: group by `unit.effort` (S / M / L / XL). Same shape.

### Velocity & ETA

Walk every unit's `history[]`. Find every entry where `to == "verified"`.

- `velocity_7d` = count of `→ verified` transitions in the last 7 days (relative to `<now>`).
- `velocity_30d` = same for last 30 days.
- `velocity_per_day` = velocity_7d / 7 (rounded to 2 decimals).
- `remaining_units` = total - count_verified - count_skipped.
- If `velocity_per_day > 0`:
  - `eta_days` = ceil(remaining_units / velocity_per_day).
  - `eta_date` = `<now>` + `eta_days` days (ISO date only).
  - `eta_variance` = ceil(eta_days * 0.25) — rough ±25% bound.
- If `velocity_per_day == 0`: set ETA fields to `"indeterminate"`.

### Risk heat-map

For each unit, compute a risk signal if any of these hold:

1. `retry_count >= 2`
2. `rollback_info != null`
3. `status == "failed"`
4. `status == "blocked"`
5. `depends_on` includes an id whose unit has been in some non-`{verified, migrated}` status for more than 7 days (compute from history: the most recent transition into that status's `at` timestamp).

Include any unit with at least one signal in the risk table. Format: `<unit.id> | <status> | <comma-separated signals>`. Sort by signal count desc, then by id asc.

### Ownership

Walk every unit's `history[]`. For each entry, attribute one "touch" to `entry.by`. Also attribute the current `in_flight.by` (if set) as the most-recent activity.

For each contributor:
- `units_worked_on` = count of distinct unit ids they appear in.
- `last_activity` = the most recent `at` across their history entries (or `now` if they have an active in-flight).

Sort contributors by units_worked_on desc.

### In flight, recent activity, blockers

- **In flight block**: for each unit with `status == "in_progress"`, render its `in_flight` block in the same format as `/web-modernize:status` §5 (id, started, by, host, current_step, heartbeat freshness).
- **Recent activity (last 10)**: across all units, collect history entries (carrying the unit id), sort by `at` desc, take top 10. Format: `<at>  <by>  <unit.id>: <from> → <to>`.
- **Blockers**: every unit with status `blocked` or `failed`. Format: `<status>: <unit.id> — <failure.diagnostic or "no diagnostic recorded">`. If none, say "No blockers."

### Acceptance criteria

Read `migration.md §10`. Render each `- [ ]` line verbatim, and `- [x]` lines too. This is the team's own checklist; do not interpret.

## Render the report

### Markdown format (default)

Read `${CLAUDE_PLUGIN_ROOT}/templates/report.md`. Substitute every `{{PLACEHOLDER}}` with the computed value. For table placeholders (`{{PHASE_TABLE}}`, `{{EFFORT_TABLE}}`, `{{RISK_TABLE}}`, `{{OWNERSHIP_TABLE}}`, `{{ACCEPTANCE_CRITERIA_BLOCK}}`), produce one Markdown table row per group. For block placeholders (`{{IN_FLIGHT_BLOCK}}`, `{{RECENT_ACTIVITY_BLOCK}}`, `{{BLOCKERS_BLOCK}}`), produce multi-line content (use a code fence if appropriate).

If `--filter=phase`: omit the effort and ownership sections.
If `--filter=effort`: omit the phase and ownership sections.
If `--filter=owner`: keep ownership, omit phase and effort.

Write to `.claude/modernize/reports/<YYYY-MM-DD>-status.md`. If a file with that name already exists, append a suffix: `-2`, `-3`, ... (do not overwrite).

### JSON format

Emit a single JSON document with the same data, no template. Shape:

```json
{
  "generated_at": "<ISO now>",
  "plugin_version": "<from state>",
  "project_name": "<from migration.md §1>",
  "workflow_status": "<state.status>",
  "source_stack": "<state.source_stack.primary>",
  "target_ui": "<state.target_stack.ui>",
  "strategy": "<state.strategy>",
  "counts": { "total": N, "migrated": N, "verified": N, "in_flight": N, "pending": N, "failed": N, "blocked": N, "skipped": N, "percent_complete": N },
  "by_phase": [ { "phase": N, "name": "<from plan.md or 'Phase N'>", "total": N, "done": N, "remaining": N, "percent_done": N } ],
  "by_effort": [ { "effort": "S|M|L|XL", "total": N, "done": N, "remaining": N } ],
  "velocity": { "verified_last_7d": N, "verified_last_30d": N, "per_day_7d": N, "eta_days": N, "eta_date": "YYYY-MM-DD", "eta_variance_days": N },
  "risk": [ { "unit_id": "...", "status": "...", "signals": ["..."] } ],
  "ownership": [ { "by": "...", "units_worked_on": N, "last_activity": "<ISO>" } ],
  "in_flight": [ ... ],
  "recent_activity": [ ... ],
  "blockers": [ { "status": "failed|blocked", "unit_id": "...", "diagnostic": "..." } ],
  "acceptance_criteria": [ { "line": "- [ ] ...", "checked": false } ]
}
```

Write to `.claude/modernize/reports/<YYYY-MM-DD>-status.json` (suffix on collision as above).

### HTML format

Generate a single-file HTML page with inline CSS. Match the Markdown layout but render tables as `<table>`. Use a sober colour palette (no marketing flair). Keep the file under 200 KB. Write to `.claude/modernize/reports/<YYYY-MM-DD>-status.html`.

For simplicity in this version, you can generate the Markdown first and convert with the same template structure, replacing pipe-tables with HTML tables. Skip JavaScript entirely — the page should render statically and be safe to paste into a wiki.

## Terminal output

After writing the file, print a one-screen summary to stdout:

```
✓ Report written to .claude/modernize/reports/<filename>

  Workflow phase: <state.status>     Completion: <percent>%
  Verified: <N> / <total - skipped>     In flight: <N>     Failed: <N>     Blocked: <N>

  ETA: <eta_date> (<eta_days> days, ±<variance> days)     7-day velocity: <X> units

  Top risks (<count> units flagged):
    - <unit.id> — <signals>
    - ...   (up to 3)

Share the file with stakeholders, or commit it to keep a snapshot history.
```

Do not modify state files.

## What report does NOT do

- Does not push, share, or upload the report anywhere. Output stays on disk.
- Does not "predict the future" beyond linear extrapolation of recent velocity. If the team's burndown shape is non-linear, the ETA is wrong.
- Does not compute a confidence score on the ETA. The `±variance` is a flat 25% — for serious capacity planning, the team should overlay their own sprint commitments.
- Does not analyze code coverage, performance, or accessibility. Those are `/web-modernize:audit` territory (deferred to a future release).

## State transitions

None. Report is read-only.

## Edge cases

- **No units in plan yet** (status is `planned` but `state.unit_ids` is empty): print "Plan is empty — nothing to report." and stop. Do not write a report file.
- **`state.unit_ids` references a missing `units/<id>.json` file** (corrupt state): skip the missing entries; add a warning to the report's footer listing every missing file.
- **All units verified** (migration complete): include a "Migration complete" banner at the top of the report and skip the burndown/ETA sections (replace with "Complete on <date>, took <N> days from plan").
- **History entries missing `at` field** (corrupt unit file): skip those entries in velocity calculation and add a warning to the report's footer.
- **`migration.md` missing or malformed**: render the report without §1 metadata and §10 acceptance-criteria blocks; substitute "(migration.md missing)" placeholders.
