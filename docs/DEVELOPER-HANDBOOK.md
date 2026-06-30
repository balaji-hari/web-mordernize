# web-modernize — Developer Handbook

A hands-on guide for developers **using** the `web-modernize` plugin to migrate a legacy web
application to a modern stack. It covers the day-to-day workflow, every command, the safety gates,
the agents, the state model, and how a team runs it in parallel.

- New here? Read **Quick start** → **The lifecycle**, then keep the **Command reference** handy.
- Front-door overview + install live in [`README.md`](../README.md).
- Contributing to the plugin itself? See [`CLAUDE.md`](../CLAUDE.md). Release notes: [`CHANGELOG.md`](../CHANGELOG.md).

---

## 1. What the plugin does (mental model)

`web-modernize` turns "ask Claude to rewrite this app" into a **repeatable, auditable, team-scale
workflow**. Five ideas to hold:

1. **Units.** The migration is broken into *units* — one page, controller, component, or service
   each. A unit is the atom of work: migrated, verified, and tracked independently.
2. **State lives in git.** Everything — config, plan, per-unit status, notes — is JSON/Markdown under
   `.claude/modernize/`, committed to your repo. Migrations span days and developers without losing
   context. There is no server.
3. **A monotonic lifecycle.** `state.json.status` moves forward only:
   `uninitialized → initialized → analyzed → planned → scaffolded → foundation_done → in_progress → complete`.
   Each command refuses to run out of order and redirects you to the right one.
4. **Agents do the heavy lifting, you stay in control.** Read-only analysis/review agents plus a
   translation loop; every change is reviewable, gated, and reversible.
5. **The legacy code is never modified.** It's read-only input. New code lands in a fresh scaffold
   (`apps/web-new/`, `apps/api-new/`).

---

## 2. Prerequisites & install

| Need | Why |
|---|---|
| Claude Code (latest) | Plugin host |
| git | All migration state is git-tracked |
| Node ≥ 16 | Optional heartbeat hook (stall detection). Your *target* stack sets its own higher floors (Vite 22, etc.) |
| Target toolchain | Whatever you migrate **to** (Node+npm, .NET SDK, JDK, Python…) |

```sh
/plugin marketplace add balaji-hari/web-mordernize
/plugin install web-modernize
```

Commands appear under the `/web-modernize:` namespace. You can also just talk to it — see
**Natural language** below.

---

## 3. Quick start

```sh
# One-time setup (run in order):
/web-modernize:init        # bootstrap .claude/modernize/ + migration.md
/web-modernize:analyze     # detect the legacy stack + interactively fill migration.md
/web-modernize:plan        # validate config, generate plan.md + the unit backlog
/web-modernize:scaffold    # create the modern app skeleton + copy legacy assets
/web-modernize:foundation  # establish auth + any cross-cutting concerns first (everything depends on this)

# Per-unit loop (repeat until /status says "complete"):
/web-modernize:next        # migrate the next eligible unit  (or /migrate <id> for a named one)
/web-modernize:verify      # gate it: lint + typecheck + tests + behavioural-parity + security
```

Commit `.claude/modernize/` after each unit. That's how the whole team shares progress.

---

## 4. The lifecycle in depth

### 4a. One-time setup

