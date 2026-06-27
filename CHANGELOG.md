# Changelog

All notable changes to the `web-modernize` plugin are documented here. Versioning follows [Semantic Versioning](https://semver.org/).

## [0.12.0] - 2026-06-27

Adopts the first six "borrowings" from the sibling `code-modernization` plugin (catalogued in `docs/planning/future-code-modernization-borrowings.md`) — the disciplines and one agent that harden *understanding, verification rigor, and safety* around the migration, without touching the per-unit execution loop that is this plugin's strength. All changes are additive: no `state.schema.json` `schema_version` bump, no removed/renamed commands. Teams pull this with `/plugin uninstall web-modernize && /plugin install web-modernize`; **no `.claude/modernize/` reset required**.

### Added
- **`agents/migration-critic.md`** (borrowing #3) — new read-only subagent that reviews a migrated unit's TARGET code for **idiomatic quality**, orthogonal to `parity-reviewer`'s behavioural check. Flags "JOBOL" / legacy-paradigm leakage (WebForms-in-React `useEffect`-postback emulation, jQuery-style imperative DOM in a reactive framework, scriptlet/code-behind-shaped controllers, God-components), ceremonial error handling, single-use abstractions, tests that exercise paths instead of pinning behaviour, and on-call/operability gaps. Returns `quality_findings[]` + a one-line headline. **Advisory only — never blocks** the `migrated → verified` transition.
- **`/web-modernize:quality-check`** (`skills/quality-check/SKILL.md`) (#3) — on-demand migration-quality review for one unit or `--all`; the sibling of `/parity-check` minus the acknowledge/gate machinery (quality findings don't block, so there's nothing to suppress). Brings the user-facing command count to **17**.
- **`templates/unit.schema.json` — `quality_findings[]`, `quality_reviewed_at`, `quality_headline`** (#3) — additive fields holding the migration-critic's output. No `schema_version` bump.
- **Toolchain preflight in `/web-modernize:scaffold`** (#6) — a fast read-only check at the top of scaffold that reads each chosen target's runtime floor from its `frameworks/<name>.md` and probes the binaries (Node/npm, Python, .NET SDK, Java/Maven). Missing required runtime → **stop before any half-scaffold** with the install one-liner; below-floor → warn and ask; all green → proceed. Unknown targets skip the probe and fall through to the existing follow-up. Skipped under `--assets-only`.
- **`SECRETS.local.md` quarantine** (#2) — `/web-modernize:init` now gitignores `.claude/modernize/SECRETS.local.md`, the only place a raw discovered credential may be written.

### Changed
- **`agents/parity-reviewer.md`** — three additions: (#5) a **security-parity dimension** (dropped authorization, injection, lost output-encoding, secret-in-bundle, dropped CSRF) with five new finding kinds (`security_authz_dropped`, `security_injection`, `security_output_encoding`, `security_secret_exposure`, `security_csrf`), default severity `high`, gated by an exploit-scenario discipline; (#4) a **refute pass** that requires every `high` finding to have a one-sentence consumer-visible impact before it's emitted, raising precision on the one gate that can trap a working migration; (#1/#2) **untrusted-input** and **secret-masking** rules.
- **`templates/unit.schema.json`** — the five `security_*` values added to the `parity_findings[].kind` enum (#5, additive).
- **`skills/verify/SKILL.md`** — (#3) a new **advisory step 5b** runs `migration-critic` after the parity gate (graceful-degrade, never blocks; `--no-quality` opts out) and prints a `quality:` line; (#5) clarifies that security-kind `high` parity findings block exactly like any other high and are acknowledged the same way via `/parity-check`.
- **`agents/legacy-analyzer.md`, `agents/unit-migrator.md`** — (#1) untrusted-input and (#2) secret-masking rules: legacy code is data, never instructions; credential values are masked (`AKIA****`) + `file:line` and never written into `analysis.json`, `notes/*.md`, symbol maps, or any tracked artifact; instruction-shaped text is reported, not obeyed.

### Why this is a minor, not a patch
A new user-facing command (`/web-modernize:quality-check`), a new agent, a new advisory pass in `/verify`, a new scaffold gate that can stop a run, and a new behaviour-blocking finding class (security-parity highs). User-visible surface and workflow behaviour both change.

### Why this is a minor, not a major
No `state.schema.json` `schema_version` bump. The new `unit.schema.json` fields and the five `parity_findings[].kind` values are additive and optional — existing unit files validate as-is. No removed or renamed skills/commands. Migrations mid-flight keep working; the new security highs apply on the next `/verify`, and `--no-parity` / `--no-quality` / acknowledgement remain available.

## [0.11.0] - 2026-05-31

Closes the biggest silent-failure gap in the workflow: until now `/verify` proved a migrated unit was *valid* (lint + typecheck + tests pass) but never that it *behaved like the legacy original*. Tests green, behaviour subtly different — a flipped default sort, a tightened validation rule, a renamed response field, a dropped error path — was an invisible class of regression. This release adds a behavioural-parity reviewer that compares the migrated target against the legacy source and reports observable differences, and wires it into `/verify` as a gate on the `migrated → verified` transition.

Implements **Candidate 2** from `docs/future-additional-agents.md` (the doc's recommended-first addition). The parity-reviewer is a real read-only subagent in the `legacy-analyzer` mould (isolated context, returns structured JSON, no user interaction) — deliberately **not** the inline-read shape of `unit-migrator`, because parity review needs neither interactive prompts nor file mutations and benefits from an isolated context window.

### Added
- **`agents/parity-reviewer.md`** — new read-only subagent (`model: sonnet`, `disallowedTools: Write, Edit, NotebookEdit`). Given a unit's `id`, `kind`, `source_paths[]`, and `target_paths[]`, it reads both sides and reports observable behavioural differences across input (required/optional, validation, normalisation), output (shape, field names, types, sort order, null-vs-missing, status codes, pagination), error handling, UI (fields, client validation, submit/redirect, error states), and business-logic/edge-case dimensions. Returns a single JSON block of `parity_findings[]` with a `high/medium/low` severity rubric; emits nothing when behaviour matches. False-positive guardrails: identical-but-differently-expressed behaviour is not flagged, intentional changes documented in notes/acceptance-criteria lean to medium/low, and genuine unknowns (e.g. a stubbed unmigrated dep) go to `warnings[]` rather than being invented as `high`. Finding `id`s are content-derived so an acknowledgement survives a re-run on unchanged code but a *changed* behaviour re-surfaces.
- **`/web-modernize:parity-check`** (`skills/parity-check/SKILL.md`) — standalone on-demand parity review for one unit (`<unit-id>`) or all migrated/verified units (`--all`). Persists findings to the unit and prints them grouped by severity. Also the **acknowledge** path: `--acknowledge <finding-id> --reason "…"` (or an interactive prompt after a single-unit review) records an intentional difference in `parity_acknowledged_diffs[]` so it stops blocking `/verify`. Reviewing never changes a unit's `status` — the gate itself lives in `/verify`.
- **`templates/unit.schema.json` — `parity_findings[]`, `parity_acknowledged_diffs[]`, `parity_reviewed_at`** — additive fields. `parity_findings[]` is the reviewer's output (replaced wholesale each run); `parity_acknowledged_diffs[]` holds `{ id, by, at, reason }` entries that suppress matching high-severity findings from the gate; `parity_reviewed_at` timestamps the last comparison so staleness is visible. No `schema_version` bump.

### Changed
- **`skills/verify/SKILL.md` — behavioural-parity gate** — new step 5, run after the lint/typecheck/test thresholds pass (and skipped when they don't, since the unit can't reach `verified` anyway). Launches `parity-reviewer`, persists `parity_findings` + `parity_reviewed_at`, and computes *blocking* findings = `severity: high` not present in `parity_acknowledged_diffs[]`. The `migrated → verified` transition now requires both the existing thresholds AND zero blocking parity findings; medium/low findings are surfaced as info but never block. New `--no-parity` flag opts out for fast iteration. Graceful degrade: if the reviewer errors or returns malformed JSON, `/verify` records `verification.parity = "review-unavailable"` and proceeds rather than trapping a working migration in `migrated`. Blocking findings are printed inline (legacy → migrated + recommendation) with the two ways forward — fix and re-verify, or acknowledge via `/parity-check`.

### Why this is a minor, not a patch
Adds a new user-facing slash command (`/web-modernize:parity-check`), a new agent, and a new gate that changes when `/verify` flips a unit to `verified`. A unit that previously verified on green tests can now stay `migrated` if it has an unacknowledged high-severity behavioural difference — a behaviour change at the workflow level, not just a doc tweak.

### Why this is a minor, not a major
No `state.schema.json` `schema_version` bump. The three new `unit.schema.json` fields are additive and optional — existing unit files validate as-is and units never reviewed simply carry no `parity_findings`. No removed or renamed skills/commands. Teams pull this with `/plugin uninstall web-modernize && /plugin install web-modernize`; **no `.claude/modernize/` reset required**. Migrations already mid-flight keep working; the gate applies to the next `/verify` run, and `--no-parity` (or acknowledging) is always available if a team wants the old behaviour for a unit.

## [0.10.0] - 2026-05-31

UX overhaul shipping three coordinated changes that transform the plugin from "memorize 15 slash commands + hand-edit migration.md" into "type plain English; the plugin walks you through choices; unknown tech is a graceful path, not a dead end."

### Added

- **Interactive `/analyze` interview** — after auto-filling `migration.md §2` (source stack), `/analyze` now walks the user through the remaining REQUIRED sections (§3 UI, §4 API, §6 strategy, §7 auth, §12 testing) via `AskUserQuestion` prompts. Each option list is rendered from `templates/migration-interview.json`, with source-stack-aware recommendations labelled `(Recommended)` (e.g., AngularJS source → Angular target; ASP.NET WebForms → React; LOC < 5,000 → big-bang strategy). Skip-if-filled makes the interview idempotent on re-runs and respects manual edits. Bail-out via "skip the rest" is safe — `/plan`'s validation remains the safety net for unset required fields. Replaces the previous "open migration.md and fill sections 3, 6, 7, 10 by hand" closing message from `/init`.
- **`frameworks/` directory** — 31 per-framework markdown files (17 source, 8 target-UI, 6 target-API) replacing the inline detection table in `agents/legacy-analyzer.md`, the per-stack scaffold recipes in `skills/scaffold/SKILL.md`, and the per-stack password-hashing notes in `skills/auth/SKILL.md`. Each file uses a consistent template (`## Detection` / `## Scaffold` / `## Test framework` / `## Auth notes` / `## Dev server` / `## Recommendation context`). Adding a new framework is now a one-file drop-in. Currently shipped:
  - **Source**: aspnet-{webforms,mvc,core-mvc}, java-{jsp,struts,spring-mvc,spring-boot}, angularjs-1, vue-2, jquery-spaghetti, php-classic, coldfusion, vbscript-asp-classic, ruby-on-rails, django, wordpress, extjs.
  - **Target UI**: react-vite-ts, next-app-router, vue3-vite, angular, svelte-kit, astro, nuxt, remix.
  - **Target API**: dotnet-minimal-api, spring-boot-3, nestjs, fastapi, express, hono.
- **First-class unknown-tech path** — `legacy-analyzer` now returns `primary: "unknown"` with an `evidence[]` array (raw signals observed in the source tree) when no framework rule matches. The `/analyze` interview surfaces that evidence to the user and offers an explicit free-text "specify your own" option; `state.json.source_stack.user_provided` is set to `true` and downstream skills check it. For unknown target frameworks, `/scaffold` runs a 3-question follow-up (scaffold command / test framework / verify commands) writing the answers to `verify.config.json` so retries don't re-ask. For unknown target API, `/auth` skips the prebuilt password-hashing template and defers to `agents/permanent-gotchas.md` + OWASP. End-to-end Rails → Astro now works with zero plugin recipes.
- **`templates/migration-interview.json`** — declarative question catalog driving the new interview. Each entry has `id`, `section_anchor`, `field_label`, `options` (framework IDs resolved against `frameworks/*.md`) or `options_inline`, and optional `recommend_by_source` / `recommend_by_loc` / `derive_from` lookups.

### Changed

- **All 15 SKILL.md `description:` fields rewritten** to a packed format: `<one-line action>. Use when state.status is <X>. Triggers: '<phrase 1>', '<phrase 2>', '<phrase 3>'.` Leverages Claude Code's native skill auto-invocation (`disable-model-invocation: false`, already set) so plain-English utterances like *"what's next"*, *"let's plan it"*, *"where are we"*, *"stuck lock"* reliably route to the right slash command. Lifecycle anchors (`Use when state.status is X`) disambiguate adjacent skills — *"let's plan"* fires `/plan` when status is `analyzed` but routes elsewhere otherwise. No router skill added; the model does the matching, descriptions encode the rules.
- **`agents/legacy-analyzer.md`** — inline detection table replaced with: glob `frameworks/*.md` where `role: source`, read each `## Detection` section, score signals against the source tree, return top match or `unknown + evidence`. Adding a source framework no longer requires editing this agent.
- **`skills/scaffold/SKILL.md`** — inline UI/API recipe branches replaced with: read `frameworks/<ui>.md` / `frameworks/<api>.md` `## Scaffold` section and execute. Missing file → unknown-target 3-question follow-up. The shared dev CORS allow-list and the load-bearing cross-cutting rules (`reflect-metadata` first-import, `only-include` for FastAPI hatchling, `partial class Program` for .NET, Nest:3001 ↔ Next:3000) stay documented in the SKILL.md prose and `agents/permanent-gotchas.md`.
- **`skills/auth/SKILL.md`** — per-stack password-hashing recipe block replaced with: read `frameworks/<api>.md` `## Auth notes`. Always also read `permanent-gotchas` for cross-cutting rules (bcrypt 72-byte truncation, passlib ban, CSRF defaults). Missing framework file → skip the stack-specific template, do not block; let the user proceed per `permanent-gotchas` + OWASP guidance.
- **`skills/analyze/SKILL.md`** — added an Interview phase between the §2 auto-fill and the closing summary. Now writes `state.json.source_stack.user_provided` and `state.json.target_stack` (pre-populating fields `/plan` would otherwise write).
- **`skills/init/SKILL.md`** — closing "Next steps" updated to point at `/analyze` for both detection and interactive filling, removing the "open migration.md and fill in sections 3, 6, 7, 10 by hand" line.

### Why this is a minor, not a patch

The three changes are all additive at the schema level (no `schema_version` bump, no removed/renamed commands, no removed skills). But each is large enough in surface area — 31 new framework files, a new interview catalog, a refactor of three skills + one agent, all 15 description: fields rewritten — that bundling them as a patch would understate the impact. Teams pull this with `/plugin uninstall web-modernize && /plugin install web-modernize`; no `.claude/modernize/` reset required.

### Why this is a minor, not a major

No state-schema change. No removed commands, no removed skills, no renamed slash commands. The new `state.json.source_stack.user_provided` field is optional / additive — existing state files validate as-is. Existing migrations keep working without re-running `/analyze`.

## [0.9.3] - 2026-05-14

Patch release: fixes the scaffold closing message to spell out dependency-install steps before the dev-server commands.

### Fixed
- **`skills/scaffold/SKILL.md`** — the "Run the new stack locally" closing block jumped straight to `uvicorn` / `npm run dev` without showing the install step. The scaffold's smoke-build does install once during scaffolding, but (a) a fresh shell (especially a Python venv) won't have the tools on PATH until activation, and (b) a teammate who just pulled the scaffolded skeleton from git hasn't installed at all. The closing message now prints an explicit **install / activate** line directly above every dev-server line, per stack: `npm install` for all Node UIs and NestJS, `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` for FastAPI (with Windows PowerShell + Git Bash variants), `./mvnw -q -DskipTests package` for Spring Boot, `dotnet restore` for .NET. Same change applies to the `custom` UI fall-through ("install your UI dependencies, then start the dev server").

## [0.9.2] - 2026-05-14

Patch release: fixes a self-inflicted version-skew warning that fired on every fresh `/web-modernize:init`.

### Fixed
- **`skills/init/SKILL.md`** — `plugin_version` in the initial `state.json` was a hardcoded literal (`"0.3.0"`), so every freshly initialized repo got stamped with a stale version and tripped the skew warning (`State written by: 0.3.0 / Running version: 0.9.x`) on the very next skill run. The init skill now reads the running plugin's version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` (the same pattern `next`/`plan`/`verify` already use for the skew check) and writes that into state. Existing `state.json` files keep self-healing the way they already do — on the next successful `/next`, `/plan`, or `/verify` run, `state.plugin_version` is bumped to the running version and the warning stops.

## [0.9.1] - 2026-05-14

Documentation + schema cleanup patch surfaced by an audit pass. No behavior change for users on 0.9.0.

### Removed
- **`docs/v0.9.0-strategic-audit.md`** — paused-discussion artifact captured before v0.9.0 shipped. The decisions it deferred are now committed to `main` and recorded in the 0.9.0 changelog entry; the file itself was unreferenced.

### Fixed
- **`CLAUDE.md`** — corrected the stale "14 total" skills comment to "15 total" (the `/web-modernize:unlock` skill added in v0.8.2 was never reflected here).
- **`README.md` slash-command table** — added the missing `/web-modernize:unlock` row. The skill has shipped since v0.8.2 and is referenced from `/web-modernize:status` as the recovery path for stuck locks, but it never made it into the user-facing reference table.
- **`templates/state.schema.json`** — declared the `testing` top-level block (`ui_framework`, `api_framework`, `target_pct`, `last_aggregate_check`). `/web-modernize:plan` has been writing this block since v0.4.0 and `/scaffold` + `/verify` have been reading it; the schema's `additionalProperties: false` meant validating an in-the-wild `state.json` against the schema would have rejected it. Additive — no `schema_version` bump, existing 0.9.0 state files validate as-is.

## [0.9.0] - 2026-05-14

Strategic prune driven by a single criterion: **keep something in the plugin only if the agent can't discover it on its own.** That means first-run crashes, silently-wrong behavior, or load-bearing rules without a searchable symptom. Everything else — well-documented deprecations, version bumps, framework guides — leaves the plugin and is handled by the agent + WebSearch at scaffold time.

Concretely: 0.8.x carried framework-specific recipes that aged out within weeks (Pydantic v1→v2 patterns, `'use client'` reminders, Svelte 5 runes, `--use-minimal-apis` removal, hyphenated `dotnet` namespace splits, Vite 7 Node 22 floor, `npm create svelte@latest` retirement, Initializr `packageName` sanitization, xUnit v3 collector mismatch, Angular `karma.conf.js` regeneration, JaCoCo Java 23 compat). Each of those is one WebSearch away. The catalog now keeps only the entries an agent provably can't reach via search — hatchling editable-install eager-eval, `passlib[bcrypt]` `detect_wrap_bug`, Spring `/actuator/health` vs `/health` smoke-gate mismatch, NestJS `reflect-metadata` first-import requirement, Nest:3001 ↔ Next:3000 collision, and the chrome + global-CSS pattern rule.

No state schema changes, no removed commands, no renamed slash commands. The surface (15 skills / 15 commands / 2 agents / 2 hooks) is identical to v0.8.3. The diff is content slimming + template-file deletion. Teams on 0.8.x pull this with `/plugin marketplace update web-modernize && /plugin uninstall web-modernize && /plugin install web-modernize`, then restart Claude Code — **no `.claude/modernize/` reset required**, since `state.schema.json` is unchanged.

### Removed
- **`templates/permanent-gotchas/{dotnet,spring-boot,nestjs}/`** — eight stack-recipe template files deleted. The scaffold skill now describes the CORS / `/health` / `partial class Program` / `reflect-metadata` first-import / Nest port shape in prose; the agent regenerates the file shape at scaffold time. One exception kept: `templates/permanent-gotchas/fastapi/pyproject.toml` is the single surviving template — hatchling's eager `default_only_include` bug is the most-bit gotcha in this session's testing and reconstructing the dual-`only-include` config from prose alone is error-prone.
- **`agents/permanent-gotchas.md` web-searchable entries** (219 → ~100 lines): dropped `--use-minimal-apis`, `npm create svelte@latest`, Pydantic v1→v2 patterns, Svelte 5 runes, Next.js `'use client'`, Vite 7 Node 22 floor, Angular karma.conf.js regeneration, Spring Initializr packageName sanitization, hyphenated dotnet namespace split, xUnit v3 / MTP collector mismatch, FastAPI `@app.on_event` deprecation, Spring Boot 3 `javax`→`jakarta` rename, NestJS `bcryptjs` performance footgun, `WebApplicationFactory<Program>` partial-class trick (now inlined in the scaffold recipe), and `dotnet new webapi` CORS/health omission (absorbed into the cross-cutting CORS note).
- **`skills/auth/SKILL.md` per-stack hashing-library table** — agent picks the per-stack default from current docs; the one durable rule (no `passlib[bcrypt]` for Python) survives in `agents/permanent-gotchas.md`.
- **`skills/plan/SKILL.md` UI framework enum** — §3 Target UI framework now accepts any non-empty value. The scaffold skill maps known names to recipes and falls through to `custom` for anything else; the enum at preflight time added no real safety.

### Changed
- **`README.md` workflow block** restructured so `/scaffold` and `/auth` are framed as one-time setup (steps 5–6) rather than as iterations inside the per-unit "Loop:" block. The previous framing parenthetically annotated them `(once)` but the structural placement still misled new readers.
- **`README.md` typo callout** removed. The `Repo URL note` block at the top of the file warning readers about the `web-mordernize` repo name was noise — the install commands already use the correct repo name; no clarification needed.
- **`skills/scaffold/SKILL.md` API recipes** rewritten to describe the per-stack CORS / `/health` / first-import / port shape in prose, with explicit pointers to the surviving `agents/permanent-gotchas.md` entries. The FastAPI recipe still references `templates/permanent-gotchas/fastapi/pyproject.toml` (the one template kept).
- **`skills/auth/SKILL.md`** dropped the per-stack hashing-library table and the inline `security.py` copy instruction. Replacement is a single paragraph: agent picks the default per current docs; the catalog forbids `passlib`; document the choice in `notes/__auth__.md`.

### Why this is a minor, not a major
No state schema bump, no removed/renamed commands, no removed skills. Existing 0.8.x state files are forward-compatible — `schema_version` is unchanged. The "removed" entries are content inside skill files and a templates directory; nothing the plugin's runtime state depends on.

### Why this is a minor, not a patch
The removed entries change agent behavior at scaffold time (the agent now must regenerate file shapes from docs + the slimmer catalog, rather than copying from templates). A scaffold smoke test on a stack the team relied on getting from a template will exercise a different code path than on 0.8.3, even though the workflow surface is identical.

## [0.8.3] - 2026-05-14

Captures a class of migration gap surfaced by a real user run: ASP.NET WebForms → React migrations were producing pages with no header/footer/nav and partially-applied legacy CSS. Root cause is the same for every legacy stack — page-wrapping templates (master pages, `_Layout.cshtml`, JSP includes, ColdFusion `<cfinclude>`, Struts tiles, classic PHP `include 'header.php'`) aren't standalone content pages and so don't appear as units in `/plan`. The migrator translated content pages in isolation; chrome silently disappeared. Same shape for global stylesheets — copied to `public/` by `/scaffold` but never imported from the entry, so most rules don't load.

Per the "prefer pattern-level rules over per-scenario features" principle, this release does **not** add a synthetic `__layout__` unit or a new required `migration.md` field. It adds one shape-agnostic entry to the durable-quirks catalog and one line to the migrator agent's checklist — the same rule covers Site.master today, ColdFusion includes tomorrow, anything else after that.

### Added
- **`agents/permanent-gotchas.md` — "Page-wrapping chrome and global stylesheets aren't 'units'"** — durable, shape-agnostic rule documenting the cross-cutting-chrome pattern + global-CSS wiring across 7 legacy stack families (WebForms, MVC/Razor, JSP, ColdFusion, Struts, AngularJS, classic PHP). Five-step fix: identify the wrapping template, translate to target's root layout file, import legacy stylesheets from the entry, preserve the body wrapper class, order CSS after framework defaults. Recorded in `notes/__layout__.md` so subsequent units don't redo it.
- **`agents/unit-migrator.md` step 2b — first-unit-only chrome translation** — one line in the general algorithm. When no feature unit has been migrated yet (only `__auth__` or none), the agent translates the wrapping template + wires global CSS before the first feature unit's content lands. Skipped on subsequent units; chrome + CSS inherit automatically.

### Why this is a patch, not a minor
No schema changes, no new skills, no new templates, no new required fields, no new state shape. Two text additions to existing files. Existing migrations don't retroactively benefit (the chrome would have to be applied manually), but every migration started after this version handles it on the first feature unit.

## [0.8.2] - 2026-05-14

Operational hardening — five concrete failure modes a real migration team would have hit under normal use. None had bitten anyone yet, but each was reproducible against the code. None of these are version-of-framework issues; they're plugin-design quirks that wouldn't go away on their own.

### Added
- **`/web-modernize:unlock`** (`skills/unlock/SKILL.md`) — force-clears a stuck advisory lock on `state.json`. Required after a Claude session crashes while holding the lock (otherwise `/plan` and `/scaffold` are blocked for the full 10-minute TTL with no recovery path). Requires the user type `force-clear` explicitly; records the action in `state.history` for audit.
- **Stale-lock detection in `/status`** — `skills/status/SKILL.md` §8 now distinguishes a fresh lock from an expired-but-still-recorded lock and from a current-user lock with no matching in-flight session. Each case prints the appropriate recovery hint (`/web-modernize:unlock`) instead of just saying "lock held."
- **Asset copy size guard** in `skills/scaffold/SKILL.md` — `cp -r`-style asset copy was unbounded; legacy repos with multi-GB PSD/AI/MOV directories silently filled dev disks. Now: scaffold sums the discovered asset tree, and if > 500 MB prompts with `y` (exclude large binary extensions) / `n` (copy everything) / `s` (show 10 largest first). Threshold is intentionally generous — small projects skip the prompt entirely.
- **Plugin-version skew warning** in `skills/next/SKILL.md`, `skills/plan/SKILL.md`, `skills/verify/SKILL.md` — every skill compares `state.plugin_version` to the running plugin's manifest version. If major/minor differ (patch differences ignored), prints a warning but **continues** the skill — refusing would block the team on its slowest updater. On successful exit, the skill bumps `state.plugin_version` to its own, so the warning self-resolves after one synchronized run.

### Fixed
- **`hooks/heartbeat.mjs` scope-narrowing** — previously scanned every `*.json` file under `units/` on every Write/Edit, parsing JSON + rewriting any `in_progress` unit's heartbeat. With 50+ units this added 200–800 ms per tool call on Windows. Worse, the hook bumped heartbeats on units claimed by **other** developers (Alice's local Writes refreshed Bob's unit), causing cross-dev misattribution after a `git pull`. Now: read `git config user.email` + `os.hostname()` once, then bump only units whose `in_flight.by` and `in_flight.host` match. Typical-case fs work drops to 0–1 file write per tool call.
- **`/auth` seed step checks the users table exists first** — `skills/auth/SKILL.md`'s seed-dev-users step used to INSERT blind. If the team hadn't run DB migrations yet, the script failed with a cryptic SQL error, `/auth` recorded "seed convenience failed, but auth itself is migrated," bumped `state.status` to `auth_done`, and the team only discovered the missing table on their first login attempt. Now: the seed script's first action is a `SELECT 1 FROM users LIMIT 1` (or equivalent per stack); on missing table it exits with code 2 and a per-stack "run your migration tool then re-run X" message. `/auth` reads exit 2 specially, records `seed_skipped_reason: "users-table missing"` on the auth unit file, still bumps `state.status` (the code itself is fine), and prints reseed instructions in the closing block instead of credentials.

### Why this is a patch, not a minor
No state schema changes. New `/unlock` skill is additive. Behavior changes in `/auth`, `/scaffold`, `/next`, `/plan`, `/verify`, and the heartbeat hook are all warn-or-prompt; nothing refuses to run where it previously ran. Teams pull this with `/plugin uninstall && /plugin install`.

## [0.8.1] - 2026-05-14

Sweep-up after the 0.8.0 lean refactor. Five small leftovers where stale version numbers, inlined templates, or missing config fields contradicted the new "let `@latest` decide, durable quirks live in permanent-gotchas" architecture.

### Changed
- **`README.md`** — Node ≥ 16 row clarified: that floor is for the heartbeat hook only; scaffolded UI stacks need their own (Vite 22, Next 20.10, Angular 20.11). The §3 framework row dropped the stale "Angular 21+, Next 16+" examples in favor of "latest stable major via `@latest`".
- **`skills/scaffold/SKILL.md`** — junit5 test-harness no longer hardcodes JaCoCo `0.8.15`; the recipe now says "use the latest JaCoCo Maven plugin" and points at `agents/permanent-gotchas.md` for the root-cause note about JDK bytecode-version compatibility. One less version to bump on a release.
- **`skills/auth/SKILL.md`** — the `security.py` template was inlined twice (in this SKILL and in `templates/permanent-gotchas/fastapi/security.py`). Removed the inline copy; auth now points at the template. Future fixes land in one place.
- **`templates/migration.md` §8 Constraints** — added an explicit "Framework version pin" bullet. The README claimed teams could pin via §8 but the template offered no field for it; teams had to invent the convention.

### Why this is a patch, not a minor
Pure cleanup. No new behavior, no new files. Existing scaffolds and state files are unaffected. Teams already on 0.8.0 pull this with the usual `/plugin uninstall && /plugin install` flow.

## [0.8.0] - 2026-05-14

Center-of-gravity shift: the plugin moves from "prescribe every framework version" to **"stateful workflow + a durable catalog of permanent quirks."** The 0.5.x–0.7.x line patched real bugs as teams hit them, but each fix pinned a specific framework version (Spring Boot 3.4.1, JaCoCo 0.8.12, Angular 17, FastAPI 0.115, …) that went stale within weeks. The recipe-version maintenance load was outpacing the actual value. This release reorganizes so framework versions are picked at scaffold time by `@latest` CLIs, while only the **durable** quirks — bugs that don't depend on a specific framework version — are catalogued in one place.

Also adds two UX improvements customers asked for: run-the-stack instructions printed at the end of `/scaffold`, and pre-seeded dev users printed at the end of `/auth` so the team can log in without reverse-engineering the register payload.

### Added
- **`agents/permanent-gotchas.md`** — new read-only catalog of version-agnostic bugs/workarounds across every supported stack. Each entry documents a tool/library quirk that Claude cannot reliably discover on its own (e.g., passlib's `detect_wrap_bug` crash on bcrypt ≥4, Spring actuator's `/actuator/health` vs scaffold's `/health`, NestJS `reflect-metadata` first-import requirement, hatchling eager `default_only_include`, the `--use-minimal-apis` flag removal, Spring Initializr silent hyphen-stripping in `packageName`, Vite 7 dropping Node 18/20, `npm create svelte@latest` retirement, Svelte 5 runes, Pydantic v1→v2 rewrite map, NestJS:3000 ↔ Next:3000 port collision). Updated only when a quirk's root cause changes — not bumped for version drift.
- **`templates/permanent-gotchas/<stack>/`** — concrete file shapes that encode the workarounds: `fastapi/{pyproject.toml,main.py,security.py,conftest.py,test_health.py}`, `spring-boot/{HealthController,CorsConfig}.java`, `dotnet/Program-additions.cs`, `nestjs/main.ts`. The scaffold skill now copies these in rather than inlining ~200 lines of code blocks per stack.
- **Post-scaffold run-the-stack message** — `/scaffold`'s closing block now prints exact dev commands and URLs for the chosen UI + API stacks (e.g., `cd apps/api-new && fastapi dev app/main.py`, `cd apps/web-new && npm run dev`, `curl http://localhost:8000/health`). Customers no longer have to remember which framework uses `npm run dev` vs `npm start` vs `dotnet run`.
- **`/auth` pre-seeds dev users** (when target auth is a local password store, not an IdP) — generates an idempotent seed script in the target stack's idiomatic shape (`apps/api-new/scripts/seed_dev_users.py` for FastAPI, `DevUserSeeder.java` with `@Profile("dev")` for Spring, `--seed` CLI flag for .NET, `seed-dev-users.ts` for Nest), runs it once, writes `.claude/modernize/dev-credentials.md` (gitignored), and **prints the credentials in the terminal closing block** so the team can `curl /auth/login` immediately. Scripts refuse to run when `NODE_ENV` / `ASPNETCORE_ENVIRONMENT` / `SPRING_PROFILES_ACTIVE` is `production`, and refuse to overwrite real users with `@dev.local` emails.

### Changed
- **`skills/scaffold/SKILL.md`** — UI + API recipes slimmed from ~200 lines of inline code blocks to ~50 lines of pointers into `templates/permanent-gotchas/<stack>/`. CLIs now use `@latest` exclusively; the only pinned versions remaining are Java 21 (Spring Initializr requires a numeric `javaVersion` parameter) and Node minimums per UI stack (which are durable preflight checks, not framework version pins).
- **`skills/auth/SKILL.md`** — Finalize step's print block extended with the seeded-credentials section.

### Removed
- **`angular-17` back-compat alias in `skills/plan/SKILL.md`** — the v0.6.0 rename kept "legacy value `angular-17` is also accepted for back-compat" in the plan validator. Per the no-migration-code rule (no production users yet), that alias is dropped; teams with `state.target_stack.ui = "angular-17"` should rename the value in their state file to `angular` or re-init.

### Why this is a minor bump, not major
No `schema_version` change. The new template files are additive. The slimmed scaffold recipes describe the same final filesystem state (CORS, `/health`, `.env`, `lifespan`, `reflect-metadata` first-import, etc.) — just sourced from templates instead of inline code blocks. Removing the `angular-17` alias is breaking only for in-flight teams using that exact string, of which there are none (no production users yet).

## [0.7.1] - 2026-05-14

Bug fix: the `/web-modernize:auth` skill named "BCrypt" as a legacy pattern to detect, but didn't prescribe a target-side library — so when migrating local-password-store auth into FastAPI, Claude defaulted to the tutorial convention `passlib[bcrypt]`, which crashes on the very first `pwd_context.hash()` call under bcrypt ≥4.0 (`ValueError: password cannot be longer than 72 bytes`). Root cause: passlib's last release was 2020; its bcrypt-detection routine tests `_bcrypt.hashpw()` with a 73-byte secret to detect old truncation behavior, but bcrypt 4.x raises on >72 bytes instead of truncating, so passlib's init explodes before the caller's password is even seen. Passlib is effectively unmaintained.

### Fixed
- **`skills/auth/SKILL.md` — new "Password hashing — pick the right library per target stack" section** with an explicit prescription table:
  - FastAPI: `bcrypt>=4.0` directly with 72-byte input truncation. **Explicitly forbids `passlib[bcrypt]`** with a one-line explanation of the detection-routine crash, so Claude doesn't reach for it again.
  - Spring Boot: `BCryptPasswordEncoder` from `spring-security-crypto`.
  - .NET minimal API: `Microsoft.AspNetCore.Identity.PasswordHasher<TUser>` or `BCrypt.Net-Next`.
  - NestJS: `bcrypt` (npm) or `argon2`; flags `bcryptjs` as the slow pure-JS fallback to avoid.
- **Concrete `app/auth/security.py` template for FastAPI** with safe `_prep(password)` that truncates to 72 bytes, plus a documented SHA-256 pre-hash alternative for teams that want arbitrary-length password support. Both options note their effect on legacy hash compatibility.

Existing migrations whose `security.py` was generated against the old (silent) `/auth` recipe will have already crashed and likely been hand-fixed. The plugin's prescription change prevents recurrence on the next `/web-modernize:auth` run; no schema or behavior change for state in flight.

## [0.7.0] - 2026-05-14

Closes the "scaffold passes, app doesn't run" gap. The 0.5.x / 0.6.0 work made every recipe prescriptive and version-current; this release fixes the next-most-common failure mode — running the scaffolded app and immediately hitting CORS errors, wrong `/health` path, wrong Node version, or "where does my UI find the API?". All four are now configured at scaffold time, not left for the team to discover when their first `/web-modernize:next`-migrated unit calls the API.

### Added
- **New "Stack defaults" table** at the top of `skills/scaffold/SKILL.md` per-subsystem checklist. Single source of truth for UI dev port, Node minimum, API dev port, and the dev CORS allow-list per stack. Referenced by both the Node preflight and every API CORS recipe. The NestJS API dev port is **3001** (Nest's default is 3000, which collides with Next.js dev) — documented explicitly so teams running Next + Nest don't fight port binding.
- **Per-UI-stack Node version preflight** — Node 22 for Vite-based stacks (`react-vite-ts`, `vue3-vite`, `svelte-kit` — Vite 7 dropped Node 18/20), 20.10 for `next-app-router`, 20.11 for `angular`. The old blanket "Node ≥ 18" check passed for stacks where it shouldn't have, leaving the scaffold to fail at the `npm install` step.
- **"Wire to API" step in every UI scaffold** — writes `.env.example` + `.env` (or Angular's `environment.ts` pair) with the canonical API URL for the chosen API stack, plus a tiny `src/lib/api.ts` helper that the migrator can import. The team's first `fetch()` from a migrated unit has a real target.
- **CORS + explicit `/health` in every API scaffold** — every API recipe now writes a permissive-for-dev / TODO-for-prod CORS config and an explicit `/health` endpoint at the path the smoke gate hits:
  - **FastAPI**: prescriptive `app/main.py` template with `CORSMiddleware`, `lifespan` context manager (the deprecated `@app.on_event("startup")` is dead as of FastAPI 0.121+), and `@app.get("/health")`.
  - **Spring Boot**: writes a `CorsConfig.java` (`WebMvcConfigurer` + `addCorsMappings`) and a `HealthController.java` (`@RestController` + `@GetMapping("/health")`). Critical — actuator's health is at `/actuator/health`, **not** `/health` where the smoke gate looks.
  - **.NET minimal API**: `Program.cs` snippet adding `builder.Services.AddCors(...)` with the dev allow-list and `app.MapGet("/health", ...)`.
  - **NestJS**: rewrites `main.ts` to preserve the load-bearing `import 'reflect-metadata';` as the first line (omitting it crashes Nest at startup), enables CORS via `app.enableCors`, and binds to port 3001. Adds a `@Get('health')` route to the generated `app.controller.ts`.

### Why this is a minor bump
All four items are additive — they extend recipes and add files to fresh scaffolds. Existing scaffolds (already at `state.status >= "scaffolded"`) are untouched; teams that want the new wiring can re-run `/web-modernize:scaffold --assets-only` for the asset bits or hand-apply the CORS/health snippets from the recipe. No schema change, no breaking key changes.

## [0.6.0] - 2026-05-14

Modernization pass on **every scaffold recipe** for staleness. The 0.5.x line proved the "vague recipe → broken scaffold" failure mode (FastAPI hatchling, .NET `--use-minimal-apis`, Spring Boot Initializr); this release applies the same scrutiny to the remaining pinned versions and CLI patterns. Driving principle, per customer feedback: **default to the latest stable major** of each target framework; teams that need an LTS pin can override via `migration.md` §8 Constraints.

### Changed
- **`angular-17` stack key renamed to `angular`** in `templates/migration.md` §3, `skills/plan/SKILL.md` preflight enum, `templates/state.schema.json` description, and `README.md`. The recipe in `skills/scaffold/SKILL.md` now runs `npx @angular/cli@latest new ...` (was `@angular/cli@17`, which pinned to a Nov-2023 release while Angular is on v21+). Plan validation accepts the legacy `angular-17` value as a back-compat alias.
- **Spring Boot pin `bootVersion=3.4.1` → `3.5.14`** in the `start.spring.io` curl recipe (3.5 is the final 3.x minor; 3.5.14 is the latest patch). Customers needing Boot 4.x should plan for it explicitly.
- **FastAPI dep pins** in the scaffold template: `fastapi>=0.115` → `fastapi>=0.136`, `uvicorn[standard]>=0.32` → `>=0.37`, `requires-python = ">=3.11"` → `">=3.12"`. Current FastAPI is 0.136.x and the FastAPI docs recommend Python 3.12.
- **JaCoCo pin `0.8.13` → `0.8.15`** in the `junit5` test-harness POM snippet. 0.8.15 (May 2026) adds Java 25 support and experimental Java 26 bytecode; older versions fail on classes compiled with Java 23+.
- **SvelteKit recipe**: `npm create svelte@latest` → `npx sv create`. The old `create-svelte` CLI was retired in favor of the new `sv` tool (ships with Svelte 5 / SvelteKit 2).
- **Karma + Angular note**: since Angular 18 the CLI no longer guarantees a generated `karma.conf.js` in every configuration. The `karma-jasmine` test-harness recipe now includes a manual install fallback and a one-line nudge toward `other: web-test-runner` / `other: vitest` for greenfield Angular migrations, since Karma is on Angular's deprecation runway.
- **xUnit recipe note**: added a one-line opt-in for `dotnet new xunit3` (Microsoft Testing Platform) for teams targeting **.NET 10**, with the caveat that coverage flows through `Microsoft.Testing.Extensions.CodeCoverage` rather than `coverlet.collector`. Default stays on xUnit v2 to avoid regressing the well-tested coverage path.

### Why this is a minor bump and not a patch
The `angular-17` → `angular` rename is technically a stack-key change. Existing `state.json` files with `target_stack.ui = "angular-17"` keep working (plan accepts the legacy value, and `state.schema.json` doesn't enum-constrain the field — only the description was updated), so this is additive at the schema level. No `schema_version` bump and no `/init` reset required. Teams pull the new version with `/plugin uninstall web-modernize && /plugin install web-modernize` before their next `/web-modernize:scaffold` run.

## [0.5.2] - 2026-05-14

Bug fix follow-up to 0.5.1: audited the **.NET minimal API** and **Spring Boot 3** scaffold recipes for the same class of "vague instruction → Claude invents broken config" issue that bit FastAPI. Found four landmines per stack; this release replaces both recipes with prescriptive, version-pinned templates.

### Fixed
- **`skills/scaffold/SKILL.md` — .NET recipe (line 85 + `xunit` section)**
  - Dropped `--use-minimal-apis` flag (removed in .NET 9; minimal API has been the default since .NET 8). Recipe now uses `dotnet new webapi -o apps/api-new` and documents `--use-controllers` as the explicit opt-out.
  - Documented the hyphen-vs-underscore split that `dotnet new` performs on hyphenated paths (`<AssemblyName>api-new</AssemblyName>` + `<RootNamespace>api_new</RootNamespace>`), and suggested `-n ApiNew` as an opt-in for teams that want PascalCase consistency.
  - Resolved the ambiguous `<ProjectName>` placeholder in the xunit harness recipe with a concrete `<project>` substitution example, pinned the working directory to repo root, and added a `dotnet new sln && dotnet sln add ...` step so `dotnet test` / `dotnet build` at repo root just work.
- **`skills/scaffold/SKILL.md` — Spring Boot recipe (line 86 + `junit5` section)**
  - Replaced the "use start.spring.io API; offer to provide curl command" hand-wave with a literal, pinned curl recipe (Java 21, Maven, Boot 3.4.1, `web,actuator`, explicit `groupId`/`artifactId`/`packageName`, `.tgz` archive). Documents why `bootVersion` and `packageName` must be set explicitly (Initializr's hyphen-stripping `packageName` sanitization is silent and surprising).
  - Bumped JaCoCo pin from `0.8.12` → `0.8.13` (0.8.12 fails on classes compiled with Java 23+; 0.8.13 adds Java 24 bytecode support).
  - Switched the `junit5` health-test sample to lead with `MockMvc` + `@AutoConfigureMockMvc` (the right default for Spring Boot 3's MVC/Tomcat stack), demoted `WebTestClient` to a WebFlux-only alternate. `WebTestClient` requires `spring-boot-starter-webflux` on the classpath, which `spring-boot-starter-test` alone doesn't bring.

No template/schema changes; existing in-flight migrations are unaffected. To pick up the fix, users should `/plugin uninstall web-modernize && /plugin install web-modernize` before their next `/web-modernize:scaffold` run.

## [0.5.1] - 2026-05-14

Bug fix: the FastAPI scaffold's generated `pyproject.toml` could fail `pip install -e ".[dev]"` on recent hatchling (notably Python 3.14) with `ValueError: Unable to determine which files to ship inside the wheel`. Hatchling's `only_include` property evaluates `default_only_include()` eagerly as the default arg to `dict.get()`, so the auto-detection raises before the configured `packages` fallback can apply — triggered whenever the project name (e.g., `api-new` → `api_new`) doesn't match the package directory (`app/`).

### Fixed
- **`skills/scaffold/SKILL.md` — FastAPI recipe** — now prescribes a concrete `pyproject.toml` template with explicit `only-include = ["app"]` on both `[tool.hatch.build.targets.wheel]` and `[tool.hatch.build.targets.editable]`, which short-circuits hatchling's failing auto-detection path. Existing scaffolds that hit the error can fix in place by adding the same two `only-include` lines to their `pyproject.toml`.

## [0.5.0] - 2026-05-13

Builds on 0.4.0's execution-based gates. Those gates answer "does it run?"; this release answers "does it preserve the legacy behaviour?". The plugin now picks the test framework at `migration.md` time (with per-stack suggestions), scaffolds a working test harness with a sample test at `/scaffold` time, translates legacy unit tests to the target framework at `/migrate` / `/next` / `/retry` time, and generates additional tests to top up to the team's coverage bar (default 80%). Coverage below target is a **soft fail** — the unit still finalises, but with a `below_threshold` flag and a warning listing the uncovered regions, so a flaky coverage measurement never blocks a working migration.

### Added
- **`templates/migration.md §12 "Testing" — REQUIRED** — three new fields (UI test framework, API test framework, target coverage %) with stack-aware suggestions printed inline (vitest for Vite UIs, jest for Next/Nest, karma-jasmine for Angular, pytest for FastAPI, xunit for .NET, junit5 for Spring Boot). `/web-modernize:plan` validates all three before generating the plan; missing → numbered failure report.
- **`state.json.testing` block** — written by `/plan` from §12. Single source of truth for which runner `/scaffold` installs and which coverage bar the migrator and `/verify` measure against. Re-plans overwrite from §12; switching runners mid-migration does not retroactively re-translate already-migrated units.
- **`skills/scaffold/SKILL.md` "Test harness" sub-step** — runs after the framework CLI / API skeleton creation and before the smoke-build gate. Per-runner recipes for vitest, jest, karma-jasmine, pytest, xunit/nunit/mstest, junit5: install the runner + coverage tool, write the config file (`vitest.config.ts`, `pyproject.toml [tool.pytest.ini_options]`, JaCoCo plugin, etc.), create the test directory in the framework's convention (`tests/` with `conftest.py` for pytest, colocated `*.test.tsx` for vitest, `src/test/java/` for junit, etc.), write one passing sample test against `/health` (API) or the placeholder root (UI), and add `test` / `test:coverage` scripts. `manual` / `n/a` runners record `"test_harness": "manual"` and skip auto-install (soft-skip).
- **`skills/scaffold/SKILL.md` smoke-build gate test-harness extension** — in addition to the install+build smoke from 0.4.0, the gate now runs a test-harness smoke (`pytest -q tests/test_health.py`, `npm run test -- --run`, `dotnet test --no-build`, `./mvnw -q test`, etc.) that proves the harness picks up and runs the sample test. Both smokes must exit 0 before the subsystem flips to `done`. Records `scaffold.<subsystem>.smoke.test_harness = { runner, command, exit_code }`.
- **`agents/unit-migrator.md` step 7c "Tests — translate legacy first, then top up to coverage threshold"** — new step in §3 between visuals (7b) and the placeholder-test fallback (8). Scans for legacy tests touching the unit's `source_paths` (NUnit/MSTest, JUnit, Jasmine, pytest conventions per detected source stack); translates enabled tests to the target framework preserving names and assertion intent (mocks/fixtures/parameterised cases included); records disabled tests in `tests.skipped_legacy` and infrastructure-bound tests in `tests.untranslatable`; runs translated tests with scoped coverage; if `pct < target_pct`, generates targeted behavioural tests for uncovered regions using the legacy code's observable behaviour as the spec; iterates up to **2 generation passes** then accepts the result (deliberate ceiling — auto-generation loops can rot context).
- **`agents/unit-migrator.md` §5a smoke gate test+coverage extension** — after boot+curl / build+typecheck, the gate now runs the unit's scoped tests with coverage. Decision tree: tests pass + coverage ≥ target → green. Tests pass + coverage < target → **soft-fail on coverage**, unit still finalises as `migrated` with `tests.coverage.below_threshold = true` and a yellow warning listing the uncovered regions. Test runner errors out (collection/import/config) → **hard fail** via §4 with a runner-specific diagnostic. Test assertions fail (the new implementation doesn't match the legacy behaviour the translated test encodes) → **hard fail** with the first-failing-test + message in the diagnostic so `/retry --with-prompt` can act on it.
- **`templates/unit.schema.json` — optional `tests` block** — additive (no `schema_version` bump). Tracks `framework`, `translated_from[]` (legacy_path → target_path), `translated_count`, `skipped_legacy[]`, `untranslatable[]`, `generated_count`, and `coverage` (pct, target_pct, below_threshold, uncovered_regions).
- **`skills/verify/SKILL.md` aggregate coverage post-check** — built-in `run_when: "before_complete"` post-check that runs project-wide coverage when `state.testing.target_pct` is set. Per-unit `tests.coverage` blocks are refreshed (cross-unit regressions caught: a unit that was above target can be flagged below if other units' changes broke its coverage). The aggregate result is recorded in `state.testing.last_aggregate_check`. **Soft-fail at the aggregate level too** — below-target prints a yellow warning listing the offending units but still flips `state.status` to `complete`.

### Changed
- **`skills/plan/SKILL.md` Preflight validation** — three new required fields (UI test framework, API test framework, target coverage %) added to the validation table. Plan stops with a numbered missing-fields report if §12 is incomplete. `state.json` write now includes a `testing` block; re-plans overwrite it from §12.
- **`agents/unit-migrator.md` §5b migrated record schema** — `smoke` now carries `tests` (runner, passed/total) and `coverage_check` (pct, target_pct, below_threshold) sub-blocks in addition to the 0.4.0 `endpoints_hit` / `build` sub-blocks. The full `unit.tests` block (translated/skipped/generated/coverage) is also written alongside `smoke` on success. `manual` / `n/a` frameworks omit the test+coverage smoke sub-blocks gracefully.
- **`agents/unit-migrator.md` step 8 ("Add a placeholder test")** — now a no-op when 7c already produced real tests (the common case). Only fires when the team is on a `manual` / `n/a` runner and the agent wants to leave a TODO marker.

### Why this isn't a breaking change
No `schema_version` bump (state remains v3; the `tests` block on each unit is additive and ignored by anything that doesn't read it). The new `state.testing` block is new — older `state.json` files predating 0.5.0 will lack it, in which case `/scaffold`, the migrator's 7c, and `/verify`'s aggregate check all detect the absence and degrade to "manual / skip" gracefully. Teams already mid-migration on 0.4.0 can keep working without filling in §12; new units they migrate will skip 7c (recording `tests.skipped_reason = "state.testing not configured"`) until they re-run `/plan` after editing §12. `manual` / `other:` framework values also degrade to skip — never block.

### Out of scope (deferred)
- Mutation testing / property-based testing — overkill for behavioural-parity migration; revisit if a team asks.
- Hard-fail coverage mode — left out per the 0.5.0 soft-fail policy. A future minor could add `coverage_policy: "hard" | "soft"` in §12 if teams want it.
- E2E / browser tests (Playwright, Cypress) — different bar than unit coverage; out of scope for this release.

## [0.4.0] - 2026-05-13

Driven by a real FastAPI migration that surfaced two bugs the plugin should have caught: a hatchling `pyproject.toml` missing `[tool.hatch.build.targets.wheel] packages = ["app"]` (so `pip install -e ".[dev]"` failed), and SQLAlchemy routes using plain `.query()` for models with `relationship()` (so Pydantic serialised nested fields as `null` after the session closed). Common cause in both: the plugin generated artefacts and trusted the LLM that they worked, without ever executing them. This release adds execution-based gates at both production points.

### Added
- **`skills/scaffold/SKILL.md` "Smoke-build the subsystem"** — new mandatory gate between writing each subsystem's files and flipping `state.scaffold.<subsystem>.status` to `"done"`. Runs the install + build command for the chosen stack (e.g., `pip install -e ".[dev]" && python -c "import app.main"` for FastAPI, `dotnet build` for .NET, `./mvnw -q -DskipTests package` for Spring Boot, `npm install && npm run build` for Node-based UIs and NestJS) and records `smoke.command`, `smoke.exit_code`, `smoke.stderr_tail` on the subsystem block. On non-zero exit the subsystem stays `in_progress`, the user sees the captured stderr tail, and scaffold stops — does not advance to the next subsystem or to `state.status = "scaffolded"`. Unknown stacks record `"smoke": "n/a"` and proceed (graceful degrade).
- **`agents/unit-migrator.md` §5a "Smoke-test before finalising"** — new mandatory gate between writing target files and flipping `unit.status = "migrated"`. For API-touching units, boots the dev server (uvicorn for FastAPI, `dotnet run` for .NET, `./mvnw spring-boot:run` for Spring, `npm run start:dev` for NestJS) on a free port, waits for the health probe, hits each endpoint the unit added with a representative request derived from `migration.md §10` acceptance criteria or the schema's example values, and asserts both HTTP 2xx and that the response body conforms to the declared response schema field-for-field (non-Optional nested objects must be non-null with the declared keys — this is what catches lazy-load / serialisation bugs). For UI-touching units, runs `npm run build && npm run typecheck`. Cross-cutting units run both blocks. On any failure, takes the existing §4 failure path with a smoke-specific diagnostic that includes the actual response body or build error (specific enough that `/web-modernize:retry --with-prompt="…"` can paste it back). On success, records a `smoke` block on the unit alongside the migrated status. Unknown stacks record `"smoke": "skipped — no recipe"` and proceed.

### Changed
- **`skills/scaffold/SKILL.md` Per-subsystem checklist intro** — now states explicitly that the smoke-build gate must pass before a subsystem can be marked `done`, and that a failed gate halts scaffold rather than advancing.
- **`agents/unit-migrator.md` §5 structure** — split into §5a (smoke-test gate) and §5b (write the migrated record). A failed smoke test routes through §4's failure path so the user sees the actual reason and gets `/retry` as an option, instead of silently flipping to a status they'd later discover was broken.

### Why this isn't a breaking change
No schema bump (state remains v3). The new `smoke` blocks are additive fields on `scaffold.<subsystem>` and on each unit; existing tooling that doesn't read them is unaffected. No skill renamed or removed. Stacks without recipes degrade to `"smoke": "n/a"` / `"skipped"` rather than blocking — teams using custom or other stacks see no behaviour change. Teams whose scaffold already ran on 0.3.x and is already `scaffolded` keep working as-is; the new gates apply to new scaffold runs and new unit finalisations.

### Out of scope (future work)
This release deliberately does NOT ship per-stack template files (e.g., a tested `pyproject.toml` the scaffold copies verbatim) or a "Backend translation patterns" idioms section in unit-migrator. Both are useful follow-ups but were excluded so the execution-based safety net could ship without expanding scope; the gates will catch a future bad `pyproject.toml` or a missing `joinedload` even before those follow-ups land.

## [0.3.1] - 2026-05-12

Bug-fix patch driven by a real testing session. Migrated pages were looking wrong (custom legacy design system flattened to generic utility classes) and assets (images, favicon, fonts) were missing from the target's `public/` directory because the plugin didn't instruct Claude to handle either concern.

### Added
- **`agents/unit-migrator.md` §3 step 7b "Translate visuals, not just logic — preserve the legacy design"** — new explicit guidance to read adjacent CSS/SCSS/LESS files alongside `source_paths`, detect custom design-system class-name prefixes (e.g., `esh-*`, `app-*`), preserve visual fidelity when translating to Tailwind / CSS Modules / Material UI / etc., verify asset references resolve to the target `public/`, and append a "Design translation" mapping table to `notes/<unit.id>.md`.
- **`skills/scaffold/SKILL.md` "Copy legacy assets" step** — scans the legacy tree for common asset directories (`Pics/`, `images/`, `Content/`, `wwwroot/`, `assets/`, `fonts/`, `static/`, top-level favicons) and copies them into the target UI's `public/` (or `src/assets/` for Angular). Honors `migration.md §3` declared paths as authoritative when present; falls back to heuristics otherwise. Detects absolute-URL references in legacy CSS (e.g., `url('/Content/Pics/foo.png')`) and warns about target framework basePath implications. Idempotent — never overwrites existing target files.
- **`/web-modernize:scaffold --assets-only` flag** — runs ONLY the asset-copy step (skips framework/API/DB scaffolders and `verify.config.json` updates). For teams whose scaffold ran on a pre-0.3.1 plugin and need to backfill missing assets without touching the rest. Precondition: `state.status >= "scaffolded"`. Does not advance top-level status.
- **`templates/migration.md` §3 optional sub-sections** — "Legacy design system / custom CSS" (class-name prefixes, stylesheet locations, notes) and "Asset directories" (explicit list of paths in the legacy tree). If filled, both `/scaffold` and the migrator use them as authoritative; if blank, heuristics apply.

### Changed
- **`agents/unit-migrator.md` §3 step 1** — now also reads stylesheets adjacent to `source_paths` (sibling `*.css`/`*.scss`/`*.less`, files referenced via `<link>` / `@import`, project-wide style files), not just the source files. The legacy visual design lives in those stylesheets; reading them upfront is essential to preserving fidelity in step 7b.

### Why this isn't a breaking change
No schema bump (state remains v3). No skill renamed or removed. No behavior removed — only additive guidance and a new step. Existing scaffolds keep working; teams who hit the asset gap can run `/web-modernize:scaffold --assets-only` to backfill.

## [0.3.0] - 2026-05-12

### Breaking changes
- **`state.schema.json` bumped to v3.** Per-unit state moves out of `state.json.units[]` into one file per unit at `.claude/modernize/units/<unit-id>.json`. Top-level `state.json` now carries only workflow status, stacks, scaffold, lock, and an ordered `unit_ids` array.
- **`/web-modernize:init` no longer migrates older state files.** No schema-migration scripts ship with the plugin (the v1→v2 migrator added in 0.2.0 has been removed). If `state.json` exists with `schema_version != 3`, `/init` refuses with a clear message and asks the user to delete `.claude/modernize/` and re-init.
- **`/web-modernize:migrate <id>` now blocks on unmet dependencies by default.** Pass `--force` to restore the previous warn-and-stub behavior; the agent will stub missing dep imports with `// TODO: provided by <dep.id>` comments and record the override in `notes/<id>.md`.

### Added
- **`templates/unit.schema.json`** — per-unit object schema, referenced by every per-unit file under `.claude/modernize/units/`.
- **`.claude/modernize/units/`** directory created by `/init`. Tracked in git via `.gitkeep`.

### Changed
- **Per-unit file layout for multi-developer concurrency.** Two developers working on different units now edit completely different files; git merges trivially with zero conflicts. The headline win for teams that coordinate offline (standup-style) and pick disjoint units.
- **`/web-modernize:init`** — emits a schema v3 bootstrap state. Creates `.claude/modernize/units/` and `.claude/modernize/notes/` with `.gitkeep` files. Removes the v1→v2 schema migration block.
- **`/web-modernize:plan`** — seeds units by writing one file per unit to `.claude/modernize/units/<id>.json`. Maintains `state.unit_ids` in plan order. The re-runnable history-preservation logic now reads/writes the per-unit file instead of an in-memory array.
- **`/web-modernize:next`, `/migrate`, `/retry`, `/rollback`** — all read/write `.claude/modernize/units/<id>.json` instead of `state.units[]`. `/migrate` adds `--force` and blocks by default on unmet deps.
- **`/web-modernize:verify`, `/status`, `/report`, `/auth`, `/abandon`** — refactored to iterate `units/*.json` or the per-unit file by id. `/auth` now writes the synthetic `__auth__` unit to `units/__auth__.json` and ensures it heads `state.unit_ids`. `/abandon --soft` clears every per-unit file and resets `unit_ids: []`; `--hard` deletes `.claude/modernize/` including `units/`; `--unit <id>` writes one per-unit file and prunes the dep from every other unit's `depends_on`.
- **`/web-modernize:sync`** — per-file merge for `units/*.json` (Cases 1/2/3: only-on-remote → take, only-on-local → keep, both → field-level merge). Top-level `state.json` merge unchanged in spirit but updated for `unit_ids` and the schema v3 shape.
- **`agents/unit-migrator.md`** — all unit mutations write `units/<id>.json`. Top-level `state.json` is touched only for the `auth_done → in_progress` transition. Accepts a `force_deps` flag from `/migrate --force` to enable the stub-with-TODO behavior on demand.
- **`hooks/heartbeat.mjs`** — walks `.claude/modernize/units/*.json` instead of `state.json.units[]`. Heartbeat updates land in the per-unit file only; the hook no longer touches `state.json` at all, keeping the top-level file conflict-free across concurrent edits.

### Removed
- v1→v2 schema-migration block from `skills/init/SKILL.md` (added in 0.2.0). No migration scripts ship with the plugin going forward; schema bumps require a fresh `/init`.

### Versioning
- `state.schema.json` `schema_version` bumped to `3`. No automated migration from v1 or v2. To upgrade an existing repo, delete `.claude/modernize/` and re-run `/web-modernize:init` followed by `/analyze` and `/plan`. Notes under `.claude/modernize/notes/` are safe to copy back after re-init.

## [0.2.0] - 2026-05-11

### Added
- **`/web-modernize:rollback --unit <id>`** — soft inverse of `/migrate`. Reverts a single migrated, verified, or failed unit back to `pending` and restores its target files via git. Preserves design notes and history; populates new `rollback_info` field on the unit.
- **`/web-modernize:retry <unit-id> [--with-prompt="…"]`** — re-attempt a failed unit using the shared migration procedure. Optional `--with-prompt` lets the user steer the re-attempt with guidance the model layers on top of `migration.md`. Increments `retry_count` and preserves prior diagnostics in `failure.diagnostic_history[]`.
- **`/web-modernize:sync`** — pulls latest `state.json` from origin and merges it with the local copy using deterministic rules ("most-advanced unit status wins", "freshest heartbeat wins"). Replaces what would otherwise be a hand-resolved JSON merge conflict.
- **`/web-modernize:report [--format=md|json|html]`** — generates a stakeholder-friendly progress report (burndown, velocity, ETA, risk heat-map, ownership, blockers, acceptance-criteria status) at `.claude/modernize/reports/<date>-<format>`.
- **`agents/unit-migrator.md`** — shared per-unit migration procedure now used by `/next`, `/migrate`, and `/retry`. Consolidates the in-flight collision handling (Case A/B/C) and the translation body in one place, removing the previous "delegate by reference" drift risk between `/next` and `/migrate`.
- **`migration.md §9b Unit rename map`** (optional) — declare `old_id → new_id` mappings so re-running `/web-modernize:plan` carries unit history, notes, and verification forward across renames.
- **`state.schema.json` v2** — adds per-unit fields: `retry_count`, `last_retry_prompt`, `rollback_info`, `failure.diagnostic_history[]`. Required by the new failure-recovery commands.
- **`templates/report.md`** — Markdown template used by `/web-modernize:report`.

### Changed
- **`/web-modernize:init`** — when invoked on an existing `state.json` with `schema_version: 1`, performs an idempotent, lossless v1→v2 upgrade (adds the new per-unit fields). Closing nudge now points at `/analyze` first (auto-fills migration.md §2), then user edits §3–§11 on the populated source-stack section. This fixes the chicken-and-egg of "fill in source stack to run analyze that fills source stack".
- **`/web-modernize:plan`** — re-runnable without losing progress. Existing units are matched by id (with `§9b` rename map support); their `status`, `history`, `notes_path`, `verification`, `failure`, `retry_count`, `last_retry_prompt`, and `rollback_info` carry forward. Top-level `state.status` never rewinds on re-runs (e.g., a re-plan during `in_progress` stays `in_progress`). Existing scaffold blocks are preserved.
- **`/web-modernize:next`** — selection and closing message only; the translation body now lives in `agents/unit-migrator.md`.
- **`/web-modernize:migrate`** — same delegation as `/next`. Failed units now redirect to `/web-modernize:retry` (preserves diagnostic history); explicit override still allowed.

### Versioning
- `state.schema.json` `schema_version` bumped to `2`. `/init` migrates v1 → v2 on first run after upgrade. No team action required beyond running any plugin command.

## [0.1.1] - 2026-05-11

### Fixed
- `hooks/hooks.json` schema: wrap event matchers under a top-level `hooks` key so Claude Code's plugin loader accepts it. Previously installs failed with `Hook load failed: expected record, received undefined`.

## [0.1.0] - 2026-05-11

### Added
- Initial release.
- Plugin manifest and self-referencing marketplace.
- Ten skills: `init`, `analyze`, `plan`, `scaffold`, `auth`, `next`, `migrate`, `verify`, `status`, `abandon`.
- Team-facing `migration.md` template (11 sections).
- `plan.md` and per-unit notes templates.
- `state.schema.json` (schema_version 1) for the git-tracked progress ledger.
- `legacy-analyzer` subagent for source-stack detection.
- Optional `PostToolUse` heartbeat hook for stale-session detection.
- README with install instructions, five-step workflow, multi-developer notes, troubleshooting, and FAQ.
