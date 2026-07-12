# Command-surface consolidation — design proposal

> **Status:** proposal / analysis only. No code, skill, schema, or config changes are made by
> this document. It exists to evaluate review finding **C-2** ("command surface is large — 19
> skills; several are thin verbs that could be flags/sub-modes; a reference plugin does
> comparable work in ~10 commands") and make a recommendation the maintainer can accept,
> reject, or shelve against the backlog.

## TL;DR

The reviewer's C-2 is a **hypothesis worth taking seriously but not at face value.** Two of the
named merges are genuinely worth doing; most of the rest are thin commands that are *justified*
and should stay. Recommended target: **17 commands** — fold `retry` into `migrate` and
`next-batch` into `next --n=K` (both are near-duplicate satellites of a command whose body is
*already* shared), and keep everything else, including several "thin" commands the reviewer
named (`unlock`, `abandon`, `parity-check`, `quality-check`, `status`/`report`). An optional
stretch to 16 (`quality-check` → `verify --quality-only`) is presented but not recommended.
Because removing a slash command is a **breaking change (major bump → 1.0.0)** per the plugin's
own versioning policy, any consolidation should ride the **same 1.0.0** that already owes the
queued `/auth`→`/foundation` and `auth_done`→`foundation_done` renames, done once while the
plugin still has no production users.

---

## 1. Framing: is "19 vs ~10" the right lens?

Command count is a **proxy** for cognitive surface, not a target to hit. web-modernize
legitimately covers dimensions a simpler reference plugin may not — behavioural **and** security
parity, an advisory idiomatic-quality + static-perf pass, an opt-in dynamic (API-replay +
Playwright) tier, multi-developer state reconciliation, an idempotent composition/cutover step,
and a multi-concern foundation phase. Each of those is a real user-facing capability, not
ceremony. The honest test is **"does each command earn its keep?"** — not "can we reach 10?".
Forcing the number down to 10 would require merging distinct state-machine phases or separately
useful read-only diagnostics, and (as §4 argues) that actively *hurts*.

That said, C-2 is partly right: a handful of commands are thin **and** near-duplicates of a
sibling, so they pay the "standing consistency tax" the reviewer names (the copy-pasted
`plan_override` flag-parsing block is verbatim across `next`/`migrate`/`retry`, with a fourth
variant in `next-batch` — this is real drift surface, adjacent to finding F-3). Cutting *those*
is worth it. Cutting the rest is not.

A mitigating factor unique to this plugin (see README "Talk to it naturally"): commands are also
reachable by **natural-language routing** off each skill's `description:` trigger phrases.
Removing a command name is therefore *softer* here than in a pure-CLI tool — the merged host
command absorbs the removed command's triggers, so "try again" / "retry" can still land on
`/migrate`. This lowers (does not erase) the discoverability cost of a merge.

---

## 2. The 19 commands by lifecycle phase

Disposition label is **my recommended verdict** (one of keep-standalone / merge-candidate /
flag-candidate). "C-2?" marks whether the reviewer named it as a consolidation target.

### Bootstrap path — one-time, linear, strong "next step" nudges. Each = one monotonic state transition.

| Command | Precondition (`state.status`) | Unique responsibility | Disposition | C-2? |
|---|---|---|---|---|
| `init` | `uninitialized` (refuses if state exists) | Lay down `migration.md` + `.claude/modernize/`; git/gitignore/schema-version checks | keep-standalone | no |
| `analyze` | `initialized` / `analyzed` | Detect source stack + entry points (loop-until-dry); interactive target-choice interview | keep-standalone | no |
| `plan` | `analyzed` | Validate `migration.md`; generate `plan.md` + per-unit files; set `review_mode`; confirm foundation concern set | keep-standalone | no |
| `scaffold` | `planned` | Create target skeleton (UI/API/DB) + copy legacy assets; `--assets-only` backfill | keep-standalone | no |
| `foundation` | `scaffolded` | Establish cross-cutting slice (auth + opted-in concerns); always-on design gate | keep-standalone | no |

### Iteration loop — repeated per unit, soft nudges. All four delegate the *same* translation body to `unit-migrator-caller.md` + `unit-migrator-subagent.md`.

| Command | Precondition | Unique responsibility | Disposition | C-2? |
|---|---|---|---|---|
| `next` | `foundation_done` / `in_progress` | Auto-select ONE pending unit (dep-aware) + resume in-flight; per-unit plan gate | keep-standalone (host for `next-batch`) | yes |
| `next-batch` | `foundation_done` / `in_progress` | Auto-select K independent units; **parallel** Workflow fan-out; always skips gate | **flag-candidate** → `next --n=K` | yes |
| `migrate <id>` | `foundation_done` / `in_progress` | **Explicit** named unit; `--force` bypasses deps | keep-standalone (host for `retry`) | yes |
| `retry <id>` | `foundation_done` / `in_progress` (unit `failed`) | Re-attempt a `failed` unit; preserves failure context; `--with-prompt` | **merge-candidate** → `migrate` | yes |
| `verify [id]` | `>= scaffolded` | lint/typecheck/test + parity gate + advisory quality; flips `migrated → verified`; `--dynamic` tier | keep-standalone | yes (as the thing parity/quality "overlap") |

### On-demand inspection / review — read-mostly, invoked between migrations.

| Command | Precondition | Unique responsibility | Disposition | C-2? |
|---|---|---|---|---|
| `parity-check <id>` | `>= scaffolded` (unit `migrated`/`verified`) | Run parity subagent on demand **+ owns the `acknowledge` mutation** that un-blocks `/verify` | keep-standalone (defended) | yes |
| `quality-check <id>` | `>= scaffolded` (unit `migrated`/`verified`) | Advisory idiomatic + perf review without the test cycle (fast quality loop) | keep-standalone (defended; softest) | yes |
| `status` | any (read-only) | Live console dashboard + artifact-drift check; **never mutates** | keep-standalone | implied (read-only diags) |
| `report` | `in_progress` / `complete` | Stakeholder digest → **file artifact** in md/json/html with filters | keep-standalone | implied |

### Composition / cutover.

| Command | Precondition | Unique responsibility | Disposition | C-2? |
|---|---|---|---|---|
| `integrate` | `foundation_done` / `in_progress` / `complete` | Idempotent app assembly — router/nav, whole-app smoke, orphan/cutover report, strangler proxy | keep-standalone | no |

### Recovery / maintenance / lifecycle exit.

| Command | Precondition | Unique responsibility | Disposition | C-2? |
|---|---|---|---|---|
| `sync` | needs git remote | Reconcile `state.json` + per-unit files after concurrent multi-dev work | keep-standalone | no |
| `rollback --unit <id>` | `>= in_progress` | Revert one unit's target files via git; reset to `pending`; shared-file safety check | keep-standalone | no |
| `unlock` | any | Force-clear a stale advisory lock (`force-clear` friction + audit append) | keep-standalone (defended; weakest) | yes |
| `abandon` | any | **Destructive** reset (`--soft`/`--hard`/`--unit`); two-step confirmation | keep-standalone (defended) | yes |

**Tally:** keep-standalone ×17, merge-candidate ×1 (`retry`), flag-candidate ×1 (`next-batch`).

---

## 3. Proposed consolidations (with gained / lost / recommendation)

### 3.1 Merge `retry` into `migrate` — RECOMMEND (high confidence)

`/migrate <id> [--force] [--with-prompt="…"] [--plan | --no-plan]`; if the named unit is in
`failed` status, behave as today's `retry` (preserve failure context, accept `--with-prompt`);
otherwise behave as today's `migrate`.

- **Gained.** −1 prompt file. Both already take an explicit `<unit-id>`, run in the same states,
  and share the exact same translation body — the only real deltas are `retry`'s `failed`
  precondition and its `--with-prompt`. Removes one verbatim copy of the `plan_override`
  flag-parsing / precondition / delegation / closing blocks (the C-2 "consistency tax" made
  concrete). `--with-prompt` becomes generally available, which is a genuine feature — you
  sometimes want to hand guidance to a *fresh* migrate too, not only a retry.
- **Lost / risked.** `retry` is a strong, memorable verb with its own NL triggers ("try again",
  "fix the failed unit"); its `failed`-status precondition currently produces a crisp error, and
  folding means `migrate` must branch on status with softer guidance. `migrate`'s usage text
  grows. Teams that learned `/retry` must relearn.
- **Mitigant.** NL routing: `migrate`'s `description:` absorbs the retry triggers, so plain
  English still lands. Auto-detecting `failed` keeps behaviour identical to today.
- **Recommendation: MERGE.** Lowest-risk, highest-clarity merge in the set — same argument
  shape, adjacent semantics, already-shared body.

### 3.2 Merge `next-batch` into `next --n=K` — RECOMMEND (medium confidence)

`/next [--n=K] [--plan | --no-plan]`; `--n=1` (default) is today's `next` exactly (serial, gate
honoured); `--n>1` fans out K independent units in parallel via the Workflow tool and force-skips
the gate with today's mandatory banner.

