---
description: >
  Inspects the legacy source tree, detects the primary framework and version,
  builds a file inventory and rough dependency graph, and fills section 2 of
  migration.md (source stack). Writes .claude/modernize/analysis.json with the
  full detection payload. Run after /web-modernize:init and after the user has
  partially filled migration.md (sections 3-7 may still be empty at this point).
disable-model-invocation: false
---

# `/web-modernize:analyze`

You are the **analyze** skill. Your job is to detect what the team is migrating *from* and record what you find.

## Preflight

1. Read `.claude/modernize/state.json`. Required.
   - If `status != "initialized"` and `status != "analyzed"` (re-run), explain to the user that analyze runs after `/web-modernize:init` and stop.
2. Read `migration.md`. Required.
3. Confirm the source tree is non-empty (something other than just `.git/`, `.claude/`, `migration.md`).

## Detection strategy

Delegate the heavy lifting to the `legacy-analyzer` subagent (defined at `${CLAUDE_PLUGIN_ROOT}/agents/legacy-analyzer.md`). Invoke it with a prompt like:

> Analyze the legacy web application in the current working directory. Report: primary framework + version + confidence; build tool / package manager; top 5 libraries; approximate LOC; entry points (pages/controllers/components); rough dependency graph (which files import which). Format the report as JSON matching the schema in {{TEMPLATE_PATH}}. Skip `.git/`, `node_modules/`, `bin/`, `obj/`, `dist/`, `build/`, `.claude/`.

Run the subagent, then validate the JSON it returns. If invalid, fix obvious errors and ask the subagent to retry once.

## Frameworks to recognize

Detection signals (non-exhaustive — add more in legacy-analyzer.md):

| Framework key | Signals |
|---------------|---------|
| `aspnet-webforms` | `*.aspx`, `*.aspx.cs`, `*.ascx`, `Web.config`, `Global.asax`, `System.Web.UI` |
| `aspnet-mvc` | `Controllers/`, `*.cshtml`, `App_Start/RouteConfig.cs`, `System.Web.Mvc` |
| `aspnet-core-mvc` | `Program.cs` with `AddControllersWithViews`, `*.cshtml`, `Startup.cs` |
| `java-jsp` | `*.jsp`, `web.xml`, `WEB-INF/`, `pom.xml` or `build.gradle` |
| `java-struts` | `struts-config.xml`, `*.action`, JSP + Struts taglibs |
| `java-spring-mvc` | `@Controller` annotations, `applicationContext.xml`, `pom.xml` with `spring-webmvc` |
| `angularjs-1` | `angular.module(...)` in JS, `ng-*` directives in HTML, `package.json` with `angular@1.x` |
| `jquery-spaghetti` | jQuery usage but no framework module pattern |
| `php-classic` | `*.php` files with mixed HTML, no Laravel/Symfony markers |
| `coldfusion` | `*.cfm`, `*.cfc`, `Application.cfc` |
| `unknown` | confidence < 0.5 → write `candidates[]` with the top 3 guesses |

## Output 1: `.claude/modernize/analysis.json`

Write a complete payload. Schema:

```json
{
  "analyzed_at": "<ISO timestamp>",
  "primary": "<framework key>",
  "confidence": 0.0,
  "candidates": [{ "name": "...", "confidence": 0.0 }],
  "detected_version": "<string or null>",
  "build_tool": "<msbuild|maven|gradle|npm|yarn|none|...>",
  "package_manager": "<nuget|npm|yarn|maven|...>",
  "loc_estimate": 0,
  "top_libraries": [{ "name": "...", "version": "...", "purpose": "..." }],
  "entry_points": [
    { "id": "LoginController", "kind": "controller", "files": ["..."] }
  ],
  "dependency_graph_summary": "<one-paragraph description>",
  "warnings": ["<any caveats, e.g., 'mixed asp.net mvc and webforms'>"]
}
```

`entry_points[]` is the seed list that `/web-modernize:plan` will turn into `state.json.units[]`. Be thorough but not exhaustive — large repos can have hundreds; cap at the top 100 by importance heuristic (route registration, "Main" pages, controllers with many actions).

## Output 2: update `migration.md` §2

Replace the contents of "## 2. Source stack" with detected values. Preserve the AUTO comment block at the top of the section. Use bullet format matching the template.

If the user has manually edited §2 (lines outside the `<!-- AUTO -->` markers contain non-template text), do NOT overwrite. Instead, print a diff to the user and ask: "I detected `<framework>` but you already wrote `<their value>` in §2. Should I overwrite, append a comment, or skip?"

## Output 3: update `state.json`

Update these fields:

```json
{
  "status": "analyzed",
  "source_stack": {
    "primary": "<analysis.primary>",
    "confidence": <analysis.confidence>,
    "detected_at": "<ISO now>",
    "candidates": <analysis.candidates>
  },
  "updated_at": "<ISO now>"
}
```

Do not modify any other top-level fields.

## After writing

Print a one-screen summary:

```
✓ Analyzed: <framework> (confidence <pct>%)
  Build tool: <tool>     LOC estimate: <n>
  Top libraries: <comma-separated top 3>
  Entry points found: <n> (will become migration units in /plan)

  Warnings:
    <list any>

  migration.md §2 has been updated. Review it, then:
  → Fill in sections 3 (target UI), 6 (strategy), 7 (auth), 10 (acceptance) in migration.md.
  → Then run /web-modernize:plan.
```

## Low-confidence path

If `analysis.confidence < 0.5`:

- Still write `state.json.source_stack.primary = "unknown"` and the candidates list.
- Add a prominent warning to the user output: "Could not confidently detect framework. `/web-modernize:plan` will produce a skeleton plan with TODOs rather than a fully generated unit list. Consider editing `migration.md §2` manually before continuing."

## State transition

- Pre: `state.status` == `initialized` (or `analyzed`, for re-runs)
- Post: `state.status` = `analyzed`
