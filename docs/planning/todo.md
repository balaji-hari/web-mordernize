# web-modernize — Backlog (open gaps & future designs)

> **This file replaces** the old `docs/todo.md` plus four separate
> `docs/planning/future-*.md` docs (additional-agents, a numbered feature backlog,
> data-layer-migration, subagent-unit-migrator). They were two layers of the same backlog —
> a short tracker that pointed at standalone design docs — and the two layers had already
> drifted out of sync once (one of those docs still listed three items as open after they'd
> shipped in v0.13.0). Merging removes that failure mode structurally: there's only one
> place left to update.
>
> Shipped-feature *narrative* (what changed, why, version numbers) lives in `CHANGELOG.md` —
> this file does not restate it beyond a one-line pointer per item, to avoid the same kind
> of drift between two docs describing the same thing.

**Status legend:** `OPEN` = no design doc, gap only · `DESIGNED` = decisions made, ready to
implement · `BLOCKED` = explicitly deferred pending an external signal · `DONE` = shipped,
kept here only as a one-line pointer for context.

**Feasibility tiers** (this is a *readiness* ranking, not a value ranking — an idea can be
high-value and still Tier 3 if nobody's designed it yet):

- **Tier 1 — Ready now.** Complete design (or small enough not to need one), no blockers.
- **Tier 2 — Ready, but large.** Complete design, but big enough to deserve its own session.
- **Tier 3 — Needs design first.** The gap is real but nobody's made the design decisions yet.
- **Tier 4 — Deliberately deferred.** A design exists or is easy, but it's intentionally on
  hold pending a specific signal (telemetry, a prerequisite shipping, etc.) — building it
  now would contradict the reasoning already on record below.

---

## Priority order (scan this first)

| Tier | Item | Category | Effort | Depends on |
|---|---|---|---|---|
| 1 | [Docs sync — version + counts to current release](#docs-sync--version--counts-to-current-release) | Docs / release hygiene | M | — |
| 1 | [Configuration migration](#configuration-migration) | Coverage | M | — |
| 1 | [Global / shared client state](#global--shared-client-state) | Composition | M | — |
| 2 | [Data-layer bulk migration](#data-layer-bulk-migration) | Coverage | L | — |
| 2 | [`/verify` referee panel](#verify-referee-panel) | Verification depth | L | — |
| 3 | [Accessibility (a11y) check](#accessibility-a11y-check) | Verification depth | M | — |
| 3 | [Runtime performance (Tier-2)](#runtime-performance-tier-2) | Verification depth | ? | dynamic tier (shipped) |
| 4 | [Dependency-preflight agent](#dependency-preflight-agent) | Control & safety | S | retry-pattern evidence |
| 4 | [Visual regression (Phase C)](#visual-regression-phase-c) | Verification depth | ? | — |
| 4 | [Business-rule mining as a first-class pre-translation artifact](#business-rule-mining-as-a-first-class-pre-translation-artifact) | Verification depth | unscoped | — |

*(`unit-migrator` subagent conversion, `/next-batch`, and CSS audit shipped in v0.17.0 — moved to "Shipped" below.)*

*(See `docs/planning/command-consolidation-proposal.md` for the command-surface consolidation analysis (C-2).)*

---

## Tier 1 — Ready now

### Docs sync — version + counts to current release
**Category:** Docs / release hygiene · **Status:** DESIGNED · **Effort:** M

`docs/` is hand-maintained (not generated from plugin source) and has drifted a full minor +
several patches behind. Surfaced during the v0.17.4 doc-cleanup pass; deliberately **not** fixed
under a patch's cover because it predates v0.17.4 and needs its own verified deck regeneration.

**Version lag (all still at v0.16.0):** `docs/DEVELOPER-HANDBOOK.md` §13 header ("What's new
(v0.12.0 – v0.16.0)" + its narrative), all three `docs/diagrams/architecture-p{1,2,3}-*.svg`
footers, and both `docs/scripts/build_presentation.py` + `docs/scripts/build_onepager_v2.py`
version strings. The handbook's "What's new" narrative is missing everything from v0.17.0 on:
`unit-migrator` subagent conversion, `/next-batch`, CSS audit, the v0.17.1–v0.17.3 prompt fixes,
and v0.17.4 (datastore-reachability preflight, `## Verify commands` / `## Data migration`
framework sections, `/status` foundation rollup, string-built-SQL warning, i18n multi-locale
guard, guarded EALLOWSCRIPTS gotcha).

**Count drift:** `architecture-p3-state.svg` footer + `build_presentation.py` read "18 skills ·
6 agents"; actual is **19 skills** (20 dirs under `skills/` minus non-command `_shared`) and
**31 framework files** (correct/unchanged). **Decision on record:** count as **5 agents** — the
actual subagents — and treat `agents/agent-rules.md` + `agents/permanent-gotchas.md` as shared
reference docs, not agents. (Confirm the count freshly at execution time; skill/agent/framework
totals can move between now and then.)

**How to execute (per CLAUDE.md "Presentation & diagram assets"):** never hand-edit the binary
`.pptx` — edit the strings/counts in the two `docs/scripts/build_*.py` scripts and the three
SVGs directly, then re-run `python docs/scripts/build_presentation.py` and (with `docs/scripts/`
importable) `build_onepager_v2.py` to regenerate the decks; confirm `python-pptx` (1.0.2) imports
before editing and report if the regenerate step fails rather than leaving half-updated binaries.
Grep `docs/` for the old version string **and** the old counts and update every hit together
(they're hardcoded in many places — footers, title/closing slides, the "The N Skills" slide
title, inventory tables). **Recommended model: Sonnet 5 / high** — mostly mechanical + one prose
sub-task (extend the handbook "What's new" from `CHANGELOG.md`), where the real risk is catching
every hardcoded hit, not reasoning difficulty.

**Files:** `docs/DEVELOPER-HANDBOOK.md` · `docs/diagrams/architecture-p{1,2,3}-*.svg` ·
`docs/scripts/build_presentation.py` · `docs/scripts/build_onepager_v2.py` · regenerated
`docs/decks/*.pptx` (build artifacts, via the scripts — never by hand).

---

### Configuration migration
**Category:** Coverage · **Status:** OPEN · **Effort:** M

v0.12 *masks* secrets in artifacts, but nothing *migrates* configuration — `web.config` /
`appsettings.json` / connection strings / app settings / feature-flag config → the target
stack's config system (`.env`, `appsettings.json` equivalent, etc.). No design doc yet; follows
the same "establish once, reference everywhere" shape as the Foundation phase's concerns —
likely lands as a `/foundation` concern or a `/scaffold` step that reads a per-target-framework
config recipe, rather than a new command.

---

### Global / shared client state
**Category:** Composition · **Status:** OPEN · **Effort:** M

`unit-migrator` translates per-unit ViewState → component state, but there's no "establish the
app-wide store once" step for cart/preferences/other shared client state beyond the auth
session — so different developers invent their own. No design doc yet; likely a natural fit as
an additional opt-in `/foundation` concern (same shape as i18n/feature-flags/telemetry) rather
than a bespoke mechanism.

---

## Tier 2 — Ready, but large

### Data-layer bulk migration
**Category:** Coverage · **Status:** DESIGNED · **Effort:** L (biggest remaining functional gap)

The plugin covers detect → plan → scaffold → foundation → migrate units → verify → report, but
the data layer has no execution path beyond *wiring* (the `/foundation` `data` concern ships
ORM/client/connection/migration-harness setup only). Nothing translates the legacy schema,
queries, stored procedures, or ORM mappings.

**The core decision — gate it like auth, not as a soft dependency.** Seeding `kind: data` units
that flow through `/next` gated only by `depends_on` is **rejected**: a missing edge in `/plan`,
or `/migrate --force`, would silently wire a feature page to a database that was never migrated
— tests could still pass (the exact silent-failure class `parity-reviewer` exists to catch).
Instead, treat the data layer the way auth already works: a **hard phase gate** no `--force` can
jump.

```
... → scaffolded → foundation_done → data_done → in_progress → complete
                                      ^^^^^^^^^  NEW
```

**Chosen design (B1) — dedicated command:** new `/web-modernize:migrate-data` skill drives
`foundation_done → data_done`. (B2 — gating `/next` itself to only offer `kind: data` units
during that window — is an acceptable lighter-surface alternative if minimizing command count
matters more than explicitness; gate semantics are identical either way.)

**Provision vs. translate are two different moments:** `/scaffold` keeps provisioning the empty
target DB + ORM wiring (one-shot, bootstrap — roughly what it does today). The new
`data-layer-migrator` agent runs the actual translation in its own `migrate → verify → retry`
loop — translation can be wrong and needs checking, which a one-shot scaffold step can't provide.

**New agent — `agents/data-layer-migrator.md`:** reads legacy schema/SQL/procs/ORM mappings,
reads the chosen `frameworks/<target-db>.md` recipe, emits target ORM models + migrations,
verifies by **equivalence** (does the migrated query return the same row shape / ordering /
null-vs-missing semantics?) via new `parity_findings[].kind` values (`query_result`,
`schema_shape`) handled by the existing `parity-reviewer` — not a second reviewer.

**New framework role — `role: target-db`:** one file per target ORM (`prisma`, `drizzle`,
`ef-core`, `typeorm`, `jpa-hibernate`), each with `## Scaffold` / `## Models` / `## Migrations` /
`## Query translation notes` / `## Verification` sections. Cross-cutting rules (decimal/money
precision, timezone handling, N+1 traps) stay in `permanent-gotchas.md`.

**Explicitly out of scope:** per-stack translator agents (stack knowledge stays in framework
files); live-data ETL (code migration only, not moving production rows).

**Files:** `agents/data-layer-migrator.md` (new) · `frameworks/{prisma,drizzle,ef-core,typeorm,
jpa-hibernate}.md` (new, `role: target-db`) · `skills/migrate-data/SKILL.md` (new) ·
`skills/plan/SKILL.md` (seed `kind: data` units, add `__data__` token to feature deps) ·
`skills/scaffold/SKILL.md` (DB step reads the new recipe instead of writing a placeholder) ·
`skills/verify/SKILL.md` (recognize `kind: data`, run query-equivalence checks) ·
`skills/{next,migrate}/SKILL.md` (precondition shifts to `status >= data_done`) ·
`agents/parity-reviewer.md` (`query_result`/`schema_shape` kinds) · `templates/state.schema.json`
(`data_done` status value — additive, decide separately whether it warrants a `schema_version`
bump; no migration code either way) · `templates/unit.schema.json` (`"data"` kind value).

**Verify:** `/plan` seeds `kind: data` units + `__data__` deps · after `/scaffold` +
`/foundation`, `/migrate SomeFeaturePage --force` **must refuse** (the regression test for the
bypass bug this design exists to prevent) · the data phase runs, `/verify` checks query
equivalence, status advances to `data_done` · `/next` then offers feature units against the real
migrated tables · dropping a hand-written `frameworks/<custom-db>.md` works with no other edits.

---

### `/verify` referee panel
**Category:** Verification depth · **Status:** OPEN (strategic) · **Effort:** L

**Not to be confused with the now-shipped `/verify` Workflow-tool parallelization (v0.17.0,
see Shipped below) — that made existing verification faster (units + reviewer dimensions run
concurrently instead of sequentially); this item is about depth, not speed.** The full version
of the refute pass already shipped for `parity-reviewer` highs (v0.12.0): a per-finding
**referee panel** — multiple independent passes that must agree before a finding escalates —
deepening confidence on `/verify`'s gate beyond the current single refute check. `workflows/
verify-run.js` already exists and fans out per-unit reviewers in parallel; this item would add
a further fan-out *within* the parity stage (N referees per finding) rather than introduce a
new mechanism. No design doc yet beyond this description.

---

## Tier 3 — Needs design first

### Accessibility (a11y) check
**Category:** Verification depth · **Status:** OPEN · **Effort:** M

Porting WebForms/legacy markup → React etc. can lose ARIA/labels/keyboard semantics; nothing
checks for it today. Leaning toward an **opt-in `/verify` post-check** (reusing the advisory,
never-blocks shape of `migration-critic`'s static passes) rather than an always-on agent — but
the actual check design (axe-core integration? static markup heuristics? both?) isn't decided.

### Runtime performance (Tier-2)
**Category:** Verification depth · **Status:** OPEN · **Effort:** unscoped

The *static* perf-regression pass (N+1, unbounded data, waterfalls, blocking I/O, bundle bloat)
already shipped in `migration-critic`. Actual runtime measurement (p99 latency, benchmarking)
was deliberately deferred to ride on the dynamic testing tier (API replay + Playwright, both now
shipped) — but nobody has designed what a runtime-perf pass on top of that tier looks like yet.

---

## Tier 4 — Deliberately deferred

### Dependency-preflight agent
**Category:** Control & safety · **Status:** BLOCKED · **Effort:** S

A read-only agent that scans a unit's imports for missing/unmet `depends_on` before migration
starts, instead of discovering it mid-migration. **Design is simple and ready** — the only reason
this is Tier 4, not Tier 1, is a deliberate decision already on record: hold it until real
migrations show a retry pattern that justifies the latency cost (it would run on *every* `/next`
and `/migrate` invocation). Building it now means guessing at a cost/benefit ratio nobody has
evidence for yet. Revisit once `/retry` usage data exists.

**Design (when unblocked):** new `agents/preflight.md`, read-only. Scans `source_paths` for
imports/includes, cross-references `units/*.json`, returns `declared_deps` / `inferred_deps` /
`missing_deps` / `pending_deps`. Runs automatically as a pre-step of `/next`/`/migrate`; output to
`notes/<id>.md`; warns + asks for confirmation if `missing_deps` is non-empty. Additive
`unit.schema.json` fields (`inferred_deps[]`, `missing_deps[]`).

### Visual regression (Phase C)
**Category:** Verification depth · **Status:** BLOCKED · **Effort:** unscoped

Pixel/visual diffing between legacy and migrated UI. Explicitly deferred — the fragile,
baseline-heavy tier — behind both the CSS audit and the dynamic testing tier (API replay +
Playwright E2E), both now shipped. No active blocker beyond "build the cheaper tiers first and
see how much they already catch."

### Business-rule mining as a first-class pre-translation artifact
**Category:** Verification depth · **Status:** BLOCKED · **Effort:** unscoped

Business-rule mining as a first-class pre-translation artifact — promote the Given/When/Then
behaviour contract from a migration side-effect to a mined, reviewed artifact consumed as a gate
(deferred; adjacent to the data-layer work above, but distinct — no design doc yet beyond this
description).

---

## Anti-patterns already considered and rejected

Don't re-propose these without new evidence — the reasoning held when last reviewed:

- **Per-stack expert agents** (`dotnet-translator`, `java-translator`, …) — conflicts with the
  framework-file model; stack knowledge belongs in `frameworks/*.md` as data.
- **Specialized mini-agents fragmenting `unit-migrator`** (test-translator, design-extractor,
  asset-extractor, …) — splits one concern across many files; coordination overhead exceeds the
  value.
- **Documentation-generator agent** — `/report` already covers stakeholder reporting.
- **Always-on per-concern auditors** (security/perf/a11y scanners as dedicated agents) — useful
  in isolation, but better as opt-in `/verify` post-checks reading `verify.config.json` than as
  dedicated agents (this is *why* a11y above leans toward a post-check, not a new agent).
- **Subjective translation-quality grader** — superseded by the objective, orthogonal
  idiomatic-structure critic (`migration-critic`) that actually shipped.

## Shipped (pointer only — see `CHANGELOG.md` for the full story)

Integration/cutover command · Foundation phase (cross-cutting concerns) · emergent shared-code
extraction + `/plan` backfill · non-UI/background units · per-unit plan gate · cross-unit
rollback safety · static performance review · dynamic testing tier (API replay + Playwright) ·
behavioural-parity reviewer + refute pass + security-parity dimension · migration-quality critic
+ `/quality-check` · untrusted-input/secret-masking disciplines · `/scaffold` toolchain preflight
· Given/When/Then behaviour contracts · artifact-drift staleness detection · dependency graph in
`plan.md` · `workflows/analyze-discovery.js` loop-until-dry discovery · auto-authored E2E specs ·
`/report` verification-depth sections · **(v0.17.0)** `unit-migrator` subagent conversion (two-call
plan-gate via independent fire-and-forget subagent calls, not resumption) · `/next-batch` parallel
migrator (`workflows/next-batch.js`, always-ungated) · CSS audit (styling detection in
`legacy-analyzer` + shared-stylesheet sizing in `/plan` + `css_*` quality-finding kinds) ·
`/verify` Workflow-tool parallelization (`workflows/verify-run.js` — pipeline across units,
parallel reviewer fan-out per unit).
