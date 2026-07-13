---
description: "Detect the legacy source stack, fill migration.md §2, and interactively walk the user through filling target choices (§3 UI, §4 API, §6 strategy, §7 auth, §12 testing) via AskUserQuestion with stack-aware recommendations. Use when state.status is 'initialized' (first run) or 'analyzed' (re-run to fill gaps). Triggers: 'analyze the codebase', 'what stack is this', 'detect framework', 'configure the migration', 'walk me through setup'."
disable-model-invocation: false
---

# `/web-modernize:analyze`

You are the **analyze** skill. Your job is to detect what the team is migrating *from* and record what you find.

## Preflight

1. Read `.claude/modernize/state.json`. Required.
   - If `status != "initialized"` and `status != "analyzed"` (re-run), explain to the user that analyze runs after `/web-modernize:init` and stop.
2. Read `migration.md`. Required.
3. **Resolve the source root.** Read `${CLAUDE_PLUGIN_ROOT}/skills/_shared/source-root-resolve.md` and follow it to get `SOURCE_ROOT` (the resolved absolute path; `null`-equivalent means the working directory). Then, beyond that shared resolution, `/analyze` alone does the deeper validation and the team-fact bookkeeping:
   - If `.claude/modernize/source_root.local.json` was absent (same-repo, the common case): leave `state.uses_external_source` as-is (default `false`); nothing further to do here.
   - If present, validate the resolved path:
     - Does not exist, or is not a directory → **STOP**: `✗ .claude/modernize/source_root.local.json's "source_root" ('<raw>') resolves to <abs>, which does not exist or is not a directory. Fix the path (or clone the legacy repo there) and re-run.` Do NOT silently fall back to scanning the working directory.
     - Resolves to a path **inside** the target repo → **STOP**: `✗ source_root ('<raw>') points inside the target repo. That is the same-repo layout — delete source_root.local.json instead.` (If it resolves to exactly the target repo root, treat it as same-repo — harmless.)
     - Otherwise, try `git -C <abs> rev-parse --show-toplevel` and `git -C <abs> rev-parse --short HEAD`. If it succeeds, record `state.source_repo = { remote: <git config --get remote.origin.url, or "">, root_commit: <short SHA> }` — this is safe to share via git (it's the same for every teammate), unlike the local path itself. If it fails (not a git repo), warn the user once (provenance only — this is not fatal) and proceed.
     - Set `state.uses_external_source = true` (the team-wide fact — no path — mirrors `migration.md §1`'s toggle; set it regardless of whether the toggle was already marked `yes`, since the local file is the actual source of truth for behavior).
   - If `migration.md §1`'s toggle says `yes` but no local file exists yet, warn once: `⚠ migration.md §1 says legacy source is external, but .claude/modernize/source_root.local.json doesn't exist yet. Copy source_root.local.json.example and set your path — until then, SOURCE_ROOT falls back to the working directory.` (Non-fatal — proceed with the working directory.)
4. Confirm the source tree is non-empty: `SOURCE_ROOT` contains something other than just `.git/`, `.claude/`, `migration.md` (this check is only meaningful when `SOURCE_ROOT` == the working directory; an external `SOURCE_ROOT` is a legacy checkout and is expected to already be non-empty — just confirm it has files at all).

## Detection strategy

The output is the same `analysis.json` payload either way — pick the method by what's available.

### Method A — Workflow orchestration (preferred when the Workflow tool is available)

Running `/web-modernize:analyze` is your authorization to use the **Workflow tool**. When it's available, invoke the bundled discovery workflow — it fans out the `legacy-analyzer` agent **loop-until-dry** (rounds of parallel, scoped passes until two consecutive rounds find nothing new), so it enumerates entry points a single pass would truncate or sample-miss on a large estate (the analyzer caps at ~100 entry points per pass). Tell the user the rough agent count first (one detect pass + a few workers per round).

```
Workflow({ scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/analyze-discovery.js", args: { sourceDir: "<SOURCE_ROOT>" } })
```

`<SOURCE_ROOT>` is the resolved absolute path from the preflight above (the working directory in the common case). The workflow's `entry_points[].files` come back relative to it.

It returns one object in the **same shape as `analysis.json`** (detect metadata + a merged, deduplicated `entry_points[]` + `warnings` + `rounds`). Surface the workflow's `log()` lines as they arrive. The workflow's agents are read-only — **you** write `analysis.json` from the returned object (Output 1 below), exactly as in Method B. If the Workflow tool is NOT available (older Claude Code build, headless run), fall through to Method B automatically.

### Method B — single subagent pass (fallback)

Delegate to the `legacy-analyzer` subagent (defined at `${CLAUDE_PLUGIN_ROOT}/agents/legacy-analyzer.md`). Invoke it with a prompt like:

> Analyze the legacy web application rooted at `<SOURCE_ROOT>` (the resolved absolute path from the preflight above — the current working directory in the common case). Report: primary framework + version + confidence; build tool / package manager; top 5 libraries; approximate LOC; entry points (pages/controllers/components); rough dependency graph (which files import which); and a styling-detection pass (CSS frameworks/preprocessors, stylesheet-vs-CSS-in-JS approach, rule-count estimate, shared stylesheets referenced by more than one entry point). Emit every `entry_points[].files` and `styling.*.path` value **relative to that root**. Load detection rules from `${CLAUDE_PLUGIN_ROOT}/frameworks/*.md` files where `role: source`. If no rule matches, return `primary: "unknown"` with the `evidence[]` array populated. Format the report as JSON matching the schema in the agent's own preamble (including its `## Styling detection` section). Skip `.git/`, `node_modules/`, `bin/`, `obj/`, `dist/`, `build/`, `.claude/`.

Run the subagent, then validate the JSON it returns. If invalid, fix obvious errors and ask the subagent to retry once.

Either way, the validated result is the payload you write to `analysis.json` (Output 1).

## Frameworks to recognize

Detection rules are **data-driven** — the plugin ships one file per known framework at `${CLAUDE_PLUGIN_ROOT}/frameworks/<name>.md` with `role: source`. Adding a new source framework means dropping a new file in `frameworks/`, not editing this skill or the legacy-analyzer agent.

To see the currently-supported set, `Glob` `${CLAUDE_PLUGIN_ROOT}/frameworks/*.md` and filter by frontmatter `role: source`.

For frameworks the plugin doesn't have a file for (e.g., Phoenix, Grails, Wicket): `legacy-analyzer` returns `primary: "unknown"` with `evidence[]` listing the raw signals found, and the **Interview phase** below surfaces those signals to the user with a free-text "specify your own" option.

## Output 1: `.claude/modernize/analysis.json`

Write a complete payload. Schema:

```json
{
  "analyzed_at": "<ISO timestamp>",
  "primary": "<framework key from frameworks/*.md name:, or 'unknown'>",
  "confidence": 0.0,
  "candidates": [{ "name": "...", "confidence": 0.0 }],
  "evidence": ["<raw signal, required when primary == 'unknown'>"],
  "detected_version": "<string or null>",
  "build_tool": "<msbuild|maven|gradle|npm|yarn|none|...>",
  "package_manager": "<nuget|npm|yarn|maven|...>",
  "loc_estimate": 0,
  "top_libraries": [{ "name": "...", "version": "...", "purpose": "..." }],
  "entry_points": [
    { "id": "LoginController", "kind": "controller", "files": ["..."] }
  ],
  "styling": {
    "frameworks": ["bootstrap"],
    "preprocessors": ["sass"],
    "approach": "stylesheets",
    "rule_count_estimate": 0,
    "shared_stylesheets": [{ "path": "...", "referenced_by_estimate": 0 }]
  },
  "dependency_graph_summary": "<one-paragraph description>",
  "warnings": ["<any caveats, e.g., 'mixed asp.net mvc and webforms'>"]
}
```

Omit `styling` entirely (not an empty object) when the analyzer found no stylesheets to report.

`entry_points[]` is the seed list that `/web-modernize:plan` will turn into per-unit files under `.claude/modernize/units/<id>.json` plus an ordered `state.json.unit_ids` array. Be thorough but not exhaustive — large repos can have hundreds; cap at the top 100 by importance heuristic (route registration, "Main" pages, controllers with many actions).

## Output 2: update `migration.md` §2

Replace the contents of "## 2. Source stack" with detected values. Preserve the AUTO comment block at the top of the section. Use bullet format matching the template.

If the user has manually edited §2 (lines outside the `<!-- AUTO -->` markers contain non-template text), do NOT overwrite. Instead, print a diff to the user and ask: "I detected `<framework>` but you already wrote `<their value>` in §2. Should I overwrite, append a comment, or skip?"

## Output 3: update `state.json`

Update these fields (`uses_external_source`/`source_repo` were already written during the preflight's source-root resolution step, above — don't re-derive them here):

```json
{
  "status": "analyzed",
  "source_stack": {
    "primary": "<analysis.primary>",
    "confidence": <analysis.confidence>,
    "detected_at": "<ISO now>",
    "candidates": <analysis.candidates>,
    "user_provided": false
  },
  "updated_at": "<ISO now>"
}
```

If the user supplies their own source stack via the interview's free-text option (low-confidence path below), set `source_stack.user_provided = true` and overwrite `primary` with their value.

Do not modify any other top-level fields.

## Output 4: Interview phase — fill REQUIRED migration.md sections

After §2 is written and `state.json.source_stack` is updated, walk the user through filling the remaining REQUIRED migration.md sections (§3 target UI, §4 target API, §6 strategy, §7 auth, §12 testing). This replaces the previous "open migration.md by hand" step.

### Load the catalog

Read `${CLAUDE_PLUGIN_ROOT}/templates/migration-interview.json`. Each entry has:
- `id` — internal question id
- `section_anchor` — migration.md heading where the answer is written
- `field_label` — the bullet label inside that section
- `question` — text shown to the user
- `header` — short chip label (≤ 12 chars) for `AskUserQuestion`
- One of: `options` (list of framework IDs from `frameworks/<id>.md`), `options_inline` ([label, description] pairs), or `derive_from` + `derive_field` (pull the answer from a previously-answered question)
- Optional `recommend_by_source`, `recommend_by_loc` for picking the `(Recommended)` option
- Optional `default` for inline option lists

### Low-confidence / unknown-source handling

**First**, if `state.json.source_stack.primary == "unknown"` (or `confidence < 0.5`), surface the evidence the analyzer collected before the first question. Show the user:

```
We couldn't confidently identify your legacy stack. Here's what we found:

  <bullet list from analysis.json.evidence[]>

The framework files we know about today are:
  <bullet list of frameworks/*.md frontmatter display_names where role: source>
```

Then call `AskUserQuestion` for the source-stack question with options = (all `source` framework display names) + an explicit "**None of these — let me specify**" option (free text via the implicit "Other"). If the user picks "Other" and enters a value, set `state.json.source_stack.primary` to their value, set `source_stack.user_provided = true`, and continue with the interview. Downstream skills check `user_provided` and degrade gracefully — they skip framework-specific gotchas and lean on `permanent-gotchas` + WebSearch.

### Iterate the catalog

For each entry in `migration-interview.json` order:

1. **Skip-if-filled**: Read the relevant section of `migration.md` (locate the `section_anchor`, read the matching `field_label` bullet). If it already holds a non-placeholder value (i.e., NOT an HTML comment like `<!-- e.g. ... -->` and NOT empty), skip the question silently. This makes the interview idempotent on re-runs and respects manual edits.

2. **Render options**:
   - If the entry has `options` (framework IDs): for each id, Read `${CLAUDE_PLUGIN_ROOT}/frameworks/<id>.md` frontmatter `display_name` and use it as the option label. The option description can be a short summary from the file's first paragraph after the frontmatter (or the `## Recommendation context` first line, if present).
   - If the entry has `options_inline`: use each `[label, description]` pair directly.
   - If the entry has `derive_from`: pull the previously-answered question's framework file (e.g., `ui_test_framework` derives from `ui_framework`); Read that file's `## Test framework` section first line as the answer. Fall through to `options_inline_fallback` if the file doesn't declare one.

3. **Mark the recommendation**: look up the recommended option via `recommend_by_source[state.source_stack.primary]` or `recommend_by_loc[<loc-bucket>]`. Wildcard `"*"` is the fallback. Label that option `(Recommended)` and present it first.

4. **Ask** via `AskUserQuestion`. Single-select. The implicit "Other" lets the user provide free text. On the **first** question, also append an explicit "Skip the rest of the interview" option — picking it stops the interview cleanly; whatever's already filled stays, and `/web-modernize:plan`'s validation acts as the safety net.

5. **Write the answer immediately** via `Edit` against `migration.md` — locate the `field_label` bullet under `section_anchor` and replace its value. Do NOT batch; partial completion is recoverable.

6. **Validate** where the entry has `validate` (e.g., `integer 0-100`). Re-ask once if the user's value is invalid; on second invalid input, accept it verbatim and let `/plan`'s validation report it.

7. For source-stack-dependent recommendations on `target_auth`, also fold in the answer from the `current_auth` question (if the user picked "Keep current (bridge)", recommend the same provider).

### After the interview

Update `state.json.target_stack` with the answers (UI framework, API framework if not `none`):
```json
{
  "target_stack": {
    "ui": "<answer>",
    "api": "<answer or 'none'>"
  }
}
```

Update `state.json.strategy` and `state.json.testing` similarly from the answers (these mirror what `/plan` would otherwise write — pre-populating them here lets the user skip straight to `/scaffold` after a clean interview, while `/plan` re-reads `migration.md` as the source of truth).

## After writing

Print a one-screen summary. Two shapes depending on whether the interview completed cleanly:

**Happy path (all required fields filled by the interview):**

```
✓ Analyzed: <framework> (confidence <pct>%)
  Build tool: <tool>     LOC estimate: <n>
  Top libraries: <comma-separated top 3>
  Entry points found: <n> (will become migration units in /plan)
  <if analysis.styling present: "CSS: ~<rule_count_estimate> rules (<frameworks joined>) — <n> shared stylesheet(s) detected; /plan will offer to size them as a unit.">

✓ migration.md filled: <N of M required fields answered via interview>

  Warnings:
    <list any>

Next step:
  → Run /web-modernize:plan to generate the migration plan and seed units.

Want to tweak §10 acceptance criteria or §8 constraints? Edit migration.md by hand
— /plan re-reads the file on every run.
```

**Bail-out / partial fill (user picked "skip the rest" or some fields still unset):**

```
✓ Analyzed: <framework> (confidence <pct>%)
✓ migration.md §2 filled.

⚠ Interview partial — these REQUIRED sections still need values:
  - §3 Target UI framework
  - §6 Migration strategy
  - <etc.>

Either:
  → Edit migration.md by hand to fill the remaining sections, then run /web-modernize:plan.
  → Re-run /web-modernize:analyze — it skips sections that are already filled.
```

## State transition

- Pre: `state.status` == `initialized` (or `analyzed`, for re-runs)
- Post: `state.status` = `analyzed`