- **Gained.** −1 prompt file. Batch is conceptually "more of `next`" — one command expresses the
  whole *auto-select* axis (one or many). Removes the fourth copy of the migration-loop preamble.
- **Lost / risked.** `next-batch` genuinely has a *different execution path* (parallel Workflow
  fan-out) and an *always-skip-gate* invariant with a required banner; folding gives `next` a
  dual path (serial-gated vs parallel-ungated) that enlarges its prompt and makes its safety
  property conditional (gate honoured iff `K=1`). It only shipped in **v0.17.0**, so merging
  re-churns brand-new muscle memory.
- **Mitigant.** Default `--n=1` is byte-for-byte today's behaviour; the banner fires only when
  `K>1`.
- **Recommendation: MERGE (medium confidence).** On-theme (both are auto-select) and worth doing
  inside the same major, but lower value than 3.1 and it re-churns a just-shipped command — an
  acceptable "skip" if the maintainer wants to minimise 1.0.0 blast radius.

### 3.3 (Optional) Fold `quality-check` into `verify --quality-only` — NOT recommended

- **Gained.** −1; the migration-critic agent already runs inside `/verify` step 5b, so a
  `--quality-only` mode (skip tests + parity, run only the critic) covers it.
- **Lost / risked.** The **fast advisory loop** loses its own entry point — today you can iterate
  on idiomaticity/perf without paying for the full lint/typecheck/test/parity cycle. `verify`
  grows yet another mode and starts mixing a read-only sub-behaviour into its state-flipping one.
  "check for jobol" / "is this idiomatic" is a distinct intent from "verify".
