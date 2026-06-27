# Plan: Make web-modernize friendlier — interactive migration.md fill + sharper NL routing

> **STATUS: ✅ SHIPPED** — all three parts are implemented: the interactive interview
> (`templates/migration-interview.json`, v0.10.0), the `frameworks/*.md` model + unknown-tech path
> (Part 3), and the NL-routing skill descriptions (all 16 skills carry `Triggers:` /
> `Use when state.status`). Retained for design history; **no longer open work.**

## Context

Today the `/init` → `/analyze` → manual edit → `/plan` flow has two rough edges:

1. **`migration.md` is filled by hand.** After `/init` and `/analyze` (which auto-fills §2 source stack), the user is told to open `migration.md` in an editor and manually fill §3 (target UI), §6 (strategy), §7 (auth), §10 (acceptance), §12 (testing). Required fields are validated only later by `/plan`, which dumps a numbered error list and stops. The plugin already knows the source stack at this point and could give framework-specific suggestions, but doesn't.
2. **Users must invoke skills by exact slash-command name.** All 15 skills have `disable-model-invocation: false`, so Claude *can* auto-invoke them from plain text — but each SKILL.md `description:` field is written as a one-line action summary with no intent keywords or state-of-life cues. Result: phrases like "what's next" or "let's start migrating" don't reliably route to the right command.

This change makes `/analyze` walk the user through filling required fields with stack-aware defaults (via `AskUserQuestion`), and rewrites every `description:` field with trigger phrases + state-machine cues so Claude's native auto-invocation reliably picks the right command from natural language. **No new skills, no new state, no schema changes.**

User-confirmed scope:
- Interview happens **after `/analyze`** (so suggestions are informed by detected source stack).
- NL routing is achieved by **sharpening existing `description:` fields**, not by adding a router skill.

---

## Part 1 — Interactive interview inside `/analyze`

### Where it lives

`skills/analyze/SKILL.md`. After the existing §2 auto-fill block (currently ending with the "After writing" summary), add a new **Interview phase** that runs before the closing summary.

### Skill flow (revised)

1. Preflight (unchanged) — `state.status` must be `initialized` or `analyzed`.
2. Run `legacy-analyzer` subagent → write `analysis.json` (unchanged).
3. Update `migration.md` §2 and `state.json.source_stack` (unchanged).
4. **NEW — Interview phase** (see schema below).
5. Print closing summary, now pointing at `/web-modernize:plan` as the next step (since all required fields are filled inline).

### Interview phase logic

Driven by a declarative question catalog at `templates/migration-interview.json` (new file). For each entry:

1. Read the current value of the corresponding section from `migration.md` using a `Grep`/`Read` of the section header range.
2. **Skip-if-filled:** if the field already holds a non-placeholder value (i.e., not an HTML comment like `<!-- e.g. ... -->` and not empty), skip the question silently. This makes the interview idempotent on `/analyze` re-runs and respects manual edits.
3. Otherwise, call `AskUserQuestion` with the question text, 2–4 predefined options, and a 5th implicit "Other" (the tool provides this automatically). The first option is labelled `(Recommended)` and is chosen by source-stack-aware logic in the SKILL.md prose (see Recommendation rules below).
4. After each answer, immediately `Edit` the relevant line(s) in `migration.md`. Don't batch — partial completion is recoverable.
5. If the user picks "Other" with custom text, write it verbatim (but still validate against the `/plan` enum where applicable, and re-ask if invalid — e.g., strategy must be one of `strangler-fig`/`big-bang`/`module-by-module`).

Bail-out: if the user picks "skip the rest" at any point (offered as the last option of the first question, see below), stop the interview cleanly. `migration.md` keeps whatever was filled so far, and `/plan` will print the usual validation errors for what's still missing. State stays `analyzed`.

### Question catalog (in `templates/migration-interview.json`)

Schema (illustrative):

