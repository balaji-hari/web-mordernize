# web-modernize

A Claude Code plugin that guides software teams through migrating legacy web applications — ASP.NET WebForms / MVC, Java JSP / Struts / Spring MVC, AngularJS 1.x, classic PHP, ColdFusion, jQuery-spaghetti, and similar — to a modern stack of the team's choosing. The plugin handles the workflow: analysis, plan generation, target scaffolding, auth migration, then unit-by-unit feature porting with verification. State is held in a git-tracked JSON ledger, so migrations span days and multiple developers without losing context.

> 📖 **Using the plugin to run a migration?** The [Developer Handbook](docs/DEVELOPER-HANDBOOK.md) is the hands-on guide — the full workflow, every command, the safety gates, the agents, and how a team runs it in parallel.

---

## Install

```sh
# 1. Add this repository as a marketplace (one-time, per developer machine):
/plugin marketplace add balaji-hari/web-mordernize

# 2. Install the plugin:
/plugin install web-modernize
```

After install, the plugin's commands appear under the `/web-modernize:` namespace. Type `/` in Claude Code and start typing `web-modernize` to discover them.

#### Install a specific version

To pin to a specific release (e.g., `v0.9.0`) instead of the latest commit on `main`, append `#<tag>` to the marketplace add command. The marketplace is then locked to that ref and `/plugin install` resolves the plugin from it:

```sh
# Pin to v0.9.0:
/plugin marketplace add balaji-hari/web-mordernize#v0.9.0
/plugin install web-modernize
```

You can also pin to a branch or commit SHA (`#main`, `#e4d01c6`) using the same syntax. To switch versions later, remove the marketplace first (`/plugin marketplace remove web-modernize`) and re-add it pointing at the new ref. There is no `/plugin install web-modernize@<version>` form — the marketplace ref is the version selector.

### Requirements

| Tool | Version | Why |
|------|---------|-----|
| Claude Code | latest | Plugin host |
| Node.js | ≥ 16 | The optional heartbeat hook (stale-session detection). Plugin still works without Node, just less precise about stalled migrations. **Note:** scaffolded UI stacks have their own, higher Node minimums — Vite-based stacks need Node 22, Next.js needs 20.10, Angular needs 20.11. The ≥ 16 floor is only for the heartbeat hook itself. |
| git | any modern version | All migration state is git-tracked |

The target stack you migrate **to** decides additional tooling (Node + npm for React/Vue/Svelte targets, .NET SDK for .NET targets, JDK for Spring Boot targets, etc.). The plugin uses your local toolchain; nothing is installed cloud-side.

### Update to a newer version

Claude Code caches plugin contents, so a `git pull` on this repo is not enough — users must explicitly refresh the marketplace and reinstall.

```sh
# 1. Refresh the marketplace so Claude Code sees the new version in plugin.json:
/plugin marketplace update web-modernize

# 2. Reinstall to pick up the new contents (uninstall first to clear the cache):
/plugin uninstall web-modernize
/plugin install web-modernize

# 3. Restart Claude Code (or exit the conversation with Ctrl+D and reopen with `claude`)
#    so the new hooks, skills, and agents load fresh in-memory.
```

Without the restart, skills picked up at the next slash-command invocation will reflect the new SKILL.md content, but hooks (e.g., `hooks/heartbeat.mjs`) are loaded once at session start and stay cached until you restart. If `/web-modernize:status` shows stale heartbeats after an update, that's the most likely cause.

#### If `/plugin install` still gives you the old version

Claude Code stores marketplace plugins in a per-user cache directory and resolves files from there rather than re-fetching on every install. When a reinstall surprises you with the previous version's behavior, clear the cache before reinstalling:

```sh
# macOS / Linux:
rm -rf ~/.claude/plugins/cache
/plugin install web-modernize

# Windows (PowerShell):
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache"
/plugin install web-modernize

# Windows (cmd):
rmdir /s /q "%USERPROFILE%\.claude\plugins\cache"
/plugin install web-modernize
```

Orphaned cache entries are normally garbage-collected after about a week, but the safest reset when you suspect cache staleness is to delete the directory and reinstall. Restart Claude Code afterwards (step 3 above) so hooks reload from the freshly fetched copy.

The currently installed version is shown in your Claude Code plugin list (and in `.claude-plugin/plugin.json` of this repo). Bumping `plugin.json` `version` is what tells Claude Code an update is available — see [CHANGELOG.md](./CHANGELOG.md) for what changes between versions.