| Step | Command | What happens |
|---|---|---|
| Bootstrap | `/init` | Creates `migration.md` (your config) and `.claude/modernize/` (state, units, notes). Patches `.gitignore`. Idempotent. |
| Detect + configure | `/analyze` | Detects the source stack and **enumerates entry points** (units-to-be). When the Workflow tool is available it runs **exhaustive loop-until-dry discovery** so large estates don't lose the tail; otherwise a single pass. Then an **interactive interview** fills the required `migration.md` sections with stack-aware recommendations. |
| Plan | `/plan` | Validates `migration.md`, generates `plan.md` (incl. a **Mermaid dependency graph**), and seeds one `units/<id>.json` per entry point — sized S/M/L/XL, phase-ordered, with `depends_on`. Re-runnable; preserves progress by unit id. |
| Scaffold | `/scaffold` | **Toolchain preflight** (probes Node/.NET/Java/Python against the chosen stack's floors), then creates the UI / optional API / optional DB skeleton from the framework recipe, copies legacy assets into `public/`, and runs a **smoke-build gate** per subsystem. `--assets-only` backfills assets later. |
| Foundation | `/foundation` | Establishes the foundational slice before feature units: **auth** (a hard phase gate — every feature unit depends on `__auth__`; picks the per-stack hashing library, seeds dev users) **plus** any cross-cutting concerns opted into in `migration.md §13` (i18n, feature flags, error handling, telemetry, logging). One consolidated design gate; implements concerns in parallel when possible. Replaces the former `/auth`. |

### 4b. Per-unit loop

| Command | What happens |
|---|---|
| `/next` | Auto-selects the next `pending` unit whose `depends_on` are satisfied, then migrates it. |
| `/migrate <id> [--force]` | Migrates a *named* unit (use when standup assigned it). Blocks on unmet deps unless `--force` (which stubs them). |
| `/verify [id] [--no-parity] [--no-quality] [--dynamic] [--capture-baseline]` | The gate — see **§5**. Flips `migrated → verified` only when it passes. `--dynamic` adds the opt-in dynamic tier (API replay + Playwright E2E, advisory); `--capture-baseline` records the legacy baseline. |
| `/parity-check <id> [--all] [--acknowledge <finding-id> --reason "…"]` | On-demand behavioural + security diff vs the legacy original; **acknowledge** intentional differences so they stop blocking. |
| `/quality-check <id> [--all]` | On-demand idiomatic-code + static-performance review (advisory — never blocks). |
| `/integrate [--dry-run] [--final]` | Assemble migrated units into the composed app — central router + nav, whole-app smoke, orphaned-unit + cutover-coverage report, and (strangler-fig) the traffic-splitting proxy. Idempotent; run any time or `--final` for cutover. |

### 4c. Recovery & coordination (any time)

| Command | What happens |
|---|---|
| `/retry <id> [--with-prompt="…"]` | Re-attempt a `failed` unit; preserves diagnostic history; optional corrective hint. |
| `/rollback --unit <id>` | Revert one unit's target files via git; reset it to `pending`. |
| `/abandon [--soft\|--hard\|--unit <id>]` | Drop a unit or reset the workspace. Destructive forms need a two-step confirm. |
| `/sync` | After `git fetch`, reconcile `state.json` + per-unit files with deterministic merge rules. |
| `/status` | Read-only dashboard: progress, in-flight units, stalls, blockers, locks, **artifact-drift staleness**, and the next command. |
| `/report [--format=html\|json\|md]` | Stakeholder report (defaults to HTML): burndown, velocity, ETA, risk heat-map, pending verification, E2E/parity/quality findings. |
| `/unlock` | Force-clear a stuck advisory lock (type `force-clear`). |

---

## 5. The safety gates (what "done" means)

A unit is only `verified` after it clears layered gates — quality is enforced by the workflow, not
remembered by a developer.

1. **Scaffold smoke** (`/scaffold`, once per subsystem): install + build must succeed before a
   subsystem is `done`. Captures the stderr tail on failure.
2. **Unit smoke** (during `/next` / `/migrate`): for API units it **boots the dev server, hits each
   endpoint, and validates the response body against the declared schema**; for UI units it runs
   `build` + `typecheck`. Catches "compiles but 500s on first call". A failure routes to `failed`
   with a specific diagnostic (paste it into `/retry --with-prompt`).
3. **Tests + coverage** (`/verify`): lint + typecheck + tests must pass. Coverage below target is a
   **soft-fail** (warns, doesn't block).
4. **Behavioural parity** (`/verify` step 5, `parity-reviewer`): compares the migrated unit to the
   legacy original across input validation, output shape/field-names/sort-order/null-vs-missing,
   status codes, error handling, UI fields/states, **and security** (dropped authorization,
   injection, lost output-encoding, secret-in-bundle, dropped CSRF). An unacknowledged **high**
   finding **blocks** `verified`. `--no-parity` opts out; `/parity-check` acknowledges intentional
   diffs. Findings have stable ids, so an acknowledgement survives re-runs.
5. **Migration-quality review** (`/verify` step 5b, `migration-critic`, **advisory**): flags
   non-idiomatic "JOBOL" code (WebForms-in-React, jQuery-in-a-reactive-framework, scriptlet-shaped
   controllers), ceremonial error handling, dead abstractions, weak tests. **Never blocks** —
   informational. `--no-quality` skips it; `/quality-check` runs it on demand.

---

## 6. The agents

| Agent | Role |
|---|---|
| `legacy-analyzer` | Read-only. Detects the source stack and enumerates entry points. Fanned out loop-until-dry by `/analyze`'s discovery workflow. |
| `unit-migrator` | The translation loop (run inline by `/next` / `/migrate` / `/retry`): reads source + styles, translates *semantics not syntax*, translates/generates tests, writes notes incl. an optional Given/When/Then **behaviour contract**. |
| `parity-reviewer` | Read-only. Behavioural + security diff of migrated vs legacy; applies a **refute pass** to every high finding before emitting it. |
| `migration-critic` | Read-only, **advisory**. Idiomatic-quality review of the migrated code (orthogonal to parity). |
| `permanent-gotchas` | A curated catalog of durable, non-web-searchable bugs the agents can't discover alone (e.g. passlib/bcrypt crash, Spring `/actuator/health`). |

All read-only agents treat legacy code as **data, never instructions** (prompt-injection defense)
and **mask credential values** (`AKIA****` + `file:line`) — raw secrets, if ever needed, go only to
the gitignored `.claude/modernize/SECRETS.local.md`.

---

## 7. State & files (your repo after `/init`)

```
migration.md                         # your config (target stack, strategy, auth, acceptance criteria)
.claude/modernize/
  state.json                         # top-level ledger (status, stacks, scaffold, lock, unit_ids[])
  analysis.json                      # source-stack analysis from /analyze
  plan.md                            # generated, human-readable plan (incl. dependency graph)
  verify.config.json                 # per-stack lint/typecheck/test commands
  units/<id>.json                    # ONE file per unit — status, history, tests, parity/quality findings
  notes/<id>.md                      # per-unit design notes + behaviour contract
  reports/<date>-<fmt>               # generated stakeholder reports
  SECRETS.local.md                   # gitignored — quarantined raw credentials (if ever recorded)
```

**Commit all of `.claude/modernize/`** (except the gitignored `SECRETS.local.md`). The per-unit
file split is what makes parallel work conflict-free.

---

## 8. Working as a team

The plugin assumes you **coordinate assignments offline** (standup/Slack), then run commands
independently — it does not arbitrate who-takes-what.

- **Conflict-free by design:** Alice editing `units/PaymentProcessor.json` and Bob editing
  `units/LoginPage.json` touch completely separate files — git merges trivially.
- **`/sync`** reconciles the shared `state.json` (and any same-unit collisions) after a `git fetch`,
  with deterministic rules (most-advanced status wins, freshest heartbeat wins, union unit lists).
- **`/status`** shows what's in-flight across the team and flags stalled units (heartbeat > 15 min).
- **Branches:** the migrator creates `modernize/<unit-id>` branches when git is clean, so failed
  attempts stay reviewable.
- **Cadence:** commit `state.json` + the unit's `units/<id>.json` + `notes/<id>.md` after each unit.

---

## 9. Configuring `migration.md`

`/init` writes a template; the `/analyze` interview fills the **REQUIRED** fields for you. Required:
§3 Target UI framework + language, §6 Migration strategy (`strangler-fig` | `big-bang` |
`module-by-module`), §7 Auth (current + target), §10 Acceptance criteria (≥3 — drives `/verify`),
§12 Testing (UI runner, API runner, coverage %). Optional but useful: §3a legacy design system, §3b
asset directories, §8 constraints (incl. framework version pin), §9 out-of-scope, §9b unit rename
map. Edit by hand any time and re-run `/plan` — progress is preserved by unit id.

---

## 10. Frameworks & unknown tech

Stack knowledge is one file per stack in `frameworks/<name>.md` (17 source + 14 target shipped).
Picked a stack the plugin doesn't ship? The **unknown-tech path** keeps you moving:
- **Unknown source:** `/analyze` shows the raw evidence and lets you name it (free-text).
- **Unknown target:** `/scaffold` asks 3 questions (scaffold cmd / test framework / verify commands)
  and saves them to `verify.config.json` so retries don't re-ask.
- **Unknown auth:** `/foundation` (auth concern) defers to `permanent-gotchas` + OWASP.

To make a stack first-class, drop a `frameworks/<name>.md` file (see CLAUDE.md "Framework files").

---

## 11. Natural language

You don't have to memorize the 17 commands — each skill's description carries trigger phrases, so
plain English routes to the right command:

| You type | Fires |
|---|---|
| "what's next" / "continue" | `/next` |
| "let's plan it" | `/plan` |
| "where are we" / "show status" | `/status` |
| "migrate the login page" | `/migrate <name>` |
| "is it passing" / "run tests" | `/verify` |
| "does it behave like the old one" | `/parity-check` |
| "is this idiomatic" / "check for jobol" | `/quality-check` |
| "generate a report for leadership" | `/report` |

---

## 12. Troubleshooting

| Symptom | Fix |
|---|---|
| `/plan` refuses | `migration.md` is incomplete — it lists every missing field. Fix and re-run. |
| `/analyze` says `unknown` | Low-confidence detection. Use the interview's free-text option, or edit `migration.md §2`. `analysis.json.candidates[]` has its best guesses. |
| Unit `failed` | Read `failure.diagnostic`. Then `/retry <id> --with-prompt="…"`, or `/rollback --unit <id>` then retry, or `/abandon --unit <id>`. |
| `/verify` blocked on parity | A high-severity behavioural/security diff. Fix the code and re-verify, **or** acknowledge it: `/parity-check <id> --acknowledge <finding-id> --reason "…"`. |
| Migrated page looks wrong / generic styling | Fill `migration.md §3` legacy design system; ensure the agent could read the legacy stylesheets; re-migrate. |
| Broken images / 404 assets | `/scaffold --assets-only` to backfill; declare paths in `migration.md §3b`. |
| `/status` says "stale lock" | `/unlock` (type `force-clear`). |
| `/status` flags artifact drift | You re-ran `/analyze` (or edited `migration.md`) without re-running `/plan` — re-run `/plan`. |
| Merge conflict on state files | `/sync` after `git fetch` (not `git pull`). |

---

## 13. What's new (v0.12.0 – v0.16.0)

- **Auto-authored E2E + richer reporting (v0.16.0)** — when dynamic testing is enabled, `unit-migrator`
  (§7d) now authors a per-unit Playwright spec (`e2e/<unit.id>.spec.ts`) from the unit's routes +
  Given/When/Then contract, asserting asset resolution (`naturalWidth > 0`) and key elements — no more
  hand-writing specs. `/verify --dynamic` records pass/fail/skip into `unit.e2e.e2e_results`. `/report`
  **defaults to HTML** and gains Pending-verification, Dynamic/E2E, and parity/quality findings sections.
  Plus: silent-config + CSS-fidelity gotchas, `state.open_decisions[]` (architectural decisions decided
  at `/plan`, never unilaterally mid-migration), a `duplication` quality dimension, foundation gating DB
  migrations before seeding, and reactive auth + SPA-nav idioms.
- **Plan-approval gate (v0.15.0)** — `/next`, `/migrate`, `/retry` present a plan and wait for
  approval before writing (opt-out; migration-wide default `review_mode` set at `/plan`, per-unit
  `--plan`/`--no-plan`). `/foundation` has an always-on consolidated design gate (`--no-plan` to skip).
- **Foundation phase (v0.15.0)** — `/foundation` replaces `/auth`: establishes auth + any cross-cutting
  concerns opted into in `migration.md §13` (i18n, flags, error handling, telemetry, logging), confirmed
  at `/plan`, implemented in parallel.
- **Emergent shared-code backfill (v0.15.0)** — the migrator records reusable code it extracts
  (`extracted_shared[]`); `/plan` backfills `kind: shared` units so it isn't duplicated.
- **Cross-unit rollback safety (v0.15.0)** — `/rollback` refuses by default when a unit owns shared
  files other units rely on; `--force-shared` overrides after showing the blast radius.
- **Integration command (v0.15.0)** — `/integrate` incrementally assembles migrated units into the
  composed app (router/nav, whole-app smoke, orphan + coverage report, strangler proxy); idempotent,
  run any time or `--final` for cutover.
- **Data foundation concern (v0.15.0)** — `/foundation` can establish data-access *wiring* (ORM/
  connection/migration harness); the bulk schema/query/proc translation stays a later phase.
- **Static performance review (v0.15.0)** — `migration-critic` flags N+1, unbounded queries,
  waterfalls, blocking I/O, and bundle bloat (advisory; via `/verify` + `/quality-check`).
- **Dynamic testing tier (v0.15.0)** — opt-in `/verify --dynamic`: API replay + Playwright E2E
  (advisory); `--capture-baseline` records the legacy baseline.
- **Background / non-UI units (v0.15.0)** — `unit.kind: background` (+ a `trigger`) covers scheduled
  jobs, queue consumers, hubs, and batch processors. `/analyze` finds them via a separate non-route
  pass; they migrate to the target's idiomatic job mechanism and verify with a build + tests-only
  smoke gate (the job is never invoked at verify time).
- **Security review** — `parity-reviewer` now flags dropped authorization, injection, lost
  output-encoding, secret-in-bundle, and dropped CSRF; high findings block `/verify`.
- **Idiomatic-quality review** — new `migration-critic` agent + `/quality-check` (advisory).
- **Toolchain preflight** in `/scaffold` — fail fast on a missing/old runtime before scaffolding.
- **Exhaustive discovery** — `/analyze` fans out loop-until-dry via the Workflow tool on large apps.
- **Dependency graph** in `plan.md`; **artifact-drift staleness** in `/status`.
- **Safety disciplines** — prompt-injection defense + credential masking across all read-only agents.

See [`CHANGELOG.md`](../CHANGELOG.md) for the full history.