```json
[
  {
    "id": "ui_framework",
    "section_anchor": "## 3. Target UI framework",
    "field_label": "Framework",
    "question": "Which target UI framework do you want to migrate to?",
    "header": "UI framework",
    "options": [
      { "label": "react-vite-ts", "description": "React 18 + Vite + TypeScript. Fast HMR, broad ecosystem, lightweight." },
      { "label": "next-app-router", "description": "Next.js App Router. SSR/RSC, file-based routing, good SEO." },
      { "label": "vue3-vite", "description": "Vue 3 + Vite. Gentle learning curve from Angular/template-heavy stacks." },
      { "label": "angular", "description": "Angular (latest LTS). Closest mental model to AngularJS or template-heavy MVC." }
    ],
    "recommend_by_source": {
      "angularjs-1": "angular",
      "aspnet-webforms": "react-vite-ts",
      "aspnet-mvc": "next-app-router",
      "aspnet-core-mvc": "next-app-router",
      "java-jsp": "react-vite-ts",
      "java-spring-mvc": "react-vite-ts",
      "java-struts": "react-vite-ts",
      "jquery-spaghetti": "react-vite-ts",
      "php-classic": "react-vite-ts",
      "coldfusion": "react-vite-ts",
      "*": "react-vite-ts"
    }
  },
  {
    "id": "ui_language",
    "section_anchor": "## 3. Target UI framework",
    "field_label": "Language",
    "question": "TypeScript or JavaScript?",
    "options": [
      { "label": "TypeScript", "description": "Recommended for any new web frontend in 2026." },
      { "label": "JavaScript", "description": "Smaller surface area; pick if team has no TS experience." }
    ],
    "default": "TypeScript"
  },
  {
    "id": "strategy",
    "section_anchor": "## 6. Migration strategy",
    "field_label": "Strategy",
    "question": "Which migration strategy?",
    "options": [
      { "label": "strangler-fig", "description": "Run legacy + new side by side; cut over route by route. Lowest risk, longest timeline." },
      { "label": "module-by-module", "description": "Migrate one feature/module at a time, ship each. Good for medium apps." },
      { "label": "big-bang", "description": "Cut over everything at once. Only for small apps or hard external deadlines." }
    ],
    "recommend_by_loc": { "<5000": "big-bang", "<50000": "module-by-module", "*": "strangler-fig" }
  },
  {
    "id": "current_auth",
    "section_anchor": "## 7. Auth provider",
    "field_label": "Current auth provider",
    "question": "What's the legacy app's current auth?",
    "options": [
      { "label": "<detected>", "description": "Inferred from analyze (e.g., 'ASP.NET Forms Authentication' if Web.config has <authentication mode='Forms'>)." },
      { "label": "Custom JWT", "description": "" },
      { "label": "Session cookie", "description": "" },
      { "label": "OIDC / SSO", "description": "Azure AD, Okta, Auth0, Cognito, etc." }
    ],
    "recommend_by_source": { "aspnet-webforms": "ASP.NET Forms Authentication", "java-spring-mvc": "Spring Security", "*": "<detected>" }
  },
  {
    "id": "target_auth",
    "section_anchor": "## 7. Auth provider",
    "field_label": "Target auth provider",
    "question": "What auth provider should the migrated app use?",
    "options": [
      { "label": "Keep current (bridge)", "description": "Wrap the legacy provider so existing sessions keep working. Lowest user impact." },
      { "label": "OIDC (Azure AD / Okta / Auth0)", "description": "Modern federated identity. Best if you can pick an IdP." },
      { "label": "Custom JWT", "description": "Roll your own. Only if you have a strong reason." }
    ]
  },
  {
    "id": "ui_test_framework",
    "section_anchor": "## 12. Testing",
    "field_label": "UI test framework",
    "question": "Which UI test framework?",
    "options": [
      { "label": "vitest", "description": "Recommended for Vite-based stacks (React/Vue/Svelte via Vite, SvelteKit)." },
      { "label": "jest", "description": "Default for Next.js and NestJS." },
      { "label": "karma-jasmine", "description": "Angular default." }
    ],
    "recommend_by_ui_framework": { "react-vite-ts": "vitest", "next-app-router": "jest", "vue3-vite": "vitest", "angular": "karma-jasmine", "svelte-kit": "vitest" }
  },
  {
    "id": "coverage_target",
    "section_anchor": "## 12. Testing",
    "field_label": "Target coverage %",
    "question": "Target test coverage percentage?",
    "options": [
      { "label": "80", "description": "Recommended baseline." },
      { "label": "70", "description": "Looser bar — useful if the legacy app has no tests today." },
      { "label": "60", "description": "Very loose — only if you accept tech debt." }
    ],
    "validate": "integer 0-100"
  }
]
```

