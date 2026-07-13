---
description: "Compare a migrated unit's behaviour against the legacy original and report differences (validation, output shape, sort order, error handling, UI states), or acknowledge a difference as intentional. Use when a unit is in 'migrated' or 'verified' status. Triggers: 'check parity', 'behavioural diff', 'does it behave like the old one', 'parity check', 'acknowledge parity', 'compare to legacy'."
disable-model-invocation: false
---

# `/web-modernize:parity-check <unit-id> [--all] [--acknowledge <finding-id> --reason "…"]`

You are the **parity-check** skill. You run the behavioural-parity comparison on demand (the same check `/web-modernize:verify` runs as a gate) and let the team **acknowledge** a difference as intentional so it stops blocking verification.

The comparison itself is delegated to `${CLAUDE_PLUGIN_ROOT}/agents/parity-reviewer.md` (a read-only subagent). This skill handles unit selection, persistence of findings, the human-readable report, and the acknowledge mutation.

## Plugin-version skew check

Read `${CLAUDE_PLUGIN_ROOT}/skills/_shared/plugin-version-check.md` and perform the check it describes before proceeding.

## Preflight

1. Read `.claude/modernize/state.json`. Require `status >= "scaffolded"` (target project must exist). If earlier, redirect to the missing skill.
2. Parse `$ARGUMENTS`:
   - `--all` → review every unit currently in status `migrated` or `verified`.
   - `--acknowledge <finding-id>` (with optional `--reason "…"`) → **acknowledge mode** (see below); requires a `<unit-id>`.
   - First non-flag token → `<unit-id>`.
   - If neither `<unit-id>` nor `--all` is present, print usage and stop:
     ```
     Usage: /web-modernize:parity-check <unit-id> [--all] [--acknowledge <finding-id> --reason "…"]

     Examples:
       /web-modernize:parity-check OrderListPage
       /web-modernize:parity-check --all
       /web-modernize:parity-check OrderListPage --acknowledge output_sort_order:OrderListPage:orderdate-desc-to-asc --reason "Product asked for newest-last"

     To see available units: /web-modernize:status
     ```
3. For a named `<unit-id>`, read `.claude/modernize/units/<unit-id>.json`. If missing, list valid ids (`ls .claude/modernize/units/*.json`) and stop.
4. **Resolve `SOURCE_ROOT`** (review mode only — acknowledge mode doesn't need it): follow `${CLAUDE_PLUGIN_ROOT}/skills/_shared/source-root-resolve.md`.

Determine **current user identity**: `git config user.email`, falling back to hostname or `"unknown"`.

---

## Acknowledge mode (`--acknowledge <finding-id>`)

Use this to record that a flagged difference is intentional, so it no longer blocks `/web-modernize:verify`.

1. Read `units/<unit-id>.json`. Confirm a finding with `id == <finding-id>` exists in `unit.parity_findings[]`. If not, print the available finding ids for that unit and stop (likely a stale id — re-run a review first).
2. Require a reason. If `--reason` was omitted, ask the user: *"Why is this difference intentional/acceptable?"* and use their answer.
3. Append to `unit.parity_acknowledged_diffs[]` (de-dupe by `id` — replace any existing entry for the same id):
   ```json
   { "id": "<finding-id>", "by": "<user>", "at": "<now>", "reason": "<reason>" }
   ```
4. Append a history entry `{ "at": "<now>", "by": "<user>", "from": "<status>", "to": "<status>", "session_id": "…" }` noting the acknowledgement in a `reason`-style note (status itself is unchanged).
5. Save `units/<unit-id>.json`. Print:
   ```
   ✓ Acknowledged parity difference [<finding-id>] on <unit-id>.
     Reason: <reason>
     It will no longer block /web-modernize:verify. Re-run /web-modernize:verify <unit-id> to flip to verified.
   ```
Stop here — do not re-run the reviewer in acknowledge mode.

---

## Review mode (default, or `--all`)

For each target unit (`<unit-id>`, or every `migrated`/`verified` unit under `--all`):

1. **Status check.** The unit must be `migrated` or `verified` (it needs `target_paths` to compare). For any other status, skip it with a one-line note:
   - `pending` / `in_progress` → "not migrated yet — nothing to compare."
   - `failed` → "migration failed — fix/retry before checking parity."
   - `skipped` / `blocked` → "unit is <status>."

2. **Launch the `parity-reviewer` subagent** (Agent tool, `subagent_type: parity-reviewer`). Pass a prompt containing the unit's `id`, `kind`, `source_paths[]`, `source_root` (the resolved `SOURCE_ROOT` from Preflight step 4 — `null` in the common same-repo case), `target_paths[]`, the `notes_path` (`.claude/modernize/notes/<unit-id>.md`), and the relevant `migration.md §10` acceptance-criteria lines. It returns a single JSON block: `{ parity_findings[], summary, warnings }`.

3. **Graceful degrade.** If the agent errors or returns malformed JSON, print a one-line warning and move on (don't mutate the unit). Never crash the skill on a bad agent run.

4. **Persist.** Write the returned array to `unit.parity_findings` (replace wholesale), set `unit.parity_reviewed_at = <now>`, and **leave `unit.parity_acknowledged_diffs[]` untouched**. Save `units/<unit-id>.json`. (Reviewing does NOT change `status` — it only refreshes findings. A `verified` unit stays `verified`; if a fresh high-severity finding appears, the user re-runs `/verify` to re-evaluate the gate, or acknowledges it.)

5. **Report.** Print, grouping by severity (high → medium → low), marking any finding whose `id` is already in `parity_acknowledged_diffs[]` as `(acknowledged)`:
   ```
   parity-check <unit-id>:  <H> high · <M> medium · <L> low   (reviewed against <count> source / <count> target files)

     HIGH
       [<finding-id>] <kind>            <(acknowledged) if applicable>
          legacy:   <legacy behaviour>
          migrated: <migrated behaviour>
          fix:      <recommendation>            (file: <file>)
     MEDIUM
       ...
     LOW
       ...

     warnings: <each warning line, if any>
   ```
   If `parity_findings[]` is empty: `parity-check <unit-id>:  ✓ no behavioural differences found — behaves like the legacy original.`

6. **Offer to acknowledge** (single-unit review only; skip the interactive prompt under `--all` to avoid a prompt storm — tell the user to acknowledge per-unit). If there are **unacknowledged high-severity** findings, ask the user which (if any) are intentional. For each one they confirm, run the acknowledge-mode mutation (append to `parity_acknowledged_diffs[]` with their reason). Findings they don't acknowledge remain blocking.

## Closing message

```
Parity reviewed for <unit-id> (or <N> units).
  <X> high-severity difference(s) still unacknowledged — these block /verify.

Suggested next steps:
  - Fix the code to restore legacy behaviour, then /web-modernize:verify <unit-id>
  - OR acknowledge any intentional difference:
      /web-modernize:parity-check <unit-id> --acknowledge <finding-id> --reason "…"
    then /web-modernize:verify <unit-id>
```

If there were no unacknowledged high-severity findings, say so plainly and suggest `/web-modernize:verify <unit-id>` (or `/web-modernize:next` if already verified).

## State transitions

- Pre: `state.status` ≥ `scaffolded`; the unit is `migrated` or `verified`.
- Post: top-level `state.status` unchanged. Per-unit `status` unchanged — this skill only writes `parity_findings`, `parity_reviewed_at`, and `parity_acknowledged_diffs`. The actual `migrated → verified` gate lives in `/web-modernize:verify`.
