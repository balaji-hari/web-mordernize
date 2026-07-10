---
description: "Migrate up to K independent pending units in parallel via the Workflow tool. Use when state.status is 'foundation_done' or 'in_progress'. Triggers: 'migrate a batch', 'next batch', 'parallel migrate', 'do 3 at once', 'speed this up', 'migrate several units'."
disable-model-invocation: false
---

# `/web-modernize:next-batch [--n=K]`

You are the **next-batch** skill. You migrate up to `K` independent pending units **in parallel**, instead of one at a time like `/web-modernize:next`. Same translation work, same shared procedure (`${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator-caller.md` + `${CLAUDE_PLUGIN_ROOT}/agents/unit-migrator-subagent.md`) — this skill only adds batch selection and fan-out.

**This command always skips the per-unit plan-approval gate**, regardless of `state.review_mode`. Reviewing K plans from K parallel agents at once isn't a workable human-in-the-loop UX, so every unit in a batch runs `unit-migrator` Part B in `call_mode: "full"` directly — design and execute in one pass, no pause. State this to the user **before** running, every time:

```
ℹ /next-batch always skips the per-unit plan-review gate — batching and per-unit review don't compose.
  Use /web-modernize:next one at a time if you want to review each unit's plan before it writes.
```

## Plugin-version skew check

Same check as `/web-modernize:next`: compare `state.json.plugin_version` to the running plugin version; warn (don't refuse) on a major/minor mismatch; update `state.plugin_version` on successful exit.

## Preflight

0. Parse `$ARGUMENTS` for `--n=K` (default `3`). Clamp `K` to `[1, 8]` — 8 mirrors the per-round worker cap `workflows/analyze-discovery.js` already uses, as a sane ceiling on parallel token spend.
1. Read `.claude/modernize/state.json`. Require `status` to be one of `foundation_done`, `in_progress`, or `complete` (same redirect/recap behaviour as `/next`).
2. Read `migration.md` and `.claude/modernize/plan.md`.

## Select up to K independent units

Iterate `state.unit_ids[]` in order (already `phase asc, list_index asc`). A unit is a **candidate** under the same rule as `/next`'s selection (status `pending`, every `depends_on` entry satisfied). Build the batch by walking candidates in order and adding one if it does **not** conflict with any unit already in the batch:

- **No shared `depends_on`** with another batch member (picking two units that depend on each other's sibling work in-flight is asking for trouble even though neither depends on the other directly — skip the lower-priority one if `depends_on` sets overlap by more than `__auth__`/foundation tokens).
- **No overlapping `source_paths` directories** with another batch member — a best-effort proxy for target-path collision, since target paths aren't known before migration. Two units whose `source_paths` live under the same legacy directory are likely to extract the same shared helper or touch the same chrome/layout file; keep them out of the same batch.

Stop once the batch reaches `K` or candidates run out. If the batch ends up with **zero** units, report exactly what `/next` would (blocked-chain analysis, or congratulations + flip to `complete` if everything is done) and stop — there is nothing to batch.

If the batch has **fewer than `K`** units (not enough independent candidates), proceed with what you found and say so: `ℹ Only <N> independent unit(s) available (asked for <K>) — migrating <N>.`

## Acquire every selected unit — sequentially, before any subagent launches

For **each** unit in the batch, in order, run `agents/unit-migrator-caller.md` §A1 (collision handling — should be a no-op for a freshly-selected `pending` unit, but run it anyway in case another developer raced you) and §A2 (acquisition: write `status: "in_progress"` + `in_flight`), and §A4 (resolve any unresolved `state.open_decisions[]` affecting this unit, asking the user inline if needed). Do this **sequentially across units**, not in parallel — these are cheap, no-subagent steps, and sequencing them keeps `state.json` writes (the one-time `foundation_done → in_progress` flip, any `open_decisions` resolution) conflict-free. If a unit fails its collision check (e.g. another developer just claimed it), drop it from the batch and continue with the rest.

If acquisition drops every unit from the batch, report that and stop.

## Run the batch

### Method A — parallel (preferred when the Workflow tool is available)

This skill's invocation authorizes the Workflow tool. If available, invoke `${CLAUDE_PLUGIN_ROOT}/workflows/next-batch.js` with:

```json
{
  "units": [{ "unit": "<acquired unit object>", "mode": "next", "force_deps": false, "retry_prompt": null, "resolvedDecisions": { } }],
  "targetStack": "<state.target_stack>",
  "sourceDir": "."
}
```

It fans out one `unit-migrator` (`call_mode: "full"`) subagent **per unit, in parallel**, each writing only its own target/test/E2E files and `notes/<unit.id>.md`, returning the `call_mode: "full"` result shape (§B8 of `agents/unit-migrator-subagent.md`) — never touching `units/<id>.json`. Tell the user the batch size before launching. Surface its `log()` lines.

### Method B — sequential fallback

If the Workflow tool is unavailable, loop over the acquired units one at a time, launching `unit-migrator` Part B (`call_mode: "full"`) via the `Agent` tool exactly as Method A's prompt does, one unit at a time. Same per-unit result shape; just no wall-clock parallelism.

## Finalize every unit

For each `(unit, result)` pair returned, apply `agents/unit-migrator-caller.md` §A7's logic exactly as `/next` does: on `final_status: "migrated"`, write `status`, `target_paths`, `in_flight: null`, `smoke`, `tests`, `e2e`/`routes`/`extracted_shared` (omit absent ones), append history; on `final_status: "failed"`, write `status: "failed"`, `in_flight: null`, `failure`, append history. Do this for **all** units in the batch even if some failed — one unit's failure doesn't block writing the others' results.

## Closing message

```
Batch complete (<K_requested> requested, <N_attempted> attempted):
  ✓ Migrated:  <unit.id>, <unit.id>, ...
  ✗ Failed:    <unit.id> (see diagnostic below), ...

<for each failed unit, print its diagnostic + the standard /retry, /rollback, /abandon recovery banner>

Suggested next steps:
  1. Review the diff: git diff --stat
  2. Run /web-modernize:verify --all  (or verify each migrated unit individually)
  3. Commit when satisfied.
  4. /web-modernize:next-batch again, or /web-modernize:next for single-unit review.
```

## State transitions

- Pre: `state.status` ∈ {`foundation_done`, `in_progress`}
- Post: top-level `state.status` = `in_progress` (or `complete` if the batch finished the last pending units)
- Per-unit file (each batch member, independently): `pending` → `in_progress` → `migrated` (or `failed`)