Notes on coverage:
- §3a (legacy design system) and §3b (asset directories) stay non-interactive — they're OPTIONAL and auto-detected by `/scaffold`. Don't add questions for them.
- §4 (API framework), §5 (database), §8 (constraints), §9 (out of scope), §11 (risks) stay non-interactive. They're either optional or free-form; the editor remains the right surface.
- §10 (acceptance criteria) stays as the template's default 5-item checklist — that already satisfies `/plan`'s "≥3 unchecked items" rule, so no question needed unless the user wants to add team-specific items (which the closing summary nudges them to do).
- The catalog is the **only** place that knows the question/option text. The SKILL.md prose just instructs Claude to "load the catalog, iterate, skip-if-filled, ask, write." This keeps the catalog data-driven and editable without touching skill prose.

### Recommendation rules

Embed in the catalog (`recommend_by_source`, `recommend_by_loc`, `recommend_by_ui_framework` keys). The SKILL.md prose tells Claude to compute the recommended option per question by looking up the keys from `state.json.source_stack.primary`, `analysis.json.loc_estimate`, and the answer already given for `ui_framework`. The recommendation is just used to label the first option `(Recommended)` and pre-rank it — the user can always pick another option or "Other."

### State and idempotency

- No new state fields.
- No schema bump.
- `/analyze` continues to set `state.status = "analyzed"` once at the end (after the interview), as today.
- Re-running `/analyze` re-detects, re-fills §2, then runs the interview — which silently skips any field already filled. So re-runs are safe and only ask about gaps.

### Closing message (new)

Replace the current §3/6/7/10 nudge with:

```
✓ Analyzed: <framework> (confidence <pct>%)
✓ migration.md filled: <N of M required fields answered>

Next step:
  → Run /web-modernize:plan to generate the migration plan and seed units.

Want to tweak §10 acceptance criteria or §8 constraints? Edit migration.md by hand
— /plan re-reads the file on every run.
```

If any required field is still unset (because the user bailed), the closing instead lists what's missing and points back at the migration.md sections directly.

---

## Part 2 — Sharpen SKILL.md descriptions for state-aware NL routing

### Goal

When a user types raw text (no slash command), Claude's runtime should pick the right web-modernize skill based on (a) the user's intent and (b) the current `state.json.status`. This relies on Claude's native model-based skill auto-invocation: it reads every loaded skill's `description:` and chooses the best match. Today's descriptions are action-only ("Bootstrap migration.md…"); we need them to include trigger phrases and lifecycle anchors.

### New description format (one-line, packed)

Each `description:` field gets rewritten to follow this template:

```
<one-line action>. Use when state.status is <X>[ or <Y>]. Triggers: '<phrase 1>', '<phrase 2>', '<phrase 3>'[, '<phrase 4>'].
```

Trigger phrases are concrete user utterances Claude should match against. Lifecycle anchors disambiguate adjacent skills (e.g., "let's plan" should hit `/plan` if status is `analyzed`, not `/scaffold`).

### Per-skill new descriptions (proposed wording)

