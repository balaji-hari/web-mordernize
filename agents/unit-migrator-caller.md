---
description: >
  Caller-side procedure for porting one unit from legacy source to the
  target stack — run inline by /web-modernize:next, /migrate, and /retry.
  Handles in-flight collision resolution, unit acquisition, the plan gate,
  and finalization; launches the unit-migrator subagent for the translation
  body.
disable-model-invocation: true
model: inherit
---

# `unit-migrator-caller` — caller-side per-unit migration procedure

You are the calling skill (`/next`, `/migrate`, or `/retry`), running inline in the main conversation. Run this procedure yourself, directly — it is written for you, not for a subagent. It tells you exactly how and when to launch the sibling `agents/unit-migrator-subagent.md` via the `Agent` tool, and what to do with what it returns.

The calling skill has already done these things before reaching this section:

- **Picked a unit** to migrate (referred to below as `unit`), read from `.claude/modernize/units/<unit.id>.json`.
- **Read** `state.json`, `migration.md`, `.claude/modernize/plan.md`.
- **Verified** the top-level workflow status is one of `foundation_done` / `in_progress`.
- **Resolved `SOURCE_ROOT`** per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/source-root-resolve.md` — this is what A6 passes to the subagent as `source_root`.

It also has a **mode** and optional inputs, exactly as before:

| Mode | Set by | Meaning |
|------|--------|---------|
| `next` | `/web-modernize:next` | Auto-selected the next eligible pending unit. Caller has already verified deps are met. |
| `migrate` | `/web-modernize:migrate` | User named the unit explicitly. By default, caller blocks on unmet deps and never reaches this file. With `--force`, caller sets `force_deps=true`. |
| `retry` | `/web-modernize:retry` | Unit was `failed`; re-attempting. `retry_prompt` may be set. |

- `retry_prompt` (retry mode only) — free-text override from `/web-modernize:retry --with-prompt="…"`. Pass it to the subagent as additional guidance layered on top of `migration.md`. Record it in `unit.last_retry_prompt` during acquisition (A2).
- `force_deps` (migrate mode only) — boolean. `true` means proceed despite unmet `depends_on`; the subagent stubs missing symbols with TODO comments. `false`/absent means the caller already verified deps are satisfied.
- `plan_override` (all modes) — `"on"`, `"off"`, or `null`/absent. The caller parses a per-invocation `--plan` (→ `"on"`) / `--no-plan` (→ `"off"`) flag. Resolved against `state.review_mode` at A3.

## A1. In-flight collision handling

Run this whenever `unit.status == "in_progress"`. Skip if `pending`/`failed`/etc.

Determine current user identity (`git config user.email`, fall back to hostname) and current host (`hostname`).

### Case A — you are the holder, heartbeat fresh

`unit.in_flight.by == <current user>` AND `last_heartbeat` is < 15 min old.

Print:

```
Resuming <unit.id> — you started it <N> min ago at step "<in_flight.current_step>".
Files touched so far: <count> (<list first 3>).
```

A Case-A resume always goes straight to **A6 in `call_mode: "full"`** — re-deriving and re-presenting a plan for a unit you already started isn't useful, and there is no pending approval to honor from a prior session (if there had been, the unit would have gone back to `pending` on cancel, not stayed `in_progress`). The subagent re-reads `in_flight.files_touched_so_far[]` plus all `source_paths` and skips re-writing files that are already present and unchanged — this is the accepted best-effort form of mid-unit resume (see the note at the end of A2).

### Case B — different user, heartbeat fresh

Print:

```
WARNING: <in_flight.by> on <in_flight.host> is currently migrating <unit.id>.
  Heartbeat last bumped <N> min ago — they may be actively working.

  Options:
    [w] Wait and check status later
    [o] Override (take over). They may lose work if they push first.
    [d] Pick a different unit instead.
```

Default to `w` on unclear input. On `o`, treat the in-flight block as stale and proceed to A2 (overwrite). On `d`, this unit is skipped — return to the caller's own unit-selection step. On `w`, stop here entirely (nothing launched).

### Case C — stale heartbeat (>15 min) or missing heartbeat block

Print:

```
A previously in-flight unit <unit.id> appears stalled (last heartbeat <N> min ago, started by <in_flight.by>).

  [r] Reclaim and resume
  [s] Skip — leave as in_progress, return to caller
  [a] Abort — reset to pending so it can be re-picked from scratch
