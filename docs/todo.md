# web-modernize — Open gaps & TODO

A running register of gaps and seams not yet implemented, surfaced while reviewing how the
per-unit, HTTP/UI-centric migration model composes a whole application. Detailed design docs for
some items live under [`docs/planning/`](./planning/) and are cross-referenced below.

**Status legend:** `NEW` = identified here, not yet captured elsewhere · `TRACKED` = has a
`docs/planning/future-*.md` design doc · `DONE` = shipped (see `CHANGELOG.md`).

**The throughline (largely resolved in v0.15.0):** the three root tensions were — auth was the *only*
cross-cutting concern with a phase (→ fixed by the **Foundation phase**), the `unit.kind` enum was
HTTP/UI-shaped (→ fixed by **background units**), and "per-unit file isolation" broke around shared
files (→ fixed by **emergent shared-code backfill** + **cross-unit rollback safety**). The remaining
open items below are mostly last-mile (integration/cutover, config migration) and depth (data layer,
performance/a11y parity, dynamic testing, parallel migration).

---

## Composition & cross-cutting

- [x] **Integration / cutover command** — `DONE` (v0.15.0, see `CHANGELOG.md`) · effort M–L · value med
  - *Shipped:* `/web-modernize:integrate` — an **idempotent reconciliation** runnable at any stage and as
    final cutover (`--dry-run`/`--final`). Assembles a central router + nav from each migrated unit's
    additive `routes[]`, runs a whole-app smoke, flags orphaned units, reports cutover coverage %, and —
    for `strategy: strangler-fig` — maintains the traffic-splitting proxy. `state.integration` object;
    per-stack `## Integration` recipe in `frameworks/*.md`; shared files inherit the rollback-safety check.

- [x] **Cross-cutting concerns phase** (beyond auth) — `DONE` (v0.15.0, see `CHANGELOG.md`) · effort M · value high
  - *Shipped:* the **Foundation phase** — `/web-modernize:foundation` **replaces `/auth`** and establishes
    all confirmed cross-cutting concerns as the first slice: auth (always) + opt-in i18n / feature flags /
    error handling / telemetry / logging (declared in `migration.md §13`, confirmed at `/plan`). One
    consolidated design gate; parallel implementation via `agents/cross-cutting-migrator.md` +
    `workflows/foundation-establish.js` (disjoint files), with sequential composition-root wiring. New
    `kind: cross-cutting`, `state.status: foundation_done`, `state.foundation` object (additive).
  - *Decisions:* generalized into ONE command (replacing `/auth`, not a per-concern skill); soft phase-1
    ordering (feature units hard-gate on auth only, not every concern); the `/auth → /foundation` rename
    is breaking (major bump deferred — no users).

- [ ] **Global / shared client state** (cart, preferences, app store) beyond the auth session — `NEW` · effort M · value med
  - *Today:* `unit-migrator` translates per-unit ViewState → component state.
  - *Gap:* no "establish the app-wide store once" step → different devs invent their own.

- [x] **Emergent reusable-code extraction + `/plan` backfill** — `DONE` (v0.15.0, see `CHANGELOG.md`) · effort S–M · value high (DRY)
  - *Shipped:* `unit-migrator` records emergent shared code in its own `extracted_shared[]` (placed in the
    stack's conventional shared location — inferred + confirmed at the plan gate, **not** a hard-coded
    `src/lib/`), and `/plan`'s **Step 6b** backfills a `kind: shared` unit (`status: migrated`) for each,
    wires `depends_on`, dedups, and warns on independent duplicates. Additive field — no `schema_version` bump.

## Coverage — units the model can't express

- [x] **Non-UI / background units** — `DONE` (v0.15.0, see `CHANGELOG.md`) · effort M–L · value high
  - *Shipped:* single `background` unit kind + optional `trigger` (`scheduled`|`queue`|`hub`|`batch`|`startup`); a separate non-route discovery pass in `legacy-analyzer` (exempt from the 100-entry importance cap); a trigger→target migration recipe in `unit-migrator`; a **build + tests-only smoke gate** (`smoke.kind: background-tests-only`, job never invoked, explicit non-silent note). `/plan` carries `trigger`, skips the `__auth__` auto-dep, and assigns a late phase. Additive — no `schema_version` bump.
  - *Decisions:* one umbrella kind (not split `job`/`worker`/`hub`); tests-only smoke (not invoke-once).