| Skill | New description |
|---|---|
| `init` | Start a brand-new modernization in this repo: create migration.md and the .claude/modernize/ scaffolding. Use when no .claude/modernize/ directory exists. Triggers: 'start a migration', 'set up the project', 'modernize this app', 'begin'. |
| `analyze` | Detect the legacy source stack, fill migration.md §2, and interactively walk the user through filling target choices (§3, §6, §7, §12). Use when state.status is 'initialized' (first run) or 'analyzed' (re-run to fill gaps). Triggers: 'analyze the codebase', 'what stack is this', 'detect framework', 'configure the migration'. |
| `plan` | Validate migration.md and generate the migration plan plus per-unit files. Use when state.status is 'analyzed' and migration.md required fields are filled. Triggers: 'create the plan', 'list the units', 'break it into units', 'plan the work'. |
| `scaffold` | Create the target project skeleton (UI/API/DB) and copy legacy assets into public/. Use when state.status is 'planned'. Triggers: 'scaffold the new project', 'create the target app', 'set up the new codebase'. |
| `auth` | Migrate authentication as the first slice. Use when state.status is 'scaffolded'. Triggers: 'migrate auth', 'do auth first', 'set up login on the new side'. |
| `next` | Pick the next pending unit (respecting dependencies) and migrate it. Use when state.status is 'auth_done' or 'in_progress'. Triggers: 'what's next', 'continue', 'keep going', 'migrate the next one', 'next page'. |
| `migrate` | Migrate a specific named unit, optionally bypassing dependency checks with --force. Use when state.status is 'auth_done' or 'in_progress' AND the user names a unit. Triggers: 'migrate <unit>', 'do the login page', 'translate <component>'. |
| `verify` | Run lint/typecheck/tests and transition a unit from 'migrated' to 'verified'. Use when at least one unit is in 'migrated' status. Triggers: 'verify', 'run tests', 'check the migration', 'is it passing'. |
| `retry` | Re-attempt a failed unit, optionally with extra guidance via --with-prompt. Use when a unit is in 'failed' status. Triggers: 'retry <unit>', 'try again', 'fix the failed unit', 'redo'. |
| `rollback` | Revert one unit's target files and reset it to 'pending'. Use to undo a single unit. Triggers: 'rollback <unit>', 'undo this unit', 'revert the migration of <unit>'. |
| `status` | Show progress, in-flight units, blockers, and the recommended next command. Read-only. Use any time. Triggers: 'where are we', 'show status', 'progress', 'how's the migration going', 'what's the state'. |
| `report` | Generate a stakeholder progress/velocity/risk report (md/json/html). Use when state.status is 'in_progress' or 'complete'. Triggers: 'generate a report', 'stakeholder update', 'progress report', 'export progress'. |
| `sync` | Reconcile local and remote state.json + per-unit files for multi-developer workflows. Use when the team works in parallel and git shows merge churn on state files. Triggers: 'sync state', 'pull teammates' changes', 'reconcile state'. |
| `unlock` | Force-clear a stale advisory lock on state.json (requires typing 'force-clear'). Use when /plan or /scaffold refuses due to a stale lock. Triggers: 'unlock', 'clear the lock', 'release the lock', 'stuck lock'. |
| `abandon` | Roll back the migration in part or whole (destructive; two-step confirmation). Use only when the user wants to stop or restart the migration. Triggers: 'abandon the migration', 'start over', 'wipe everything', 'cancel migration'. |

### Why this works without a router skill

- Claude Code's runtime ranks loaded skills by description-match against the user's utterance. Adding explicit trigger phrases moves the right skill to the top of the ranking deterministically.
- The `Use when state.status is X` clause is read by Claude (the model) and applied as a soft filter — when Claude sees the user say "let's plan" and `state.json` says `status: scaffolded`, the description tells it `/plan` is the wrong skill, so it'll pick the next-best match (likely `/next` or `/status`).
- No new code path; no new skill surface; no per-utterance routing logic to maintain. The model does the matching, the descriptions encode the rules.

---

## Critical files to modify

| File | Change |
|---|---|
| `skills/analyze/SKILL.md` | Add Interview phase between the §2 auto-fill block and closing summary. Update closing summary. Update frontmatter `description:` per Part 2 table. |
| `templates/migration-interview.json` | **NEW**. Question catalog (schema above). |
| `skills/init/SKILL.md` | Update closing "Next steps" to remove the "Open migration.md and fill in sections 3, 6, 7, 10" line; replace with "Run `/web-modernize:analyze` next — it detects your stack and walks you through filling target choices." Update frontmatter `description:` per Part 2 table. |
| `skills/{plan,scaffold,auth,next,migrate,verify,retry,rollback,status,report,sync,unlock,abandon}/SKILL.md` | Update frontmatter `description:` only — per Part 2 table. No body changes. |
| `.claude-plugin/plugin.json` | Bump version `0.9.3` → `0.10.0` (additive behavior change; no schema change). |
| `.claude-plugin/marketplace.json` | Mirror version bump. |
| `CHANGELOG.md` | New entry under `0.10.0`: (a) interactive interview in `/analyze`; (b) all skill descriptions rewritten for natural-language routing. |
| `README.md` | Update "The workflow" section to remove the manual-edit step between `/analyze` and `/plan`. Add a short "Talk to it naturally" subsection noting that users can type plain text instead of slash commands (e.g., "what's next?", "let's plan it"). |

