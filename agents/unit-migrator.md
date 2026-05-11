---
name: unit-migrator
description: >
  Shared procedure for porting a single unit from legacy source to the target
  stack. Loaded inline by /web-modernize:next, /web-modernize:migrate, and
  /web-modernize:retry — they all do the same translation work, only the
  unit-selection step and the dep-policy flag differ. This file is the single
  source of truth for the migration loop; do not duplicate it elsewhere.

  NOTE: Despite living under agents/, this is NOT launched as a separate
  subagent (unlike legacy-analyzer). It is read inline by the calling skill
  so that file mutations, user prompts, and identity all stay in the same
  conversation.

  Storage convention (schema v3): each unit lives in its own file at
  .claude/modernize/units/<unit-id>.json. Top-level workflow status lives in
  .claude/modernize/state.json. Unit mutations always write the per-unit
  file; only top-level transitions touch state.json.
---

# `unit-migrator` — shared per-unit migration procedure

You are executing the unit-migration procedure. The calling skill has already done these things and is passing you the result:

- **Picked a unit** to migrate. The unit object is referred to below as `unit`. It was read from `.claude/modernize/units/<unit.id>.json`.
- **Read** `state.json`, `migration.md`, `.claude/modernize/plan.md`.
- **Verified** the top-level workflow status is one of `auth_done` / `in_progress`.

The calling skill also passes a **mode** and an optional **force_deps** flag:

| Mode | Set by | Meaning |
|------|--------|---------|
| `next` | `/web-modernize:next` | Auto-selected the next eligible pending unit. Caller has already verified deps are met. |
| `migrate` | `/web-modernize:migrate` | User named the unit explicitly. By default, caller blocks on unmet deps and never reaches this agent. With `--force`, caller sets `force_deps=true` and you may proceed with stubs. |
| `retry` | `/web-modernize:retry` | Unit was `failed`; we are re-attempting. `retry_prompt` may be set. |

Optional inputs:

- `retry_prompt` (retry mode only) — free-text override the user provided via `/web-modernize:retry --with-prompt="…"`. When set, treat it as **additional guidance** layered on top of `migration.md`. Record it in `unit.last_retry_prompt`.
- `force_deps` (migrate mode only) — boolean. When `true`, proceed even if `depends_on` is unsatisfied; stub the missing dep imports with TODO comments. When `false` or absent, the caller would have blocked already; assume deps are met.

## 1. In-flight collision handling

If `unit.status == "in_progress"`, run the three-case logic. Skip this section if the unit is `pending` / `failed` / etc.

Determine **current user identity** (`git config user.email`, fall back to hostname or "unknown") and **current host** (`hostname` or equivalent).

### Case A — you are the holder, heartbeat fresh

`unit.in_flight.by == <current user>` AND `last_heartbeat` is < 15 min old.

Print:

```
Resuming <unit.id> — you started it <N> min ago at step "<in_flight.current_step>".
Files touched so far: <count> (<list first 3>).
```

Re-read the files in `in_flight.files_touched_so_far[]` plus all `source_paths`. Resume from `in_flight.current_step`. Skip to §3 ("Migrate body").

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

Default to `w` on unclear input. On `o`, treat the in-flight block as stale (proceed to §2 and overwrite); on `d`, return control to the caller with an indication that this unit was skipped.

### Case C — stale heartbeat (>15 min) or missing heartbeat block

Print:

```
A previously in-flight unit <unit.id> appears stalled (last heartbeat <N> min ago, started by <in_flight.by>).

  [r] Reclaim and resume
  [s] Skip — leave as in_progress, return to caller
  [a] Abort — reset to pending so it can be re-picked from scratch
```

On `r`: treat as Case A (you become the new holder; bump `last_heartbeat`). On `a`: reset `unit.status = "pending"`, clear `in_flight`, append history `{from: "in_progress", to: "pending", reason: "stalled-recovery"}`, save `.claude/modernize/units/<unit.id>.json`, return to caller. On `s`: return to caller.

## 2. Acquire the unit

Only run this if you are starting fresh (not Case A resume).

For `retry` mode, the unit's pre-retry status is `failed`. Before acquiring:

1. Move the existing `failure.diagnostic` (if any) into `failure.diagnostic_history[]` as `{ at: <unit's last history entry's at, or now>, diagnostic: <existing diagnostic>, retry_count: <current retry_count> }`.
2. Increment `unit.retry_count` by 1.
3. If `retry_prompt` was passed, set `unit.last_retry_prompt = <retry_prompt>`. Otherwise leave it as it was.
4. Clear `unit.failure.diagnostic` and `unit.failure.branch` (the old branch is preserved in `diagnostic_history`; new attempt gets a new branch if applicable).

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