If the new release bumps `state.schema.json` `schema_version`, this plugin does **not** ship migration scripts: delete `.claude/modernize/` and re-run `/web-modernize:init` (notes under `.claude/modernize/notes/` are safe to copy back after re-init). See the Versioning policy section below.

---

## The workflow

Once installed, every legacy repo follows the same shape. **Steps 1–5 are one-time setup; step 6 is the per-unit loop.**

```
One-time setup:
  1. /web-modernize:init       ← bootstrap scaffolding in this repo
  2. /web-modernize:analyze    ← detect source stack AND interactively fill migration.md
                                  target choices (§3 UI, §4 API, §6 strategy, §7 auth, §12 testing)
                                  via stack-aware AskUserQuestion prompts
  3. /web-modernize:plan       ← generate plan.md and unit list
  4. /web-modernize:scaffold   ← create target project skeleton (UI / optional API / DB) + copy legacy assets
  5. /web-modernize:foundation ← establish the foundational slice: auth (every feature unit depends on it) + any opted-in cross-cutting concerns

Per-unit loop:
  6. Loop until /web-modernize:status reports "complete":
       /web-modernize:next                  ← auto-pick the next eligible unit
       /web-modernize:migrate <unit-id>     ← OR explicitly pick a named unit (e.g., one assigned in standup)
       /web-modernize:verify                ← lint/typecheck/tests + behavioural-parity & security gate (+ advisory quality review)
       /web-modernize:parity-check <id>     ← (optional) on-demand behaviour diff vs legacy; acknowledge intentional changes
       /web-modernize:quality-check <id>    ← (optional) on-demand idiomatic-code + static-perf review (advisory; never blocks)
       /web-modernize:integrate             ← (anytime) assemble migrated units into the composed app (router/nav, whole-app smoke); incremental

     /next and /migrate <unit-id> do the same translation work — only unit
     selection differs. Use /next if you want the plugin to pick the next
     eligible pending unit; use /migrate <unit-id> when the team has already
     decided who takes what (standup, ticket assignment).

Failure recovery (any time after a /next or /migrate):
  /web-modernize:rollback --unit <id>   ← revert one unit's files via git
  /web-modernize:retry <id> [--with-prompt="…"]   ← re-attempt a failed unit

Multi-developer sync (anytime after others push):
  /web-modernize:sync           ← merge latest state.json from origin

Reporting (anytime after /plan):
  /web-modernize:report [--format=md|json|html]
```

Concretely, after step 1 your repo will contain:

```
your-repo/
├── migration.md                        ← team-editable configuration
├── .claude/modernize/
│   ├── state.json                      ← top-level workflow ledger (git-tracked)
│   ├── plan.md                         ← generated migration plan (git-tracked)
│   ├── analysis.json                   ← source-stack analysis (git-tracked)
│   ├── verify.config.json              ← verification commands per target stack
│   ├── units/<unit-id>.json            ← one file per migration unit (git-tracked)
│   └── notes/<unit-id>.md              ← per-unit design notes (git-tracked)
├── apps/web-new/                       ← target UI scaffold (created by /scaffold)
│   └── public/                         ← legacy assets (images, fonts, favicon) copied by /scaffold
├── apps/api-new/                       ← target API scaffold (optional)
└── (existing legacy source untouched)
```

Commit the `.claude/modernize/` directory. That's how Alice on Monday and Bob on Wednesday see the same progress. The per-unit split under `units/` is what makes concurrent work conflict-free — Alice editing `units/LoginPage.json` and Bob editing `units/PaymentProcessor.json` touch completely separate files; git has nothing to merge.

**Legacy code in a different folder/repo?** The layout above assumes source and target share one repo — the common case. If your legacy app lives elsewhere (a separate clone, a different git remote), mark `migration.md §1`'s "Legacy source in a separate repo/folder?" toggle `yes`, then copy `.claude/modernize/source_root.local.json.example` (created by `/init`) to `.claude/modernize/source_root.local.json` and set your own path there. That file is **gitignored** — it's a per-developer, machine-specific fact, not a team decision, so it never gets committed; only the yes/no toggle is shared. The layout then looks like:

```
some-parent-dir/
├── legacy-app/                          ← the legacy repo, cloned as a sibling, untouched
└── your-repo/                           ← the target repo (where you ran /init)
    ├── migration.md                     ← §1 toggle: yes
    ├── .claude/modernize/
    │   ├── source_root.local.json.example  ← tracked template
    │   ├── source_root.local.json           ← gitignored; { "source_root": "../legacy-app" }
    │   └── state.json                       ← uses_external_source: true (no path)
    ├── apps/web-new/
    └── apps/api-new/
```

