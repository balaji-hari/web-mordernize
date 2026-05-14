# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This repository **is the source of a Claude Code plugin** named `web-modernize`. It is also its own marketplace — teams install the plugin by adding this repo as a marketplace, then installing the plugin from it. The plugin guides teams through migrating legacy web applications (ASP.NET WebForms / MVC, Java JSP / Spring MVC, AngularJS 1.x, classic PHP, ColdFusion, etc.) to modern stacks (React / Vue / Angular / Svelte / Next / SvelteKit, optional new API, optional new DB).

Repo URL: `https://github.com/balaji-hari/web-mordernize` (note the typo "mordernize" — the **plugin** itself is correctly named `web-modernize` everywhere in code).

## High-level architecture

The plugin's runtime artifacts split into two locations: this repo (plugin source) and the **user's** repo (state). Keep them straight when working in this codebase.

### Plugin source (this repo)

```
.claude-plugin/
  plugin.json              # manifest — name, version, author
  marketplace.json         # self-referencing marketplace (source: "./")
skills/<name>/SKILL.md     # one per slash command (15 total — see Slash command reference in README)
templates/                 # files copied into the user's repo by /init and /plan
  state.schema.json        # top-level state schema (schema_version 3)
  unit.schema.json         # per-unit object schema
agents/
  legacy-analyzer.md       # read-only subagent for source-stack detection
  unit-migrator.md         # shared per-unit migration loop used by /next, /migrate, /retry
hooks/
  hooks.json               # PostToolUse heartbeat
  heartbeat.mjs            # Node script that bumps last_heartbeat in each in-flight unit file
```

### User's repo (created/maintained by the plugin)

```
migration.md                            # 11+1 section configuration the team fills in
.claude/modernize/
  state.json                            # top-level workflow ledger; conforms to templates/state.schema.json
  units/<unit-id>.json                  # per-unit state; one file per unit; conforms to templates/unit.schema.json
  plan.md                               # generated migration plan
  analysis.json                         # source-stack analysis from /analyze
  verify.config.json                    # verification commands per target stack
  notes/<unit-id>.md                    # per-unit design notes
  reports/<date>-<format>               # generated stakeholder reports (from /report)
```

`state.json` holds top-level workflow state (status, stacks, scaffold, lock, ordered `unit_ids[]`). Per-unit state lives in its own file under `units/`. Every skill reads `state.json` and the relevant per-unit files on entry, and writes the per-unit file on per-unit mutations. Only top-level phase transitions (e.g., `auth_done → in_progress`, `→ complete`) and `/plan`'s ordering updates touch `state.json` itself.

### State machine

Top-level `state.json.status` transitions monotonically:

```
uninitialized → initialized → analyzed → planned → scaffolded → auth_done → in_progress → complete
```

Each skill enforces a precondition on this status and refuses (with a redirect to the correct skill) if it's wrong. The per-unit status (`pending → in_progress → migrated → verified`, plus `blocked` / `skipped` / `failed`) lives in each `units/<unit-id>.json` file.

### Multi-developer model

State is shared via git, not a server. The architecture targets teams that **coordinate offline** (standup, Slack) on unit assignments — the plugin does not arbitrate acquisition races between concurrent `/next` runs.

The per-unit file split is the load-bearing concurrency feature: Alice editing `units/LoginPage.json` and Bob editing `units/PaymentProcessor.json` touch completely different files, so git produces no conflict. Top-level `state.json` is mutated only on phase transitions, scaffold subsystem updates, and `/plan` re-runs — `/web-modernize:sync` reconciles those cleanly when collisions do happen.

Per-unit `in_flight` blocks (with a heartbeat bumped by `hooks/heartbeat.mjs` on every Write) signal who is working on what. An advisory `lock` on `state.json` exists for `/plan` and `/scaffold` (10-min TTL).

## Editing skills

Each `skills/<name>/SKILL.md` is a prompt that gets loaded into Claude's context when the slash command runs. Conventions to preserve:

- **YAML frontmatter** must include `description:` (used for skill discovery). Optional: `disable-model-invocation`, `model` (subagent only).
- **First section** is a state-check preamble: read `state.json`, verify precondition, redirect on mismatch.
- **Body** uses second-person ("You are the X skill..."). Be explicit about which files to read, which to write, and the exact state.json mutations.
- **Closing section** is a "suggested next step" the user should see. Strong nudges in the bootstrap path (`/init` → `/analyze` → `/plan` → `/scaffold` → `/auth`), soft nudges in the iteration loop (`/next` → `/verify`), none from terminal/diagnostic skills (`/status`, `/abandon`).

Skills cannot directly invoke other skills. They can only instruct Claude (via prose) to suggest the next slash command to the user.

`/web-modernize:next`, `/web-modernize:migrate`, and `/web-modernize:retry` all delegate the actual per-unit translation work to `agents/unit-migrator.md`. Don't duplicate the migration loop — edit it in `agents/unit-migrator.md`. The skills handle only unit selection, dependency gating, and the closing message; the agent handles in-flight collision resolution (Case A/B/C), unit acquisition, the translation body, and finalization.

## Editing templates

`templates/migration.md` is the team-facing config. Sections marked **REQUIRED** are validated by `/plan` — if you add a new required section, update the validation list in `skills/plan/SKILL.md`.

`templates/state.schema.json` and `templates/unit.schema.json` are JSON Schemas (draft 2020-12). Bump `schema_version` (top-level `const` in state.schema.json) when you make breaking changes. **Do NOT add migration logic.** The plugin has no production users yet; schema bumps require a fresh `/init`. `/init` should refuse to operate on a state file with a mismatched `schema_version` and tell the user to delete `.claude/modernize/` and re-init.

`templates/plan.md` and `templates/report.md` use `{{PLACEHOLDER}}` markers that the corresponding skill substitutes. New placeholders need a corresponding substitution rule in the skill.

## Versioning policy

- `.claude-plugin/plugin.json` has an **explicit** `version`. Without bumping this, users will NOT pull updates (Claude Code uses the manifest version for change detection).
- Patch (0.x.y → 0.x.y+1): bug fix, doc change, hook script tweak.
- Minor (0.x.y → 0.x+1.0): new skill, new framework support, additive schema change (rare, since we don't ship migrations).
- Major (0.x.y → 1.0.0): breaking state schema change (per-unit-file layout change, removed fields), renamed/removed skill, renamed slash command. Note: schema bumps require users to delete `.claude/modernize/` and re-init; this is acceptable while the plugin has no production users.
- Mirror version bumps in `.claude-plugin/marketplace.json` and `CHANGELOG.md`. Tag the release as `vX.Y.Z`.

## Local plugin development

To test the plugin against a real legacy app without publishing:

```sh
# In the user's legacy repo:
/plugin marketplace add C:/1/web-mordernize       # or your local path
/plugin install web-modernize
```

Then exercise the workflow:

```sh
/web-modernize:init
# edit migration.md
/web-modernize:analyze
/web-modernize:plan
/web-modernize:scaffold
/web-modernize:auth
/web-modernize:next
```

After changes to skills, you may need to re-install (`/plugin uninstall web-modernize && /plugin install web-modernize`) to pick them up — Claude Code caches plugin contents.

## What not to do

- Do not put `commands/`, `skills/`, `agents/`, or `hooks/` inside `.claude-plugin/`. Per the Claude Code plugin reference, only `plugin.json` and `marketplace.json` live in `.claude-plugin/`; everything else is at the plugin root.
- Do not invent slash commands not declared as `skills/<name>/`. The plugin namespace is enforced by Claude Code.
- Do not write the per-team `migration.md` from this repo's `templates/migration.md` without going through `/web-modernize:init` — the init skill has additional logic (git remote detection, gitignore patching) that copying alone misses.
- Do not store team-specific state in this repo. All team state belongs in **their** repo's `.claude/modernize/` directory.