- **Recommendation: KEEP (lean).** The overlap is real but the standalone intent + fast loop
  justify the thin command. This is the softest keep in the set — reasonable to revisit later,
  but not worth the 1.0.0 churn now.

---

## 4. Where consolidation would HURT (defend the keeps)

The reviewer named `unlock`, `abandon`, `parity-check`/`quality-check`, and the
`next`/`next-batch`/`migrate`/`retry` cluster. Here is where the hypothesis breaks down.

- **Do NOT collapse the bootstrap path** (`init → analyze → plan → scaffold → foundation`). Each
  is a distinct **monotonic state transition** with its own precondition and a *human decision
  gate* (analyze = interactive interview; plan = review-mode + concern confirmation; foundation =
  always-on design gate). A single `/setup` wizard would destroy the "refuse + redirect to the
  correct skill" rail-guarding that keeps users on the happy path, erase the per-phase strong
  nudges, and conflate re-runnable phases (`analyze`, `plan`) with once-only ones (`init`). These
  five commands are the *clarity* the state machine buys — collapsing them is a net loss.

- **Keep `status` and `report` separate.** Both are read-only, but they serve different
  audiences (developer vs. stakeholder), emit different outputs (live console dashboard vs. a
  *file artifact* in md/json/html), and carry different preconditions (`status` any time;
  `report` needs `>= in_progress`). Merging separately-useful read-only diagnostics reduces
  clarity for essentially zero maintenance savings — the exact "read-only commands that benefit
  from being separately invocable" case.

- **Keep `parity-check` standalone (defended).** It is *not* merely "reachable via `/verify`": it
  owns the `parity_acknowledged_diffs[]` **acknowledge mutation** — the mechanism a team uses to
  mark a diff intentional so it stops blocking `/verify`. You cannot fold that into `verify`,
  because `verify` is the gate being unblocked. Its precondition is also *wider* (`migrated` OR
  `verified`) than `verify`'s (`migrated`). A `--parity-only` + `--acknowledge` flag pair on
  `verify` would widen its mode-space and split its read-only vs. state-flipping responsibilities.

- **Keep `abandon` standalone (defended).** It is explicitly **destructive** (deletes
  directories, prunes deps) with three modes and a two-step confirmation. Hiding a dangerous
  reset behind a flag on a safer command is a footgun; it earns its own hard-to-misfire command.

- **Keep `unlock` standalone (defended; weakest keep).** Yes, it clears one field — but with
  deliberate `force-clear` friction, a lock summary, a TTL caveat, and an audit-history append.
  The alternatives are worse: folding into read-only `/status` breaks its no-mutation invariant;
  folding into `/plan`/`/scaffold` as `--force-unlock` splits the recovery action across two
  commands and buries the friction. It is stable and rarely touched, so the cost of keeping it is
  trivial. (If the surface *must* shrink further, this is the first flag-candidate to reconsider —
  but the payoff is one small, stable file.)

- **Keep BOTH `next` and `migrate` (do not merge the two poles).** Auto-select (`next`) vs.
  explicit-select (`migrate`) is a real mental-model fork, and both are the highest-traffic verbs
  in the set. §3.1/§3.2 fold the *satellites* (`retry`, `next-batch`) into these poles; merging
  the poles themselves into one flag-driven command would damage the clearest commands in the
  plugin. This is the boundary of the consolidation, not its next step.