```

On `r`: treat as Case A (you become the new holder; bump `last_heartbeat`). On `a`: reset `unit.status = "pending"`, clear `in_flight`, append history `{from: "in_progress", to: "pending", reason: "stalled-recovery"}`, save `.claude/modernize/units/<unit.id>.json`, stop here. On `s`: stop here, unit stays `in_progress`.

## A2. Acquire the unit

Only run this if you are starting fresh (not a Case A resume).

For `retry` mode, the unit's pre-retry status is `failed`. Before acquiring:

1. Move the existing `failure.diagnostic` (if any) into `failure.diagnostic_history[]` as `{ at: <unit's last history entry's at, or now>, diagnostic: <existing diagnostic>, retry_count: <current retry_count> }`.
2. Increment `unit.retry_count` by 1.
3. If `retry_prompt` was passed, set `unit.last_retry_prompt = <retry_prompt>`. Otherwise leave it as it was.
4. Clear `unit.failure.diagnostic` and `unit.failure.branch` (the old branch is preserved in `diagnostic_history`).

Then for all modes, update `unit`:

```json
{
  "status": "in_progress",
  "history": [...existing, {
    "at": "<now>", "by": "<user>", "from": "<previous status>", "to": "in_progress", "session_id": "<sid>"
  }],
  "in_flight": {
    "started_at": "<now>",
    "by": "<user>",
    "host": "<hostname>",
    "session_id": "<sid>",
    "last_heartbeat": "<now>",
    "current_step": "reading source",
    "files_touched_so_far": []
  }
}
```

**Save the per-unit file immediately**: write the mutated unit object back to `.claude/modernize/units/<unit.id>.json`. This is what concurrent `/web-modernize:status` and the heartbeat hook read.

If top-level `state.status` is `foundation_done` (i.e., this is the first feature unit), also flip it to `in_progress` and save `state.json`. This is the only top-level mutation this procedure makes during normal operation.

**Note on `in_flight` going forward:** the subagent (`agents/unit-migrator-subagent.md`) never writes `units/<unit.id>.json` — it returns data instead (see its frontmatter note and §B8). So unlike before, `in_flight.current_step` and `files_touched_so_far` go **static** after this acquisition write — nothing updates them again until A7 writes the terminal record. This is an accepted trade-off of the subagent conversion: a literal mid-function resume point is no longer possible; resume is best-effort (re-read `files_touched_so_far` + whatever already exists on disk, skip re-writing the unchanged parts).

## A3. Resolve the plan gate

Decide whether this unit is **gated** (a plan is presented and approval is required before any file is written) using `plan_override` and `state.review_mode` (read from `state.json`; treat absent/null as `"plan-first"`):

- `plan_override == "on"` → **gated** (force the gate even if `review_mode == "auto"`).
- `plan_override == "off"` → **not gated** (skip the gate even if `review_mode == "plan-first"`).
- `plan_override` absent/null → **gated** when `review_mode != "auto"`; **not gated** when `review_mode == "auto"`.

## A4. Resolve unresolved open architectural decisions — always, before launching anything

`/web-modernize:plan` records cross-cutting architectural decisions the team must make (e.g. one responsive layout vs. a separate mobile component tree, state-management approach, routing strategy) in `state.open_decisions[]` — each `{ id, question, status, decision, affects }`. Check whether any **unresolved** decision (`status != "resolved"`) materially affects this unit (by id, kind, or area in `affects[]`).

If one does: ask the user that single question now, inline — **always**, regardless of whether the unit is gated. (This is simpler than the old split where a gated unit folded the question into the plan-gate presentation and an ungated unit asked separately — a subagent can't pause to ask either way, so the question now lives entirely here, once, upfront.) Record the resolution back into `state.open_decisions[]` (`status: "resolved"`, `decision: <choice>`, `resolved_by`, `resolved_at`) and save `state.json`, so it is decided **once** for the whole migration, not re-litigated per unit. A decision already resolved (by the user or by `/plan`) is authoritative — pass it to the subagent without re-asking.

Pass any decisions resolved here (or already resolved) that affect this unit into the subagent's input context at A6. The subagent never asks this question itself — it applies whatever is already resolved.

## A5. Heartbeat touch-up before a long subagent call

A `call_mode: "plan_only"` call makes **zero** `Write`/`Edit` calls (it is read-only by instruction), and the human may take a while to respond to the plan it returns. The heartbeat hook only fires on `Write`/`Edit`, so `in_flight.last_heartbeat` never refreshes during that whole window otherwise. **Before presenting a plan to the user, and again right before launching any `call_mode: "full"` call** (whether gated-after-approval, gated-after-revise, or ungated), bump `unit.in_flight.last_heartbeat = <now>` yourself and save the per-unit file. This is a small, deliberate write that prevents a unit actively being planned or awaiting approval from looking stalled to a concurrent `/web-modernize:status` check.

## A6. Launch the subagent

Every launch below (gated or not) includes `source_root` — the value resolved by this skill per `skills/_shared/source-root-resolve.md` (may be `null`) — alongside `unit`/`mode`/etc., so the subagent knows where to resolve `source_paths[]` against; see the subagent's §B1 step 1.

**If not gated:** launch `agents/unit-migrator-subagent.md` once via the `Agent` tool (`subagent_type: unit-migrator`). Prompt states `call_mode: "full"`, plus `unit`, `mode`, `force_deps`, `retry_prompt`, `source_root`, and any open-decisions resolution from A4. Go to A7 when it returns.

**If gated:**

1. Launch the subagent with `call_mode: "plan_only"` (same inputs as above, minus `force_deps` — nothing is executed yet). It returns either a `plan` object, or a `blocked` result if it hit a stop condition while just trying to design one (go straight to A7's failure handling in that case — there is no plan to present).
2. Present the returned plan (it already matches this shape) and ask:

   ```
   Plan gate — <unit.id>  (review_mode: <plan-first|auto>; <how it was set: default | migration.md | --plan/--no-plan>)

   Target files to create:
     - <path>  — <one-line purpose>
     ...
   Approach & key decisions:
     - <e.g. ViewState → useReducer; <asp:GridView> → TanStack Table; cookie session reused>
   Tests to write:
     - <translated from <legacy test> | generated for <behaviour>>
     - <for a UI unit with dynamic testing enabled: the Playwright E2E spec `e2e/<unit.id>.spec.ts` covering routes <…>>
   Dependencies relied on: <dep ids, or "none beyond __auth__">
   Open questions / risks: <ambiguities resolved and how, or "none">

   Proceed?  [a] approve and write   [r] revise (give feedback)   [c] cancel (don't migrate)
   ```

   In **retry** mode, the plan already folds `retry_prompt` into "Approach & key decisions" / "Open questions" (the subagent does this when it builds the plan) so the user sees how their guidance shaped it. Default to `[c]` on unclear input — never write on ambiguity.

3. **`[a]` approve** → run the A5 heartbeat touch-up, then launch the subagent **again** — a fresh, independent call, `call_mode: "full"`, including the exact **approved `plan`** object from step 1 plus `unit`/`mode`/`force_deps`/`retry_prompt`/open-decisions as before. The subagent treats the approved plan as already-decided: it does not re-derive target layout or approach, but it does re-read the source files (a single, bounded re-read — this is a fresh call with no prior context) because it needs their actual content to write the translation, not just the plan's summary of it.
4. **`[r]` revise** → relaunch `call_mode: "plan_only"` — a new, independent call, not a continuation — with the user's feedback appended to the prompt (treated exactly like `retry_prompt`: it biases every design decision). Loop back to step 2 with whatever new plan comes back.
5. **`[c]` cancel** → launch nothing further. Go directly to A7's cancel handling.

## A7. After the subagent returns (or on cancel): finalize the unit record

This is the **only** place `units/<unit.id>.json`'s terminal fields get written (besides A1/A2's interim writes). The subagent itself never writes this file.

- **Cancel** (A6 step 5): write `status = "pending"`, `in_flight = null`, append history `{from: "in_progress", to: "pending", reason: "cancelled at plan gate"}`. Save. Report to the caller: not migrated (cancelled at plan gate), nothing was written, the unit can be re-run later (optionally with `--no-plan`).
- **`plan_only` returned `status: "blocked"`** (a stop condition hit while just trying to plan): handle identically to a `full`-mode failure below, using the returned `diagnostic`.
- **`full` mode returned `final_status: "migrated"`**: write `status`, `target_paths`, `in_flight: null`, `smoke`, `tests`, `e2e` (omit if absent), `routes` (omit if absent), and `extracted_shared` (**append**, don't overwrite, any new entries the subagent reported) — every field name maps 1:1 onto `unit.schema.json`. Append history `{at, by, from: "in_progress", to: "migrated", session_id}`. Update `state.json.updated_at`. If the returned result included a coverage `below_threshold: true`, print the existing yellow soft-fail warning.
- **`full` mode returned `final_status: "failed"`**: write `status = "failed"`, `in_flight: null`, `failure: { diagnostic, branch, diagnostic_history: <existing, unchanged> }`. Append history. Print the diagnostic plus the existing recovery-options banner (`/retry`, `/rollback`, `/abandon`) — identical wording to before.

The caller (`/next`/`/migrate`/`/retry`) then prints its own mode-specific closing message exactly as it always has — that part is unchanged by this conversion.
