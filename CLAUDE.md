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
skills/<name>/SKILL.md     # one per slash command (10 total)
templates/                 # files copied into the user's repo by /init and /plan
agents/legacy-analyzer.md  # read-only subagent for source-stack detection
hooks/
  hooks.json               # PostToolUse heartbeat
  heartbeat.mjs            # Node script that bumps state.json.in_flight.last_heartbeat
```

### User's repo (created/maintained by the plugin)

```
migration.md                            # 11-section configuration the team fills in
.claude/modernize/
  state.json                            # git-tracked progress ledger; conforms to templates/state.schema.json
  plan.md                               # generated migration plan
  analysis.json                         # source-stack analysis from /analyze
  verify.config.json                    # verification commands per target stack
  notes/<unit-id>.md                    # per-unit design notes
```

`state.json` is the single source of truth for "where is this migration?" — every skill reads it on entry and updates it on exit.

### State machine

Top-level `state.json.status` transitions monotonically:

```
uninitialized → initialized → analyzed → planned → scaffolded → auth_done → in_progress → complete
```

Each skill enforces a precondition on this status and refuses (with a redirect to the correct skill) if it's wrong. The per-unit status (`pending → in_progress → migrated → verified`, plus `blocked` / `skipped` / `failed`) lives inside each `units[]` entry.

### Multi-developer model

State is shared via git, not a server. The plugin adds an advisory `lock` block for full-repo operations (`/plan`, `/scaffold`) and an `in_flight` block per unit with a heartbeat. The real concurrency arbiter is a git merge conflict on `state.json`; the plugin's locks just make those conflicts loud and predictable.

## Editing skills

Each `skills/<name>/SKILL.md` is a prompt that gets loaded into Claude's context when the slash command runs. Conventions to preserve:

- **YAML frontmatter** must include `description:` (used for skill discovery). Optional: `disable-model-invocation`, `model` (subagent only).
- **First section** is a state-check preamble: read `state.json`, verify precondition, redirect on mismatch.
- **Body** uses second-person ("You are the X skill..."). Be explicit about which files to read, which to write, and the exact state.json mutations.
- **Closing section** is a "suggested next step" the user should see. Strong nudges in the bootstrap path (`/init` → `/analyze` → `/plan` → `/scaffold` → `/auth`), soft nudges in the iteration loop (`/next` → `/verify`), none from terminal/diagnostic skills (`/status`, `/abandon`).

Skills cannot directly invoke other skills. They can only instruct Claude (via prose) to suggest the next slash command to the user.

`/web-modernize:migrate` defers its main algorithm by reference to `/web-modernize:next` — don't duplicate the migration loop, edit it in one place.

## Editing templates

`templates/migration.md` is the team-facing config. Sections marked **REQUIRED** are validated by `/plan` — if you add a new required section, update the validation list in `skills/plan/SKILL.md`.

`templates/state.schema.json` is a JSON Schema (draft 2020-12). Bump `schema_version` (top-level `const`) when you make breaking changes, and add migration logic to `/init` to move old state forward.

`templates/plan.md` uses `{{PLACEHOLDER}}` markers that `/plan` substitutes. New placeholders need a corresponding substitution rule in the skill.

## Versioning policy

- `.claude-plugin/plugin.json` has an **explicit** `version`. Without bumping this, users will NOT pull updates (Claude Code uses the manifest version for change detection).
- Patch (0.x.y → 0.x.y+1): bug fix, doc change, hook script tweak.
- Minor (0.x.y → 0.x+1.0): new skill, new framework support, additive schema change.
- Major (0.x.y → 1.0.0): breaking state schema change, renamed/removed skill, renamed slash command.
- Mirror version bumps in `CHANGELOG.md`.

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