If top-level `state.status` is `auth_done` (i.e., this is the first feature unit), also flip it to `in_progress` and save `state.json`. This is the only top-level mutation this agent makes during normal operation.

## 3. Migrate body

This is the actual translation work.

### General algorithm

1. **Read all `source_paths`** in full, plus **every stylesheet they depend on** — sibling files in the same directory (`<source>.css`, `<source>.scss`, `<source>.less`), stylesheets referenced from the source markup via `<link rel="stylesheet">` or `@import`, and project-wide style files (`site.css`, `app.scss`, anything under `Content/`, `wwwroot/css/`, `src/main/webapp/resources/css/`, `assets/styles/`, etc.). The legacy visual design lives in those files; missing them produces "looks-nothing-like-the-original" output.
2. **Read related target context**: existing `target_paths[]` of migrated dependencies (read each dep's `units/<dep_id>.json` if you need their paths), the target framework's conventions, and any existing shared utilities under `apps/web-new/src/lib/` etc.
3. **Update `in_flight.current_step = "designing target structure"`** and save the per-unit file.
4. **Decide target file layout** based on `unit.kind` and `state.target_stack.ui`/`.api`:
   - React/Vue/Svelte component → `apps/web-new/src/features/<feature>/` or `apps/web-new/src/pages/`.
   - API endpoint → `apps/api-new/src/routes/<area>/<verb>.ts` or framework equivalent.
   - Shared utility → `apps/web-new/src/lib/`.
5. **Create a feature branch** (recommended): `git checkout -b modernize/<unit.id>` — only if git is clean and the team allows. For `retry` mode, prefer a fresh branch name (e.g., suffix with `-retry-<retry_count>`) to keep failed-attempt history reviewable.
6. **Write target files**. Update `in_flight.files_touched_so_far` and `current_step` as you go and save the per-unit file periodically; the heartbeat hook keeps `last_heartbeat` fresh on every Write tool call.
7. **Translate semantics, not syntax** (data and logic):
   - WebForms event handlers → React event handlers + useState/useReducer.
   - Server-side controls (`<asp:GridView>`) → modern data table component.
   - ViewState → component state or query string, depending on intent.
   - Server-side validators → client + server validation.
   - JSP scriptlets → typed view models + template logic.
   - AngularJS controllers → modern composables / hooks.

7b. **Translate visuals, not just logic — preserve the legacy design.** This is as important as step 7. The user expectation is "the new page looks like the old page", not a clean-room re-design. A migration that produces correct data and broken-looking pages is a half-done migration.

   - **Detect the legacy design system.** Scan the stylesheets you read in step 1 for class-name prefix patterns. If a custom prefix appears in more than three distinct class names, treat it as a load-bearing design system. Common signals:
     - `esh-*` (Microsoft eShop reference apps)
     - `app-*`, `acme-*` (custom in-house BEM)
     - `btn-`, `card-`, `form-` (Bootstrap-derived but customised — check the rules)
     - `mat-`, `mdc-` (Material Design)
     - Framework defaults like `ng-`, `v-`, `data-bind` are NOT design-system classes; skip those.
   - **Honor `migration.md §3` declarations when present.** If the team has filled in "Legacy design system / custom CSS" in §3, that is authoritative — read it first, use it as the primary guide, and prefer it over heuristics.
   - **Match visual fidelity, not just functional fidelity.** When translating to the target styling system:
     - **Tailwind / utility-first**: do NOT silently flatten the legacy custom classes to generic utilities. For each custom class that encapsulates a repeated decorative pattern (padding + shadow + border-radius + bg-color, etc.), produce either (a) a `@apply`-style component class in the project's main CSS that maps to the utility combination, or (b) keep the legacy class name and add a corresponding rule in the global stylesheet. The visual definition can move to utilities; the *semantic name and visual result* should survive.
     - **CSS Modules / styled-components / Vue scoped styles**: prefer preserving the semantic class names from the legacy as the new component's style boundaries. The definition moves into the component file; the name stays.
     - **Material UI / Chakra / ready-made design libraries**: pick the closest library equivalent for each custom class. Write a brief mapping note in `notes/<unit.id>.md` so reviewers see the translation table.
   - **Verify asset references resolve.** For every `<img src="...">`, `background-image: url(...)`, `<link rel="icon">`, or `@font-face src="..."`:
     - If the path points at a directory under the legacy `Pics/`, `images/`, `Content/`, `wwwroot/`, `fonts/`, etc., the file should already exist in the target's `public/` (copied by `/web-modernize:scaffold`'s asset-copy step).
     - If the asset is missing, do NOT silently break the reference. Add a `// TODO: asset missing — copy from <legacy path>` comment near the reference and add a "Gotchas — missing assets" note in `notes/<unit.id>.md` with the expected target path.
     - If the legacy uses absolute URLs like `/Content/Pics/foo.png` and the target framework serves `public/` at a different base path (e.g., Next.js basePath, Vite base config, custom prefix), surface the discrepancy in the unit's notes.
   - **Record the design translation in notes.** Append to `notes/<unit.id>.md` a "Design translation" section. Format: a short table mapping each legacy custom class used in this unit to its target translation (Tailwind utilities, CSS module class, component library equivalent), plus any rules that ended up in shared CSS rather than per-component styles.