Prefer a **relative** source root (`../legacy-app`) over an absolute path in your local file — it stays valid as long as you clone both repos as siblings; an absolute path only works on your own machine (which is fine, since the file is never shared anyway).

---

## Slash command reference

| Command | Purpose | When you run it |
|---------|---------|-----------------|
| `/web-modernize:init` | Bootstrap `migration.md` + `.claude/modernize/` (state.json, units/, notes/) | Once per legacy repo |
| `/web-modernize:analyze` | Detect source stack and entry points — pages, controllers, APIs **and background/non-UI units** (scheduled jobs, queue consumers, hubs, batch processors) via a separate non-route pass; exhaustive loop-until-dry discovery when the Workflow tool is available, single-pass fallback otherwise; auto-fill `migration.md §2` and interactively fill target choices | Immediately after `/init` |
| `/web-modernize:plan [--review-mode=plan-first\|auto]` | Validate `migration.md`, generate `plan.md` (incl. a Mermaid dependency graph), seed unit list (re-runnable; carries history forward). Sets the migration-wide **review mode** (the per-unit plan-gate default; sticky across re-plans) | After `migration.md` is complete; re-run whenever the unit list changes |
| `/web-modernize:scaffold [--assets-only]` | Create target project skeleton (UI, optional API, optional DB) **and** copy legacy assets (images, fonts, favicon) into the target's `public/`. `--assets-only` backfills assets on an already-scaffolded repo. | Once, after `/plan`. Re-run with `--assets-only` if assets were missed. |
| `/web-modernize:foundation [--no-plan]` | Establish the foundational slice — **auth** (login/logout/session, dev users) plus any cross-cutting concerns opted into in `migration.md §13` (i18n, feature flags, error handling, telemetry, logging). **Always-on consolidated design gate** (present design for all concerns → approve → write); implements them in parallel when possible; `--no-plan` skips the gate. Replaces the former `/auth`. | Once, after `/scaffold` |
| `/web-modernize:next [--plan \| --no-plan]` | Pick next pending unit and migrate it. Honors the **plan gate** (presents a plan, waits for approval before writing) per `review_mode`; `--plan`/`--no-plan` overrides for this unit | In a loop until migration is complete |
| `/web-modernize:next-batch [--n=K]` | Migrate up to K (default 3, max 8) independent pending units **in parallel** via the Workflow tool. **Always skips the per-unit plan gate** — parallel review of K plans doesn't compose; use `/next` for reviewed, one-at-a-time migration | When you want N× wall-clock speedup on the embarrassingly-parallel portion of a migration |
| `/web-modernize:migrate <id> [--force] [--plan \| --no-plan]` | Migrate a specifically named unit. Blocks on unmet deps unless `--force`; plan gate as above | When you need to jump to a unit out of order (debug) |
| `/web-modernize:retry <id> [--with-prompt="…"] [--plan \| --no-plan]` | Re-attempt a failed unit; preserves diagnostic history; plan gate as above | When `/status` shows a unit in `failed` status |
| `/web-modernize:rollback --unit <id> [--force-shared]` | Revert one unit's target files via git; reset to `pending`. **Refuses by default** if the unit owns shared files other units rely on (layout, shared utilities, `kind: shared`/`cross-cutting` outputs); `--force-shared` overrides after showing the blast radius | When a migrated/verified unit broke and you want a clean re-attempt |
| `/web-modernize:sync` | Merge latest `state.json` and per-unit files from origin into local | After pulling, when other developers have been working in parallel |
| `/web-modernize:verify [id] [--no-parity] [--no-quality] [--dynamic] [--capture-baseline]` | Lint + typecheck + test a migrated unit, **run a behavioural-parity + security check** and an **advisory migration-quality + static-perf review**, record evidence, flip to `verified`. `--dynamic` adds the opt-in dynamic tier (API replay + Playwright E2E, advisory); `--capture-baseline` records the legacy baseline | After each `/next`, or in batch |
| `/web-modernize:parity-check <id> [--all] [--acknowledge <finding-id> --reason "…"]` | Compare a migrated unit's behaviour against the legacy original (validation, output shape, sort order, error handling, UI states, **security: dropped authz / injection / output-encoding / secret-in-bundle / CSRF**); acknowledge intentional diffs | On demand, or when `/verify` reports a parity block |
| `/web-modernize:quality-check <id> [--all]` | **Advisory** review of a migrated unit's **code quality / idiomaticity + static performance** — legacy-paradigm leakage (WebForms-in-React, jQuery-in-a-reactive-framework), ceremonial error handling, dead abstractions, weak tests, and perf regressions (N+1, unbounded queries, waterfalls, blocking I/O, bundle bloat). Never blocks verification | On demand, when you want the migrated code to read idiomatically |
| `/web-modernize:integrate [--dry-run] [--final]` | Assemble migrated units into the composed app — central router + nav, whole-app smoke, orphaned-unit + cutover-coverage report, and (strangler-fig) the traffic-splitting proxy. **Idempotent**; run any time to integrate what's migrated so far, or `--final` for the end cutover | Periodically during migration, and at cutover |
| `/web-modernize:report [--format=md\|json\|html]` | Generate stakeholder progress report (burndown, ETA, risks) | Sprint syncs, exec updates, weekly digests |
| `/web-modernize:status` | Print progress dashboard (incl. artifact-drift staleness checks — flags when discovery moved but `/plan` wasn't re-run) | Anytime — read-only |
| `/web-modernize:unlock` | Force-clear a stuck advisory lock on `state.json` (requires typing `force-clear`) | When a Claude session crashed holding the lock and `/plan` or `/scaffold` is blocked |
| `/web-modernize:abandon` | Two-step destructive reset (`--soft`, `--hard`, `--unit <id>`) | When you need to start over or formally drop a unit |

---

### The plan-approval gate (review mode)

Code-generating commands present a plan and **wait for your approval before writing** — `[a]pprove` / `[r]evise` / `[c]ancel` (cancel writes nothing and leaves the unit `pending`). It's applied with judgment: it gates code generation, not read-only or bookkeeping commands (`/status`, `/parity-check`, `/quality-check`, etc. are never gated).

- **Per-unit gate (`/next`, `/migrate`, `/retry`) — opt-out, ON by default.** Set the migration-wide default once at `/plan`: `--review-mode=auto` turns the per-unit gate off for the whole migration (fast `/next` flow), `--review-mode=plan-first` (the default) keeps it on. It's persisted as `state.review_mode`, is **sticky across re-plans**, and can also be declared via an optional `Review mode:` line in `migration.md §6`. Override a single unit with `--plan` / `--no-plan`.
- **Foundation gate (`/foundation`) — always on.** The cross-cutting concerns (auth + any opted-in) are high-stakes and foundational, so the consolidated design gate runs **regardless of `review_mode`** (a team on `auto` still reviews the foundation). The only way to skip it is the explicit `--no-plan` flag.

---

## Talk to it naturally

You don't have to memorize the 19 slash-command names above. Every skill's `description:` field includes trigger phrases and lifecycle anchors that Claude Code's native skill auto-invocation uses to route plain-English requests to the right command.

Examples of utterances that route reliably:

| You type | Skill fired |
|---|---|
| *"start a migration"* / *"set up the project"* | `/web-modernize:init` |
| *"analyze the codebase"* / *"detect framework"* / *"walk me through setup"* | `/web-modernize:analyze` |
| *"let's plan it"* / *"create the plan"* | `/web-modernize:plan` |
| *"scaffold the new project"* / *"build the skeleton"* | `/web-modernize:scaffold` |
| *"what's next"* / *"continue"* / *"keep going"* | `/web-modernize:next` |
| *"where are we"* / *"show status"* / *"progress"* | `/web-modernize:status` |
| *"migrate the OrderController"* / *"do the login page"* | `/web-modernize:migrate <name>` |
| *"verify"* / *"run tests"* / *"is it passing"* | `/web-modernize:verify` |
| *"assemble the app"* / *"wire up routing"* / *"cutover"* | `/web-modernize:integrate` |
| *"check parity"* / *"does it behave like the old one"* | `/web-modernize:parity-check <id>` |
| *"is this idiomatic"* / *"code quality"* / *"check for jobol"* | `/web-modernize:quality-check <id>` |
| *"retry"* / *"try again"* | `/web-modernize:retry <id>` |
| *"rollback the LoginPage"* / *"undo this unit"* | `/web-modernize:rollback --unit <id>` |
| *"stuck lock"* / *"unlock"* | `/web-modernize:unlock` |
| *"generate a report for leadership"* | `/web-modernize:report` |
| *"sync state"* / *"after git pull"* | `/web-modernize:sync` |
| *"start over"* / *"wipe everything"* | `/web-modernize:abandon` |

The lifecycle anchor (`Use when state.status is X`) in each description disambiguates adjacent skills — *"let's plan"* fires `/plan` only when `state.status` is `analyzed`; otherwise Claude picks the next-best match (often `/status` or `/next`).

Slash commands still work for muscle memory; NL routing is purely additive.

---

## Adding a new framework

The plugin's framework knowledge lives in `frameworks/<name>.md` — one file per source or target stack. Adding a new framework is a **one-file drop-in**, no other edits required.

The currently-shipped set covers 17 source legacy stacks and 14 modern target stacks (8 UI + 6 API). For unsupported tech, the plugin's unknown-tech path takes over: the interview asks the user to specify what stack their app is (with free-text), and `/scaffold` asks for a scaffold command, test framework, and verify commands the first time it hits an unknown target. Answers persist in `verify.config.json` so retries don't re-ask.

To add a framework (e.g., `phoenix-elixir` as a target API):

1. Create `frameworks/phoenix-elixir.md` with frontmatter:
   ```yaml
   ---
   name: phoenix-elixir
   display_name: Phoenix (Elixir)
   role: target-api  # or target-ui, or source
   ---
   ```
2. Fill in the standard sections: `## Scaffold` (shell command), `## Test framework`, `## Verify commands` (target-api only — lint/typecheck/test commands `/scaffold` populates `verify.config.json`'s `api` block from), `## Auth notes`, `## Data migration` (target-api only — `Apply:`/`Status:` commands `/foundation`'s datastore-reachability preflight and DB-migration step read), `## Dev server` (table with port + dev command + URL + health check), `## Recommendation context` (optional, for the interview's source-stack-aware recommendations).
3. Reinstall the plugin and the new framework is immediately available — `/scaffold` reads the file when a user picks `phoenix-elixir` as their target API, `legacy-analyzer` reads it for source detection if `role: source`.

For source frameworks, also include a `## Detection` section listing strong and weak signals (file paths, library references, build files) the `legacy-analyzer` agent looks for.

---

## Editing `migration.md`

`/web-modernize:init` writes a template with 11 sections. Sections marked **REQUIRED** must be filled in before `/web-modernize:plan` will run.

| Section | Required? | Notes |
|---------|-----------|-------|
| 1. Project identity | recommended | Just metadata — name, team, ticket |
| 2. Source stack | AUTO | Filled by `/analyze`; override if it got something wrong |
| 3. Target UI framework | **yes** | Pick from react-vite-ts, next-app-router, vue3-vite, angular, svelte-kit, or custom. Scaffolds pull the latest stable major from each CLI via `@latest` — pin via §8 Constraints if you need an older LTS line. Includes two optional sub-sections (legacy design system, asset directories) — fill them for high-fidelity migrations. |
| 4. Target API framework | optional | Set to `none` for UI-only migrations — plan skips API work entirely |
| 5. Database | optional | `unchanged` is the most common; set if replatforming |
| 6. Migration strategy | **yes** | strangler-fig (default), big-bang (small apps), module-by-module |
| 7. Auth provider | **yes** | Current and target; drives the auth concern of `/web-modernize:foundation` |
| 8. Constraints | recommended | Must-keep URLs, compliance, deployment target |
| 9. Out of scope | optional | Explicit "don't migrate this" list |
| 9b. Unit rename map | optional | `old_id → new_id` mappings so re-runs of `/plan` carry history across renames |
| 10. Acceptance criteria | **yes** | At least 3 items; drives `/verify`'s pass/fail bar |
| 11. Risks & open questions | free-form | Plugin reads but doesn't validate |

You can re-edit and re-run `/web-modernize:plan` at any time — the plan and unit list will regenerate. Existing units' progress (`status`, `history`, `notes_path`, `verification`, `failure`, `retry_count`, `last_retry_prompt`, `rollback_info`) is preserved across re-plans by unit `id`. If you rename a unit, declare the mapping in `§9b Unit rename map` and history will carry forward (notes file will be renamed too). If a tracked unit (status beyond `pending`) drops off the plan without a rename mapping, `/plan` will keep it and print a warning rather than silently lose progress.

---

## Multi-developer workflow

The plugin assumes git is the source of truth. There is no central server; collaboration happens by committing and pulling.

### The contract

| Artifact | Git tracked? | Why |
|----------|--------------|-----|
| `migration.md` | yes | Shared configuration |
| `.claude/modernize/state.json` | yes | Top-level workflow ledger (status, stacks, scaffold, lock, unit_ids) |
| `.claude/modernize/units/<id>.json` | yes | Per-unit state — one file per unit |
| `.claude/modernize/plan.md` | yes | Reviewable migration plan |
| `.claude/modernize/notes/<id>.md` | yes | Per-unit design records |
| `.claude/modernize/verify.config.json` | yes | Team's verification commands |
| `CLAUDE.local.md` | **no** (gitignored) | Your personal scratch space |
| `.claude/settings.local.json` | **no** (gitignored) | Personal Claude Code settings |

### Designed for offline coordination

The plugin assumes teams **decide unit assignments out-of-band** (standup, Slack, ticket assignment) — not inside the tool. Alice and Bob agree in their morning standup: "Alice takes `PaymentProcessor`, Bob takes `LoginPage`." Each then runs:

```
# Alice:
/web-modernize:migrate PaymentProcessor

# Bob (separately, on his machine):
/web-modernize:migrate LoginPage
```

Behind the scenes, Alice's work touches only `.claude/modernize/units/PaymentProcessor.json` and her target files under `apps/web-new/src/features/payment/`. Bob's work touches only `units/LoginPage.json` and his target files under `apps/web-new/src/features/auth/`. **Their commits touch zero overlapping files.** When they push/pull, git merges trivially. No JSON conflict resolution, no `/sync` invocation needed.

### When `/sync` is useful

Per-unit files solve most of the multi-dev pain, but `state.json` itself (top-level: workflow status, scaffold subsystems, advisory lock, `unit_ids` array) is still shared. The few operations that mutate `state.json` are:
- Phase transitions (`/foundation` flipping `state.status` to `foundation_done`, `/verify` flipping it to `complete`, etc.).
- `/scaffold` updating per-subsystem `scaffold.{ui,api,db}` blocks.
- `/plan` re-runs updating `unit_ids` and stack fields.

If two devs trigger these simultaneously, `/web-modernize:sync` reconciles the top-level file deterministically (most-advanced status wins, freshest scaffold completion wins, etc.). It also handles the rare case where two devs edit the **same** unit's per-unit file.

### What about acquisition races?

If two devs both run `/web-modernize:next` at the same time without coordinating offline, they may both pick the same eligible unit before either pushes — and write to the same target files. The plugin does NOT auto-detect this. The offline coordination assumption is load-bearing: have your standup, agree on assignments, then run the commands. If your team genuinely cannot coordinate offline, file an issue describing the workflow and a `/claim`/auto-fetch follow-up can be added.

### Advisory locks

`/plan` and `/scaffold` write a top-level `lock` block to `state.json` while they run, with a 10-minute TTL. If another developer runs the same skill while a lock is held, they'll see a warning naming the holder. This is advisory only — git is still the real arbiter.

### Recommended cadence

- Commit `.claude/modernize/state.json` plus the relevant `units/<id>.json` and `notes/<id>.md` after every successful unit migration. Small commits make any remaining conflicts trivial.
- Use a branch per unit if your team's policy allows: the migration agent creates `modernize/<unit-id>` branches automatically when git is clean.
- Run `/web-modernize:status` before starting work — it shows what's in-flight elsewhere.

---

## Resuming after interruption

Claude Code's `claude --continue` restores your last conversation, including which skill was active.

Every skill in this plugin re-reads `state.json` on entry, so it picks up where it left off:

- If a unit is `in_progress` with a fresh `last_heartbeat`, the active skill will resume from `current_step`.
- If `last_heartbeat` is more than 15 minutes old, `/web-modernize:status` flags it as "possibly stalled" and `/next` offers three options: reclaim, skip, or abort.
- If a migration crashed mid-write, the feature branch `modernize/<unit-id>` is left in place for human inspection.

You don't need to remember "what was I doing?" — running `/web-modernize:status` always tells you.

---

## Troubleshooting

### `/web-modernize:plan` refuses to run

It's protecting you from a half-empty `migration.md`. The error message will list every missing field by section number. Open `migration.md`, fix those, re-run.

### `/web-modernize:analyze` says my framework is `unknown`

Your codebase didn't match any of the built-in heuristics with high confidence. Three options:
1. Edit `migration.md §2` manually with your best guess and re-run `/web-modernize:plan` — the plan will be skeleton-only but at least the workflow proceeds.
2. Look at `.claude/modernize/analysis.json` — `candidates[]` shows the analyzer's three best guesses. Pick one and override §2.
3. File an issue with a redacted sample so we can add detection support.

### A unit migration failed

The unit's status will be `failed` with `failure.diagnostic` populated. The plugin creates a `modernize/<unit-id>` branch when it starts work; that branch contains whatever it managed to write before stopping. Four options:
1. **Retry with guidance**: `/web-modernize:retry <unit-id> --with-prompt="<corrective hint>"`. Increments `retry_count`, preserves the prior diagnostic in `failure.diagnostic_history`, and runs the migration again with your override layered on top of `migration.md`.
2. **Roll back first, then retry**: `/web-modernize:rollback --unit <unit-id>` reverts any target files the failed attempt left behind, then `/web-modernize:retry <unit-id>` for a clean re-attempt.
3. **Declare out of scope**: `/web-modernize:abandon --unit <unit-id>`.
4. **Mark for human migration**: edit the unit's `units/<unit-id>.json` directly to set status `blocked` with a `failure.diagnostic` explaining why.

### Migrated pages look wrong / use generic styling instead of the legacy design

The migration agent has explicit instructions (as of v0.3.1) to detect the legacy custom design system, preserve class-name conventions, and translate visual intent faithfully — see `agents/unit-migrator-subagent.md` step 7b. If your unit still came out with generic styling:

1. Make sure `migration.md §3` "Legacy design system / custom CSS" is filled in with the class-name prefix(es) and stylesheet locations. The agent treats this as authoritative; heuristics are the fallback.
2. Confirm the agent had access to the legacy stylesheets — they should be in the same directory as the source files, or referenced via `<link>` / `@import`. The agent reads sibling `*.css`/`*.scss`/`*.less` automatically.
3. Re-migrate the unit with `/web-modernize:migrate <unit-id>` (it will ask "reset to pending and re-migrate?" — choose yes). The fresh pass picks up the new guidance.

### Migrated page shows broken images / missing favicon / 404s on assets

The plugin (as of v0.3.1) copies legacy asset directories (`Pics/`, `images/`, `Content/`, `wwwroot/`, `assets/`, `fonts/`, `favicon.ico`, etc.) into the target's `public/` during `/web-modernize:scaffold`. If your existing scaffold predates v0.3.1, or the auto-detection missed something:

1. Update the plugin (see "Update to a newer version" above).
2. Run `/web-modernize:scaffold --assets-only` to backfill assets onto an already-scaffolded repo. It scans the legacy tree, copies anything missing, and prints a summary. Top-level workflow status is unchanged.
3. For directories the auto-detection won't find, declare them in `migration.md §3` "Asset directories" — those are then authoritative.
4. If the legacy CSS uses absolute URLs like `url('/Content/Pics/foo.png')`, the scaffold step warns you and writes a note to `.claude/modernize/notes/__scaffold__.md` describing the base-path implications for your target framework.

### I want to start over

`/web-modernize:abandon --hard` is the nuclear option. It is two-step (run once, confirm, run again to actually delete). It removes:
- `.claude/modernize/` (state, plan, analysis, notes)
- Target scaffold directories (`apps/web-new/`, etc.)

It does NOT touch `migration.md` (so you can re-run `/web-modernize:init` and pick up your configuration) and does NOT touch git history.

If you want to keep your design notes for postmortem, use `/web-modernize:abandon --soft` instead.

### Two developers' state files conflict on merge

With per-unit files (schema v3), this should be rare — concurrent work on different units touches different files. But for the cases where it does happen (both devs edited top-level `state.json`, or both edited the same unit's file):

1. **Use `/web-modernize:sync`** (recommended). Run it after `git fetch` instead of `git pull`. It reads the remote `state.json` plus every remote `units/<id>.json`, applies these merge rules deterministically, and writes the result to your working tree for you to review and commit:
   - For each per-unit file: only-on-remote → take; only-on-local → keep; both → field-level merge (most-advanced status wins, freshest heartbeat wins, max `retry_count`, etc.).
   - For top-level `status`: take the higher of `complete > in_progress > foundation_done > scaffolded > planned > analyzed > initialized > uninitialized`.
   - For `unit_ids`: union, preserving remote order with local-only ids appended.
   - For `history[]` (per-unit): concatenate, de-duplicate, sort by `at`.
   - For `failure.diagnostic_history[]`: concatenate.
   - Prints a plain-language reconciliation report — no JSON hand-merging.

2. **Resolve manually with git**. Follow the same rules listed above, then commit and run `/web-modernize:status` to verify. Use this if `/sync` refuses (e.g., you have uncommitted changes under `.claude/modernize/`).

### The heartbeat hook isn't firing

Check `node --version` resolves to ≥ 16. Without Node, the hook silently no-ops and stale-detection just relies on whatever heartbeat the active skill writes directly. The migration still works; you just lose the "minute-by-minute liveness" signal.

---

## FAQ

**Q: Does this plugin work on UI-only legacy apps (no backend)?**
A: Yes — first-class case. In `migration.md`, set §4 Target API framework to `none` and §5 Database to `unchanged`. The plan, scaffold, and unit list will skip API/DB work entirely.

**Q: Can I edit `plan.md` directly?**
A: You can, but `/web-modernize:plan` will overwrite it on next run. Better to edit `migration.md` (the source) and regenerate. If you need a per-unit override (e.g., move one unit to a different phase, change its dependencies, or mark it skipped), edit the per-unit file at `.claude/modernize/units/<id>.json` directly — the plugin honors manual edits.

**Q: What if my target framework isn't in the dropdown for §3?**
A: Pick "Other" in the interview and type any name. `/scaffold` will run an unknown-target follow-up — ask for the scaffold command, test framework, and verify commands — then continue normally. To make the framework first-class so the next migration of the same stack uses recipes instead of follow-ups, drop a `frameworks/<name>.md` file in the plugin directory (see "Adding a new framework" above).

**Q: My team uses GitLab / Bitbucket, not GitHub. Does this still work?**
A: Yes for the plugin itself — git host doesn't matter. The marketplace install is via GitHub today; teams behind GHE / GitLab need to clone this repo internally and use `/plugin marketplace add` with the local clone path.

**Q: Can I run multiple migrations in the same repo?**
A: Not concurrently — `.claude/modernize/` is a single workspace. If you need to migrate two distinct legacy apps living in the same repo, treat each as a separate working directory (different `migration.md`, different `.claude/modernize/`).

**Q: What if my legacy code is in a different repo/folder from where I want the new code?**
A: Mark `migration.md §1`'s toggle `yes`, then copy `.claude/modernize/source_root.local.json.example` (created by `/init`) to `.claude/modernize/source_root.local.json` and set `source_root` to a path pointing at the legacy tree (already cloned locally — the plugin reads files directly, it doesn't fetch remotes). Prefer a path relative to your target repo (e.g. `../legacy-app`, a sibling clone). This local file is **gitignored** on purpose — the actual path is a per-machine fact, not something to commit; `/web-modernize:analyze` only records the team-wide `state.uses_external_source: true` flag (no path) plus `state.source_repo` (git provenance, safe to share). Every skill/agent that reads legacy code resolves against your local file from then on. The legacy tree stays strictly read-only — nothing is ever written there.

**Q: How do I add a new framework to detection?**
A: Drop a new `frameworks/<name>.md` file with `role: source` and a `## Detection` section listing strong/weak signals (file paths, library references, build files). See "Adding a new framework" above. PR welcome.

**Q: Can I commit `.claude/modernize/notes/` selectively (e.g., keep some private)?**
A: They're git-tracked by default. If a unit's notes contain something sensitive (credentials, internal links), redact in the notes file or use `.gitignore` to exclude that specific file. The plugin never reads anything from notes — only writes — so excluding from git is safe.

---

## Contributing

Issues and PRs welcome at [github.com/balaji-hari/web-mordernize](https://github.com/balaji-hari/web-mordernize).

### Versioning policy

The plugin uses explicit semver. The `version` field in `.claude-plugin/plugin.json` is the source of truth; teams pull updates only when this is bumped. Bump:
- **Patch** (0.1.0 → 0.1.1) — bug fix, doc change, hook script tweak
- **Minor** (0.1.x → 0.2.0) — new skill, new framework support, additive schema change
- **Major** (0.x.x → 1.0.0) — `state.schema.json` breaking change, removed/renamed skill, changed slash-command name

`state.schema.json` is versioned independently via the `schema_version` integer (currently `3`). **No migration scripts ship with the plugin** — a schema bump requires deleting `.claude/modernize/` and re-running `/web-modernize:init`. This is a deliberate choice while the plugin has no production users; carrying forward-migration code adds review burden and locks past decisions in. Per-unit notes at `.claude/modernize/notes/` are safe to copy back after re-init.

---

## License

MIT. See [LICENSE](LICENSE).
