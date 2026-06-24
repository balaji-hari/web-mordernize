# Plan: Data-layer / database migration as a gated phase

## Context

The plugin covers **detect → plan → scaffold → auth → migrate units → verify → report**, but the
**data layer has no execution path**. It is a configuration field (`migration.md §5`,
`state.target_stack.db`) and a scaffold concern, but nothing actually translates the legacy schema,
queries, stored procedures, or ORM mappings to the target stack.

This doc captures that gap and the design we converged on. **Implementation is not committed** — we
will pick it up later.

### What exists today (precise)

`/scaffold` only **stubs** the database:

- `schema-migrate-to-<X>`: creates `db/migrations/` with a **placeholder** `0001_init.sql` + a README
  (`skills/scaffold/SKILL.md:120`).
- `replatform-to-<Y>`: creates `db/README.md` describing the plan and explicitly **"defer[s] actual
  migration scripts to a later phase"** (`skills/scaffold/SKILL.md:121`).
- DB smoke test is hardcoded `"smoke": "n/a"` (`skills/scaffold/SKILL.md:227`).

That "later phase" **does not exist**. There is:

- **No skill or agent** that translates schema / inline SQL / stored procedures / DAO patterns /
  ORM mappings (EF6, NHibernate, Hibernate, iBatis) to the target ORM (EF Core, Prisma, Drizzle,
  TypeORM, JPA).
- **No `role: target-db` framework files** — `frameworks/` only ships `source`, `target-ui`, and
  `target-api` roles.

The shared data layer is also homeless in the unit model: it is neither auth nor any single feature
unit, so no unit owns it.

---

## The core design decision: gate it like auth (do NOT make it a soft dependency)

The obvious-but-wrong design is to seed the data layer as ordinary `kind: data` units that flow
through `/next`, gated only by per-unit `depends_on` edges. **We rejected this.** It can be silently
skipped two ways:

1. **Missing edge.** Pages depend on the data units only through `depends_on`. `/plan` has to draw
   *every* edge correctly. Miss one, and `/migrate ThatPage` proceeds against tables that were never
   migrated.
2. **`--force`.** `/migrate <unit> --force` exists precisely to bypass dependency checks. A user in a
   hurry forces straight past the data units.

Either path yields a page wired to a database that isn't there — and the unit's tests may still
pass, so it is a **silent failure** (the exact class of bug `parity-reviewer` was built to catch).

### The fix

Treat the data layer the way the plugin **already treats auth**: not as a soft dependency, but as a
**hard phase gate**. You cannot accidentally skip auth today because auth is a *phase*
(`scaffolded → auth_done`), and `/next` / `/migrate` refuse to touch any feature unit until
`state.status` reaches `auth_done`. `--force` can skip a *unit-to-unit* dependency, but it cannot
jump a *phase gate*.

The data layer deserves the same structural gate:

```
uninitialized → initialized → analyzed → planned → scaffolded
  → auth_done → data_done → in_progress → complete
                ^^^^^^^^^  NEW
```

No feature unit — via `/next`, `/migrate`, or even `/migrate --force` — can run until the data phase
is complete. It becomes impossible to miss.

**Why this is not scenario-creep** (cf. recorded preference "patterns over scenarios"): auth and the
data layer are the *two* foundational slices every feature depends on. This reuses the existing
foundational-slice pattern the plugin already ships for auth — it is not a per-scenario synthetic
unit, required field, or one-off hack.

---

## Designs considered

| Design | Surface | Bypass-proof? | Verdict |
|---|---|---|---|
| **A — soft-dependency units** | `kind: data` units in `/next`, gated only by `depends_on` | **No** — missing edge or `--force` skips it | **Rejected** |
| **B1 — dedicated phase + command** | new `/web-modernize:migrate-data` skill + `data_done` phase | Yes — phase gate | **Recommended** |
| **B2 — gated `/next`** | reuse `/next`, but while `status == auth_done` it only offers `kind: data` units; transition to `data_done` when all are verified | Yes — phase gate | Acceptable lighter-surface alternative |

**Recommendation: B1.** It is the most explicit (one command that does exactly what it says), mirrors
`/auth` one-to-one, and is the clearest for the user — no "`/next` quietly behaves differently for
some units" surprise. B2 avoids adding a command but reintroduces the routing-indirection confusion
and is harder to explain. Whoever implements may pick B2 if minimizing command surface is paramount;
the gate semantics are identical either way.

---

## Provision vs translate — two moments, not one

A recurring point of confusion: the database is touched at **two** different moments, and neither is
"all inside `/scaffold`."