- [ ] **Configuration migration** — `NEW` · effort M · value med
  - *Today:* v0.12 *masks* secrets in artifacts.
  - *Gap:* nothing *migrates configuration* — `web.config` / `appsettings.json` / connection
    strings / app settings / feature-flag config → the target's config system.

- [ ] **Data-layer migration phase (bulk translation)** — `TRACKED` → [`future-data-layer-migration.md`](./planning/future-data-layer-migration.md)
  - **Update (v0.15.0):** the data-access **wiring** (ORM/client/connection/migration harness) now ships as the
    `data` concern of `/foundation`. What remains here is only the **bulk** translation:
  - Schema / query / stored-proc / ORM translation as a gated `data_done` phase. Biggest functional
    gap. (Live-data ETL is explicitly out of scope.)

## Control & safety

- [x] **Per-unit plan gate — opt-out, migration-wide default set at `/plan`** — `DONE` (v0.15.0, see `CHANGELOG.md`) · effort M · value med
  - *Shipped:* opt-out `state.review_mode` (`plan-first` default | `auto`) set at `/plan`; per-unit `--plan`/`--no-plan`; the gate is `unit-migrator` §3.5. Plus an **always-on `/foundation` design gate** (independent of `review_mode`, `--no-plan` to skip). `/scaffold` intentionally **excluded** (preflight + unknown-tech follow-up + permission prompts already cover it).
  - *Today:* `/next` and `/migrate` translate and write, recording design decisions in `notes/`
    *after* the fact. Plan-review exists at the macro level via `/plan` (the unit list), not per unit.
  - *Idea:* borrow `code-modernization`'s **transform-approval pattern** — before translating a unit,
    `unit-migrator` presents its plan (target file layout, approach, design decisions, tests to
    write, ambiguities) and **waits for explicit approval before writing**.
  - *Default is opt-out (gate ON):* every unit is gated unless the migration opts out. `/plan`
    optionally takes the migration-wide default and persists it (`state.json.review_mode`:
    `plan-first` (default) | `auto`); whatever is set at `/plan` is the default for the *complete*
    migration. Per-unit override stays: `/next --no-plan` / `/migrate --no-plan` skips the gate for
    one unit; `/next --plan` forces it when the migration default is `auto`. Teams that want the old
    fast flow flip the whole migration to `auto` with one `/plan`-time choice.
  - *Throughput note:* opt-out trades `/next` speed for safety-by-default; the single `/plan` setting
    (→ `auto`) and the per-unit `--no-plan` override both recover the fast path, so the cost is
    opt-out-able rather than forced.
  - *Note (transform-approval pattern):* cm gates its **code-generating** commands
    (`transform`/`reimagine`/`uplift`, plus the system-wide `brief`) with plan → explicit approval
    ("no objection" ≠ approval) → tests-first → idiomatic implementation → adversarial review.
    Discovery commands stay friction-free. The line to copy: gate *code generation*, not *read-only*
    work. (Claude Code's own plan mode is a harness/user setting the plugin can't force.)

- [x] **Cross-unit rollback safety** (shared-file entanglement) — `DONE` (v0.15.0, see `CHANGELOG.md`) · effort M · value high (correctness)
  - *Shipped:* `/rollback` runs a **data-driven** shared-file check (unit `kind` `shared`/`cross-cutting`/synthetic,
    `extracted_shared[].path`, paths shared across >1 unit, the `notes/__layout__.md` record — never path-pattern
    matching) and **refuses by default** when a unit owns shared files live dependents rely on, printing the blast
    radius. `--force-shared` overrides and records `rollback_info.shared_impact`. Ambiguous ownership → asks the dev.
  - *Decision:* refuse-by-default (not warn-and-continue).

- [ ] **Dependency-preflight agent** — `TRACKED` → [`future-additional-agents.md`](./planning/future-additional-agents.md) (Candidate 3)
  - Scan a unit's imports for missing/unmet `depends_on` before migration. Deferred pending real
    retry-pattern evidence. Rename to avoid clashing with the shipped `/scaffold` *toolchain* preflight.

## Verification depth

- [x] **Performance parity / regression (static)** — `DONE` (v0.15.0, see `CHANGELOG.md`) · effort M · value med
  - *Shipped:* a **static** perf-regression pass folded into `migration-critic` — `perf_n_plus_one`,
    `perf_unbounded_data`, `perf_waterfall`, `perf_blocking`, `perf_bundle` (added to `quality_findings[].kind`).
    Advisory; via `/verify` step 5b + `/quality-check`. **Runtime perf measurement (p99/benchmarking) is the
    deferred Tier-2** — rides the dynamic tier's future runtime pass.