### Existing utilities to reuse (no new code)

- `AskUserQuestion` tool — already a Claude Code primitive; used directly from SKILL.md prose. No wrapper needed.
- `Edit` tool — for in-place writes to `migration.md` after each answer.
- `Read` tool — to load `migration.md`, `analysis.json`, `state.json`, and `migration-interview.json`.
- The existing `legacy-analyzer` subagent stays unchanged — it still runs first and produces `analysis.json`, which the interview phase reads for recommendation logic.
- The existing `skills/plan/SKILL.md` validation block is the safety net — no need to duplicate validation in `/analyze`. If the interview is incomplete, `/plan` still catches it.

### Out of scope (explicitly not changing)

- No new skill (`/configure`, `/do`, `/help` — all rejected). Interview lives inside `/analyze`; routing lives in descriptions.
- No schema changes — `templates/state.schema.json` and `templates/unit.schema.json` untouched.
- No changes to `agents/unit-migrator.md`, `agents/legacy-analyzer.md`, `agents/permanent-gotchas.md`, or `hooks/`.
- No interview questions for OPTIONAL sections (§3a, §3b, §4, §5, §8, §9, §11). Users who care edit by hand; users who don't get sensible auto-detection at `/scaffold` time.

---

## Verification

### Manual end-to-end (the primary check — there's no test harness in this repo)

In a separate **legacy app** workspace (e.g., the eShopLegacy ASP.NET WebForms sample, or any small Spring MVC/AngularJS repo):

1. Re-install the plugin from the local path:
   ```sh
   /plugin uninstall web-modernize
   /plugin marketplace add C:/1/web-mordernize
   /plugin install web-modernize
   ```
2. Run `/web-modernize:init`. Confirm the closing message now points at `/analyze` for interactive filling (no longer says "open migration.md and fill in sections 3,6,7,10").
3. Run `/web-modernize:analyze`. Confirm:
   - `analysis.json` is written and `migration.md §2` is filled (existing behavior).
   - After §2 fill, an `AskUserQuestion` prompt appears for the UI framework with the source-stack-appropriate recommendation labelled `(Recommended)` (e.g., for an AngularJS app, `angular` is recommended).
   - Subsequent questions for language, strategy, current auth, target auth, UI test framework, coverage % all fire and write to `migration.md`.
   - Each answer is reflected in `migration.md` immediately after picking it (verify by `git diff migration.md` between answers).
4. Re-run `/web-modernize:analyze`. Confirm:
   - §2 is re-filled (existing behavior).
   - The interview SKIPS every question whose section is already filled — no duplicate prompts.
5. Run `/web-modernize:plan`. Confirm:
   - It accepts the file with no validation errors (since all required fields were filled by the interview).
   - `plan.md` and `units/*.json` are written.