| Step | Owner | Nature |
|---|---|---|
| **Provision** the empty target DB + ORM wiring (`prisma init`, `dotnet ef` setup, migrations dir) | `/scaffold`, reading a new `role: target-db` framework recipe | one-shot, bootstrap |
| **Translate** schema / queries / stored procs / ORM mappings | the new **`data-layer-migrator`** agent, run in the **data phase** (B1: `/migrate-data`; B2: first `/next` runs) | iterative, verifiable, retryable |

`/scaffold` keeps doing provisioning (roughly what it does now), extended only to read a target-db
recipe for the scaffold command. The **actual migration runs through an agent in its own phase** —
*not* inside `/scaffold`. The translation can be wrong, needs checking ("do my new queries return the
same rows?"), and may need a retry — that is the `migrate → verify → retry` loop's shape, which
`/scaffold` (a one-shot transition) cannot provide.

Timeline as the user experiences it (Design B1):

```
/scaffold      → creates the EMPTY new DB + ORM wiring (shell, no real tables)
/auth          → auth slice                       (→ auth_done)
/migrate-data  → translate schema, queries, procs (→ data_done)   ← the real DB migration
/next  ×N      → feature pages (their tables now exist)
```

---

## The `data-layer-migrator` agent

A new read/write agent, `agents/data-layer-migrator.md`, dispatched for the data phase. It **earns its
place** under the rubric in `future-additional-agents.md` (a new agent must offer a genuinely
separable concern):

- **Different source files** — schema DDL, stored procedures, ORM mapping files, DAO/repository
  classes — not pages/controllers.
- **Different target** — ORM models + migration files, not UI components or HTTP handlers.
- **Different failure mode** — data integrity / query-result equivalence, not UI/endpoint parity.

It is explicitly **not**:

- a per-stack translator (`ef-to-prisma`, etc.) — per-stack recipes live in `frameworks/*.md` as data,
  consistent with the framework-file model.
- a fragment of `unit-migrator` — it is a distinct concern with its own verification, not a piece
  carved off the feature-translation loop.

Algorithm (sketch):

1. Read the legacy data-access sources for the data unit (`unit.source_paths`): schema, SQL,
   stored procs, ORM mappings.
2. Read the chosen `frameworks/<target-db>.md` recipe (model conventions, migration tooling,
   query-builder idioms).
3. Emit target ORM models + migration files; translate queries / procs to the target query layer.
4. **Verify by equivalence**, not just "compiles": where feasible, assert the migrated query returns
   the same row shape / ordering / null-vs-missing semantics as the legacy one. This is the data-layer
   analogue of `parity-reviewer`'s checks — consider a new `parity_findings.kind` value
   (`"query_result"` / `"schema_shape"`) handled by `parity-reviewer`, rather than a second reviewer.

---

## New `frameworks/<name>.md` — `role: target-db`

Add a new framework role so the data layer is a one-file drop-in like every other stack. Initial set:

- `prisma`, `drizzle` (TypeScript/Node targets)
- `ef-core` (.NET target)
- `typeorm` (Node target, ORM-heavy migrations)
- `jpa-hibernate` (Spring Boot target)

Each file's sections (subset of the standard framework headings):

- `## Scaffold` — provisioning command(s) `/scaffold` runs (`prisma init`, `dotnet ef` setup, etc.).
- `## Models` — model/entity conventions the migrator follows.
- `## Migrations` — the migration tool + how to generate/apply a migration.
- `## Query translation notes` — idioms for translating common legacy patterns (raw SQL → query
  builder, stored proc → service method, eager/lazy loading).
- `## Verification` — how to assert query-result equivalence for `/verify`.

Cross-cutting data rules (e.g., decimal/money precision, timezone handling, N+1 traps) stay in
`agents/permanent-gotchas.md`, not duplicated per file.

---

## State and schema impact

- **State machine:** insert `data_done` between `auth_done` and `in_progress`. Each downstream skill's
  precondition shifts accordingly (`/next` and `/migrate` now require `status >= data_done` for
  feature units; the data phase requires `status == auth_done`).
- **Unit kind:** add `"data"` to the allowed `unit.kind` values (additive to `unit.schema.json`).
- **Implicit dependency token:** mirror `__auth__` with a `__data__` token that feature units carry,
  satisfied by the `data_done` transition. This keeps the gate consistent with the existing auth
  mechanism.
- **`schema_version`:** adding a status enum value and a `kind` value is additive (existing files
  still validate), but it changes the state machine. Decide whether to bump `schema_version`. Either
  way, **write no migration code** (recorded constraint: no production users; a bump just requires a
  fresh `/init` after deleting `.claude/modernize/`).

---

## Files to change (when implemented)

| File | Change |
|---|---|
| `agents/data-layer-migrator.md` | **NEW.** Read/write agent for the data phase (see algorithm above). |
| `frameworks/{prisma,drizzle,ef-core,typeorm,jpa-hibernate}.md` | **NEW.** `role: target-db` recipes. |
| `skills/migrate-data/SKILL.md` | **NEW** (Design B1). The data-phase driver; `auth_done → data_done`. (Design B2: instead, edit `skills/next/SKILL.md` to gate to `kind: data` units while `status == auth_done`.) |
| `skills/plan/SKILL.md` | Seed `kind: data` units from `migration.md §5`; add the `__data__` token to feature units' `depends_on`. |
| `skills/scaffold/SKILL.md` | DB scaffold step reads `frameworks/<target-db>.md` `## Scaffold` instead of writing a placeholder; still provisioning-only. |
| `skills/verify/SKILL.md` | Recognize `kind: data` units; run query-result-equivalence verification (delegate to `parity-reviewer` with the new finding kinds). |
| `skills/{next,migrate}/SKILL.md` | Precondition shifts to `status >= data_done` for feature units; dispatch `kind: data` to `data-layer-migrator` if any data work remains (defense in depth even with the phase gate). |
| `agents/parity-reviewer.md` | Add `query_result` / `schema_shape` finding kinds. |
| `templates/state.schema.json` | Add `data_done` to the `status` enum. Possible `schema_version` bump (no migration code). |
| `templates/unit.schema.json` | Add `"data"` to `kind`. |
| `templates/migration-interview.json` | Optional: a target-db question (resolve options from `role: target-db` framework files). |
| `agents/legacy-analyzer.md` | Optional: detect the legacy data-access stack to recommend a target-db. |
| `README.md`, `CHANGELOG.md`, `.claude-plugin/{plugin,marketplace}.json` | Doc + version bump (minor: new skill + agent + frameworks). |

---

## What this explicitly does NOT do

- **No soft-dependency-only design** (Design A) — the gate is the whole point.
- **No per-stack translator agents** — stack knowledge stays in `frameworks/<target-db>.md`.
- **No data-migration / ETL of production rows.** Scope is *code* migration (schema + data-access +
  query translation), not moving live data between databases. Live-data cutover is an ops concern,
  out of scope here (note it in `migration.md §8` constraints if relevant).
- **No schema migration code in the plugin** — `schema_version` bumps require a fresh `/init`.
- **No new required `migration.md` field beyond what §5 already provides** — patterns over scenarios.

---

## Versioning

New skill + new agent + new framework files = **minor** bump. The `data_done` status enum addition is
additive; bump `schema_version` only if you decide the state-machine change warrants it (no migration
code either way). Mirror across `plugin.json` / `marketplace.json` / `CHANGELOG.md`; tag `vX.Y.0`.

---

## Verification (when implemented)

In a legacy app with a real data layer (e.g., an ASP.NET WebForms app using EF6, or a Spring MVC app
using Hibernate):

1. Run through `/init → /analyze → /plan`. Confirm `/plan` seeds `kind: data` units from §5 and adds
   `__data__` to feature units' `depends_on`.
2. After `/scaffold` + `/auth`, attempt `/migrate SomeFeaturePage --force`. **Confirm it refuses** —
   the phase gate blocks feature units while `status == auth_done`. (This is the regression test for
   the bypass bug that motivated the gate.)
3. Run the data phase (`/migrate-data` for B1, or `/next` for B2). Confirm schema + queries translate,
   `/verify` runs query-result-equivalence checks, and `status` advances to `data_done`.
4. Now `/next` offers feature units; confirm they migrate against the real (migrated) tables.
5. **Extensibility check:** drop a hand-written `frameworks/<custom-db>.md` and confirm `/scaffold`
   provisioning + the migrator pick it up with no other edits.

---

## Relationship to other future docs

- `future-additional-agents.md` — `data-layer-migrator` is a fourth agent that passes that doc's
  separability rubric; consider folding a one-line pointer into its roster.
- `future-subagent-unit-migrator.md` — once `unit-migrator` becomes a true subagent with by-`kind`
  dispatch, `data-layer-migrator` slots into the same dispatch table cleanly.
- `parity-reviewer` (shipped v0.11.0) — extended here with data-layer finding kinds rather than a
  separate reviewer.