8. **Add a placeholder test** (smoke test at minimum). The `migration.md §10` acceptance criteria should drive what is asserted.
9. **Append to `notes/<unit.id>.md`**: design decisions, source-to-target symbol map, gotchas. For `retry` mode, add a "Retry #<N>" section that records what was different this time and (if `retry_prompt` was set) quote the user's override verbatim. The "Design translation" section from step 7b lives in this same notes file.

### Honor `retry_prompt` when set

If `retry_prompt` is set (retry mode only), it is the **first** thing you should read after the source files, and it should bias every design decision below. Treat it like a senior engineer's design note: "the prior attempt assumed X — try Y instead". Do not silently ignore it; if any part conflicts with `migration.md`, surface the conflict to the user and ask which wins.

### Honor `force_deps` when set

If `force_deps == true` (set by `/migrate --force` after the user explicitly overrode the dependency block), expect symbols imported from unmet deps to be unavailable. Stub them, leave a `// TODO: provided by <dep.id>` comment, and record the workaround in `notes/<unit.id>.md` under "Gotchas — out-of-order migration". Do not fail just because a dep is missing.

If `force_deps` is `false` or absent, assume the caller verified deps are satisfied. If you still discover a missing symbol during translation that should have been provided by a dep, fail in §4 with a diagnostic explaining the discrepancy.

## 4. Stop conditions (failure)

Set `unit.status = "failed"` and stop if:

- A required source file is missing or unreadable.
- The target framework cannot represent something critical (e.g., a custom WebForms control with no obvious equivalent — flag for human design review).
- A test that *should* pass is failing in a way that suggests the migration is incorrect (not just a missing fixture).
- A dep symbol is missing and `force_deps` was not set (unexpected discrepancy with the caller's dep check).

On stop, write to `.claude/modernize/units/<unit.id>.json`:

```json
{
  "status": "failed",
  "in_flight": null,
  "failure": {
    "diagnostic": "<one-paragraph explanation of what stopped you and what you tried>",
    "branch": "modernize/<unit.id>",
    "diagnostic_history": <existing array, possibly populated by retry mode>
  }
}
```

Append a history entry. Print the diagnostic to the user with three suggested recovery paths:

```
✗ Migration of <unit.id> failed.

Diagnostic:
  <one-paragraph>

Recovery options:
  - /web-modernize:retry <unit.id>  (re-attempt, optionally with --with-prompt="…")
  - /web-modernize:rollback --unit <unit.id>  (revert any partial target files first, then retry)
  - /web-modernize:abandon --unit <unit.id>  (declare this unit out of scope)
```

Return control to the caller. Do NOT auto-advance to another unit.

## 5. Finalize successful migration

Write to `.claude/modernize/units/<unit.id>.json`:

```json
{
  "status": "migrated",
  "target_paths": [<actual paths written>],
  "in_flight": null,
  "history": [...existing, { "at": "<now>", "by": "<user>", "from": "in_progress", "to": "migrated", "session_id": "<sid>" }]
}
```

Update `state.json.updated_at`. Do not touch any other top-level field (status stays `in_progress`; transition to `complete` is `/web-modernize:verify`'s job).

## 6. Return to the caller

The caller (`/next`, `/migrate`, or `/retry`) is responsible for the user-facing closing message — they each have slightly different next-step nudges. Hand back:

- The final `unit.status` (`migrated` or `failed`).
- The list of target paths actually written.
- The notes file path.

The caller will print the success/failure banner appropriate to its mode.