6. Type natural-language utterances and confirm Claude proposes the right skill (Claude Code's auto-invocation will surface the skill name in its response):
   - "what's next" (after step 5) → `/web-modernize:status` or `/web-modernize:scaffold`
   - "let's scaffold" → `/web-modernize:scaffold`
   - "start the migration" (in a fresh repo) → `/web-modernize:init`
   - "where are we" → `/web-modernize:status`
   - "stuck lock" → `/web-modernize:unlock`

### Sanity checks in this repo

1. `git diff` shows only the files listed in the table above — no incidental edits to agents, hooks, or schemas.
2. Frontmatter YAML in every modified SKILL.md still parses (no broken indentation in the new multi-line description blocks — keep them as single-line strings or quoted folded scalars `>` to be safe).
3. `templates/migration-interview.json` is valid JSON (catch typos before shipping).
4. Plugin version is consistent across `plugin.json`, `marketplace.json`, and `CHANGELOG.md`.

### Bail-out path verification

In the legacy app workspace, run `/web-modernize:analyze` and answer "Other → skip the rest" at the first question. Confirm:
- `migration.md` retains only the partial fill so far.
- `state.status` is `analyzed`.
- Running `/web-modernize:plan` prints the usual validation errors for the unset required fields (existing behavior — proves the safety net still works).

---

## Part 3 — Per-framework files and unknown-tech path

### Context

Parts 1 and 2 left framework knowledge spread across three files: `agents/legacy-analyzer.md` (12 source-stack detection heuristics in a table), `skills/scaffold/SKILL.md` (5 UI + 6 API target scaffold recipes), and `skills/auth/SKILL.md` (per-API password-hashing recipes). Part 1's draft of `templates/migration-interview.json` proposed hardcoding the same lists a fourth time.

Adding a framework today means surgery in 3+ files. SKILL.md prose mixes workflow logic with reference data, and every framework's recipe loads into context on every skill invocation — even though only one target was picked. The `custom` branch in `/scaffold` already exists but is bare ("tell the user we don't have a recipe"); no equivalent path exists for unknown source stacks, unknown auth providers, or unknown test frameworks.

User-confirmed scope:
- **Don't** introduce a JSON registry. Markdown prose recipes read naturally where JSON data doesn't (scaffold commands and detection heuristics need code fences, not strings).
- **Don't** add per-framework feature toggles or new skills. The user's recorded preference for *pattern-level over scenario-level* rules out a `/add-framework` skill or new state-field explosion.
- **Do** move per-framework recipes out of `legacy-analyzer.md` / `scaffold/SKILL.md` / `auth/SKILL.md` into a new top-level `frameworks/` directory.
- **Do** treat "no file for this framework" as the first-class unknown-tech signal.

### 3a. New `frameworks/<name>.md` files — one per known framework

Create a new top-level `frameworks/` directory (sibling of `skills/`, `agents/`, `templates/`). Each known framework gets one markdown file with consistent headings:

```markdown
---
name: react-vite-ts
display_name: React 18 + Vite + TypeScript
role: target-ui                          # target-ui | target-api | source
---

## Detection
(source files only) Signals indicating this stack is present in a legacy repo.
- <signal>

## Scaffold
(target files only) Shell command(s) to scaffold a new project.

```sh
<command>
```

## Test framework
<name> (default). Install + sample-test recipe.

## Auth notes
(API targets) Stack-specific auth gotchas. Cross-cutting rules stay in permanent-gotchas.

## Dev server
| Dev port | Install/activate | Dev command | URL |
|---|---|---|---|
| ... | ... | ... | ... |

## Recommendation context
(optional) Source stacks this is a natural target for.
```

Currently shipped: 17 source stacks (aspnet-{webforms,mvc,core-mvc}, java-{jsp,struts,spring-mvc,spring-boot}, angularjs-1, vue-2, jquery-spaghetti, php-classic, coldfusion, vbscript-asp-classic, ruby-on-rails, django, wordpress, extjs) + 8 target UI (react-vite-ts, next-app-router, vue3-vite, angular, svelte-kit, astro, nuxt, remix) + 6 target API (dotnet-minimal-api, spring-boot-3, nestjs, fastapi, express, hono).

### 3b. Consumers read frameworks/*.md on demand

- **`agents/legacy-analyzer.md`** — replace inline detection table with: glob `frameworks/*.md` where frontmatter `role: source`, read each `## Detection` section, score signals against the source tree, return top match or `{ primary: "unknown", confidence: 0, evidence: [...] }`. Adding a source framework no longer requires editing the agent.
- **`skills/scaffold/SKILL.md`** — after reading `state.json.target_stack.ui` / `.api`, read `frameworks/<ui>.md` / `frameworks/<api>.md`; execute `## Scaffold`. Missing file → 3.3 unknown-target follow-up.
- **`skills/auth/SKILL.md`** — read `frameworks/<api>.md` `## Auth notes` if present; always also reference `permanent-gotchas` for cross-cutting rules. Missing file → skip stack-specific template, do not block.
- **`templates/migration-interview.json`** (created in Part 1) — drop verbose per-option descriptions; option lists become arrays of framework IDs and the interview skill resolves display names from `frameworks/<id>.md` frontmatter.

### 3c. "No file" = first-class unknown-tech path

- **Unknown source (`/analyze`)**: `legacy-analyzer` returns `primary: "unknown"` with raw evidence (file extensions seen, library references, build files). The interview phase (Part 1) surfaces the evidence and adds an explicit free-text "**None of these — let me specify**" option. User-supplied value persists to `state.json.source_stack.primary` with new additive field `state.json.source_stack.user_provided: true` (no schema bump — schema already accepts free-text strings).
- **Unknown target UI/API (`/scaffold`)**: 3 `AskUserQuestion` follow-ups: scaffold command (or `manual`), test framework, lint/typecheck/test commands. Answers written to `.claude/modernize/verify.config.json` so retries don't re-ask. Optionally offer to save a stub `frameworks/<name>.md` in the user's repo for future re-use.
- **Unknown target auth (`/auth`)**: skip stack-specific password-hashing template, do NOT block; produce an auth plan that defers to `permanent-gotchas` + OWASP. Code generation falls to `unit-migrator`.

### What Part 3 explicitly does NOT do

- **No JSON registry.** Markdown prose keeps recipes readable as prose.
- **No schema enum on `target_stack.ui` / `.api`.** Already free-text; keep that way.
- **No new skills** (`/add-framework`, `/teach`). Adding a framework is "drop a markdown file in `frameworks/`".
- **No changes to `permanent-gotchas.md`'s role.** Shape-agnostic patterns continue to land there. Per-framework files cover one stack's recipes; `permanent-gotchas` covers cross-cutting rules (e.g., bcrypt 72-byte truncation applies to any stack using bcrypt).

### Critical files modified (Part 3)

| File | Change |
|---|---|
| `frameworks/<name>.md` × ~31 | **NEW.** One per source / target-ui / target-api stack. |
| `agents/legacy-analyzer.md` | Detection table replaced with glob-and-read flow; emits `unknown + evidence` when no rule matches. |
| `skills/scaffold/SKILL.md` | Per-stack recipe branches replaced with read-framework-file flow + unknown-target 3-question follow-up. |
| `skills/auth/SKILL.md` | Per-stack auth recipes replaced with read-framework-file flow; missing file = defer to permanent-gotchas. |
| `skills/analyze/SKILL.md` | Low-confidence path now surfaces evidence + free-text option; sets `state.source_stack.user_provided = true`. |

### Existing utilities to reuse (no new code)

- `AskUserQuestion` — for unknown-target follow-ups in `/scaffold`.
- `Read` + `Glob` — skills load `frameworks/*.md` on demand.
- `verify.config.json` — already framework-agnostic with `${ui_root}` / `${api_root}` placeholders; just write user-supplied commands into it.
- `agents/permanent-gotchas.md` — shape-agnostic knowledge surface (unchanged role).

### Verification

In a legacy app workspace where the source stack is *not* covered (e.g., Phoenix/Elixir or Grails — neither shipped):

1. Run `/web-modernize:analyze`. Confirm `legacy-analyzer` reports `confidence: low` with raw evidence (mix.exs / grails-app/ etc.) instead of force-fitting a label.
2. Confirm the interview shows the evidence + free-text "specify your own" option; enter a custom value; confirm `state.json.source_stack.user_provided === true`.
3. Pick "Other" for UI target → enter an unknown name. Run `/web-modernize:scaffold` — confirm 3 follow-up questions fire, scaffold command runs, `verify.config.json` updated.
4. Run `/web-modernize:auth` with the unsupported target API — confirm it does NOT block; produces an auth plan referencing `permanent-gotchas` + OWASP.

**Extensibility check**: Drop a hand-written `frameworks/<custom-name>.md` with a `## Scaffold` section. Re-run `/web-modernize:scaffold` for a project with `target_stack.ui = <custom-name>` — confirm the skill picks up the new file with no other edits. Adding a framework is genuinely one file.