- [ ] **Accessibility (a11y) check** — `NEW` · effort M · value med
  - *Gap:* porting WebForms/legacy → React can lose ARIA/labels/keyboard semantics; nothing checks.
    `future-additional-agents.md` suggests this as an opt-in `/verify` post-check, not an always-on agent.

- [ ] **CSS audit** — `NEW` · effort M · value med
  - *Approach A — legacy sizing in `/analyze`* (`legacy-analyzer` CSS pass): detect CSS frameworks
    (Bootstrap, Tailwind, Material), preprocessors (SASS/LESS), approximate rule count, CSS-in-JS vs
    stylesheets, utility-class usage. Feed `analysis.json` so `/plan` can size CSS migration as explicit units.
  - *Approach B — quality findings in `migration-critic` (Tier 2)*: add `css_*` finding kinds — unported
    rules, specificity leakage, missing responsive breakpoints, dead selectors in the migrated output.
    Surfaces in `/verify` step 5b and `/quality-check`. No new command needed.
  - *Recommendation:* ship A + B together — A gives upfront sizing (CSS is often 20–30% of migration
    effort and gets silently dropped from backlogs), B catches regressions during verification.
  - *Out of scope:* visual/pixel regression (deferred to Phase C of the dynamic tier).

- [x] **E2E · API-replay testing (dynamic tier, Phase A+B)** — `DONE` (v0.15.0, see `CHANGELOG.md`) · effort M · value med
  - *Shipped:* opt-in `/web-modernize:verify --dynamic` (advisory step 5c) — **Phase A API replay** (vs a
    recorded legacy baseline; `--capture-baseline`) + **Phase B Playwright E2E**. `dynamic_findings[]`;
    `/scaffold` sets up Playwright + replay harness when `migration.md §12` enables it; `## Dynamic tests`
    framework recipe. **Phase C visual/CSS regression remains deferred** (the fragile, baseline-heavy tier).

## Throughput (already tracked)

- [ ] **Parallel migration** (`/next-batch` via the Workflow tool) — `TRACKED` → [`future-additional-agents.md`](./planning/future-additional-agents.md) (Candidate 1) + [`future-code-modernization-borrowings.md`](./planning/future-code-modernization-borrowings.md) #7. Depends on ↓.
- [ ] **`unit-migrator` subagent conversion** — `TRACKED` → [`future-subagent-unit-migrator.md`](./planning/future-subagent-unit-migrator.md). The enabler for parallel migration + per-unit context isolation.

---

## Suggested priority (new items only)

1. ~~**Non-UI / background units**~~ — ✅ **DONE (v0.15.0)**: `background` kind + `trigger`, non-route discovery, trigger→target recipe, build+tests-only smoke gate.
2. ~~**Emergent reusable-code extraction + backfill**~~ — ✅ **DONE (v0.15.0)**: `extracted_shared[]` + `/plan` Step 6b backfill.
3. ~~**Cross-unit rollback safety**~~ — ✅ **DONE (v0.15.0)**: data-driven shared-file check, refuse-by-default + `--force-shared`.
4. ~~**Cross-cutting concerns phase**~~ — ✅ **DONE (v0.15.0)**: the Foundation phase — `/foundation` replaces `/auth`, establishes auth + opt-in concerns.
5. ~~**Per-unit plan gate (opt-out)**~~ — ✅ **DONE (v0.15.0)**: gate ON by default, migration-wide `review_mode` set at `/plan` (`plan-first` | `auto`), per-unit `--plan`/`--no-plan`, plus an always-on `/foundation` design gate.
6. ~~**Integration / cutover command**~~ — ✅ **DONE (v0.15.0)**: `/integrate` (idempotent router/nav assembly, whole-app smoke, strangler proxy). · **configuration migration** — still open ("last-mile").
7. ~~**Static performance review**~~ — ✅ **DONE (v0.15.0)**: `perf_*` kinds in `migration-critic`.
8. ~~**Dynamic testing tier (Phase A+B)**~~ — ✅ **DONE (v0.15.0)**: `/verify --dynamic` (API replay + Playwright E2E).

**Remaining open:** configuration migration · global/shared client state · CSS audit (legacy sizing + critic findings) · accessibility (a11y) check · data-layer **bulk** migration · runtime perf (Tier-2) · visual regression (Phase C) · parallel migration (+ `unit-migrator` subagent conversion).
