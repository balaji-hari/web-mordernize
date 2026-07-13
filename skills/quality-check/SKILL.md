---
description: "Review a migrated unit's TARGET code for idiomatic quality — legacy-paradigm leakage (WebForms-in-React, jQuery-in-a-reactive-framework, scriptlet-shaped controllers), ceremonial error handling, dead abstractions, weak tests, on-call gaps, and static performance regressions (N+1, unbounded queries, waterfalls, blocking I/O, bundle bloat). Advisory only — never blocks verification. Use when a unit is in 'migrated' or 'verified' status. Triggers: 'quality check', 'is this idiomatic', 'code quality', 'performance review', 'review the migration quality', 'is this good code', 'check for jobol'."
disable-model-invocation: false
---

# `/web-modernize:quality-check <unit-id> [--all]`

You are the **quality-check** skill. You run the migration-quality review on demand — the same review `/web-modernize:verify` runs as an advisory pass — without the lint/typecheck/test cycle, so a developer can iterate on code quality between migrations.

The review itself is delegated to `${CLAUDE_PLUGIN_ROOT}/agents/migration-critic.md` (a read-only subagent). This skill handles unit selection, persistence of findings, and the human-readable report.

**This is advisory.** Unlike `/web-modernize:parity-check`, there is no acknowledge step and nothing to gate: quality findings never block the `migrated → verified` transition (that gate depends only on lint/typecheck/tests + behavioural parity). Quality findings exist to inform a maintainer, not to stop the workflow. It is orthogonal to parity — parity asks *did behaviour change?*, quality asks *is the code idiomatic and maintainable?*

## Plugin-version skew check

Read `${CLAUDE_PLUGIN_ROOT}/skills/_shared/plugin-version-check.md` and perform the check it describes before proceeding.

## Preflight

1. Read `.claude/modernize/state.json`. Require `status >= "scaffolded"` (target project must exist). If earlier, redirect to the missing skill.
2. Parse `$ARGUMENTS`:
   - `--all` → review every unit currently in status `migrated` or `verified`.
   - First non-flag token → `<unit-id>`.
   - If neither `<unit-id>` nor `--all` is present, print usage and stop:
     ```
     Usage: /web-modernize:quality-check <unit-id> [--all]

     Examples:
       /web-modernize:quality-check OrderListPage
       /web-modernize:quality-check --all

     To see available units: /web-modernize:status
     ```
3. For a named `<unit-id>`, read `.claude/modernize/units/<unit-id>.json`. If missing, list valid ids (`ls .claude/modernize/units/*.json`) and stop.
4. **Resolve `SOURCE_ROOT`**: follow `${CLAUDE_PLUGIN_ROOT}/skills/_shared/source-root-resolve.md`.

Determine **current user identity**: `git config user.email`, falling back to hostname or `"unknown"`.

## Review

For each target unit (`<unit-id>`, or every `migrated`/`verified` unit under `--all`):

1. **Status check.** The unit must be `migrated` or `verified` (it needs `target_paths` to review). For any other status, skip it with a one-line note:
   - `pending` / `in_progress` → "not migrated yet — nothing to review."
   - `failed` → "migration failed — fix/retry before a quality review."
   - `skipped` / `blocked` → "unit is <status>."

2. **Launch the `migration-critic` subagent** (Agent tool, `subagent_type: migration-critic`). Pass a prompt containing the unit's `id`, `kind`, `target_paths[]`, `source_paths[]`, `source_root` (the resolved `SOURCE_ROOT` from Preflight step 4 — `null` in the common same-repo case), the `notes_path` (`.claude/modernize/notes/<unit-id>.md`), and `state.target_stack` (so it judges against the right idiom). It returns a single JSON block: `{ quality_findings[], headline, summary, warnings }`.

3. **Graceful degrade.** If the agent errors or returns malformed JSON, print a one-line warning and move on (don't mutate the unit). Never crash the skill on a bad agent run.

4. **Persist.** Write the returned array to `unit.quality_findings` (replace wholesale), set `unit.quality_reviewed_at = <now>` and `unit.quality_headline = <returned headline>`. Save `units/<unit-id>.json`. Reviewing does NOT change `status` — a `migrated` unit stays `migrated`, a `verified` unit stays `verified`. (There is no acknowledge list: quality findings don't block, so there is nothing to suppress.)

5. **Report.** Print, grouping by severity (blocker → high → medium → nit):
   ```
   quality-check <unit-id>:  <B> blocker · <H> high · <M> medium · <N> nit   (reviewed <count> target files, advisory)

     BLOCKER
       [<finding-id>] <kind>
          <observation>
          why:  <why_it_matters>
          fix:  <suggestion>            (file: <file>)
     HIGH
       ...
     MEDIUM
       ...
     NIT
       ...

     Headline: <quality_headline>
     warnings: <each warning line, if any>
   ```
   If `quality_findings[]` is empty: `quality-check <unit-id>:  ✓ idiomatic for the target stack — no quality findings.` (still print the headline if the critic returned an affirmation).

## Closing message

```
Quality reviewed for <unit-id> (or <N> units) — advisory, nothing blocked.
  <B> blocker · <H> high finding(s) worth addressing before this unit is considered done.

Suggested next steps:
  - Address the blocker/high findings, then re-run /web-modernize:quality-check <unit-id> to confirm they cleared.
  - These never block verification — /web-modernize:verify proceeds on lint/typecheck/tests + parity regardless.
```

If there were no blocker/high findings, say so plainly (e.g. "Idiomatic — nothing pressing.") and suggest `/web-modernize:verify <unit-id>` (or `/web-modernize:next` if already verified).

## State transitions

- Pre: `state.status` ≥ `scaffolded`; the unit is `migrated` or `verified`.
- Post: top-level `state.status` unchanged. Per-unit `status` unchanged — this skill only writes `quality_findings`, `quality_reviewed_at`, and `quality_headline`. There is no gate here; the advisory copy of this review also runs inside `/web-modernize:verify` (step 5b).