- **`sync` and `rollback` are not thin.** Both are non-trivial recovery/composition operations
  (git reconciliation; file revert with a shared-file blast-radius check). The reviewer did not
  target them, and rightly so.

> Naming nit (not a merge): `abandon --unit <id>` (mark **skipped** + prune deps) and
> `rollback --unit <id>` (revert files + reset to **pending**) are adjacent and easy to confuse.
> Worth a one-line cross-reference in each command's help text; not a consolidation.

---

## 5. Recommended target command set

**Primary recommendation: 17 commands** (from 19).

Remove as standalone (folded into a host command):
1. `retry` → `migrate <id> [--with-prompt="…"] [--force]` (auto-detects `failed` status). *(§3.1)*
2. `next-batch` → `next [--n=K]` (`--n=1` default = today's `next`; `--n>1` = parallel, gate skipped). *(§3.2)*

Keep (17): `init`, `analyze`, `plan`, `scaffold`, `foundation`, `next`, `migrate`, `verify`,
`parity-check`, `quality-check`, `status`, `report`, `integrate`, `sync`, `rollback`, `unlock`,
`abandon`.

**Rationale.** This removes exactly the two commands that are *both* thin *and* near-duplicate
satellites of a command whose translation body is already shared — so the merge deletes genuine
consistency-tax (duplicated flag-parsing/preamble blocks) without losing a distinct capability.
Every remaining command maps to either a distinct state-machine phase, a distinct write mutation,
a distinct audience/output, or a distinct recovery operation. It cuts surface where the reviewer
is right and holds the line where the reviewer's proxy metric would otherwise force real harm.

**Optional stretch: 16 commands** — additionally fold `quality-check` into
`verify --quality-only` (§3.3). Presented for completeness; **not** recommended, because it trades
a clean fast-advisory-loop entry point and a memorable intent for one fewer file.

**Not on the table:** matching the reference plugin's ~10 would require collapsing bootstrap
phases and/or read-only diagnostics — see §4. Do not.

---

## 6. Versioning implication

- Removing or renaming a slash command is a **breaking change** per the plugin's versioning
  policy → **major bump to 1.0.0**. (Removing a skill directory genuinely removes the command;
  Claude Code has no skill alias mechanism, and skills cannot forward to skills, so there is no
  thin-alias escape hatch. NL routing partially compensates by absorbing the removed command's
  trigger phrases into the host command's `description:`.)
- These merges need **no schema change** — `retry` and `next-batch` own no `state`/`unit` schema
  fields, and deleting a skill file does not touch `state.schema.json`/`unit.schema.json`. So it
  is a 1.0.0 for *command-surface* reasons only.
- **Batch it with the already-queued breaking changes.** CLAUDE.md already records that
  `/auth`→`/foundation` and the `auth_done`→`foundation_done` phase rename are breaking changes
  deferred "when versioning is next addressed." The command consolidation should ride the **same
  1.0.0** so the plugin takes its muscle-memory + docs churn **once**, not piecemeal across
  releases.
- **Do it now, decisively.** The repo states repeatedly that the plugin has **no production
  users** — this is the cheapest possible moment for a breaking surface change. Piecemeal renames
  are the expensive path (each one re-churns muscle memory and the version/count strings
  hard-coded across `docs/`).
- **Sync-on-release checklist** (per CLAUDE.md "counts hard-coded in many places"): update the
  README slash-command table + the NL-routing table; the "19 total" skill count in CLAUDE.md; the
  `… · N skills · …` strings in `docs/decks/*` (regenerate via the Python scripts) and
  `docs/diagrams/*.svg`; `CHANGELOG.md`; and the `version` in both `.claude-plugin/plugin.json`
  and `.claude-plugin/marketplace.json`. Move `retry`/`next-batch` triggers into `migrate`/`next`
  descriptions.

---

## 7. Recommendation summary

Accept C-2 **partially**. Do the two high-confidence merges (`retry`→`migrate`,
`next-batch`→`next --n=K`) for a 17-command surface, land them in the **1.0.0** that already owes
the `/foundation` rename, and explicitly reject the rest of the hypothesis: the bootstrap phases,
the two read-only diagnostics, `parity-check`'s acknowledge mutation, destructive `abandon`, and
recovery `unlock` are all justified even though some are thin. The reviewer's "~10 commands"
figure is a useful smell test, not a goal — chasing it past 17 means merging things whose
separateness is the product's clarity, not its bloat.
