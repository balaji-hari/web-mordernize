---
description: "Assemble the migrated units into a composed app — central router + nav, whole-app smoke, orphaned-unit detection, and (for strangler-fig) the traffic-splitting proxy. Idempotent reconciliation: run it at ANY stage to integrate what's migrated so far, or as the final cutover. Use when state.status is 'foundation_done', 'in_progress', or 'complete'. Triggers: 'integrate', 'assemble the app', 'wire up routing', 'build the router/nav', 'cutover', 'compose the app', 'whole-app smoke', 'strangler routing'."
disable-model-invocation: false
---

# `/web-modernize:integrate [--dry-run] [--final]`

You are the **integrate** skill. You assemble the units migrated *so far* into a coherent composed app: a central router + nav, a whole-app smoke, an orphaned-unit report, and — for strangler-fig — the traffic-splitting layer. You are an **idempotent reconciliation**: each run rebuilds the composition from the **current** set of migrated/verified units, so you are safe to run after the 3rd unit, the 30th, or as the final cutover. Re-running after rollbacks or new migrations just reconciles.

## Plugin-version skew check

Same as other skills: read `state.json.plugin_version`, compare MAJOR.MINOR against `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`; warn-and-continue on mismatch.

## Preflight

1. Parse `$ARGUMENTS`:
   - `--dry-run` → compute and print the report, but **write nothing** (no files, no state).
   - `--final` → strict end-cutover mode (see step 6).
2. Read `.claude/modernize/state.json`. Require `status ∈ {foundation_done, in_progress, complete}`. If earlier, redirect: "Nothing to integrate yet — migrate the foundation and at least one unit first (run /web-modernize:foundation, then /web-modernize:next)."
3. Read `migration.md` (for `§3` target UI + `§6` strategy) and `.claude/modernize/plan.md` for context.
4. Read `state.target_stack`, `state.strategy`, and `state.scaffold` (target paths).

## Collect the migrated set + their routes

Iterate `state.unit_ids[]`, read each `units/<id>.json`. Take the units with `status ∈ {migrated, verified}` (skip foundation synthetic units except where they expose routes, e.g. `__auth__`'s `/login`). For each, determine its **routes**:

- If `unit.routes[]` is present, use it (path, label, kind).
- **Fallback** (older units migrated before `routes[]` existed): infer routes by scanning the unit's `target_paths` + `notes/<id>.md` — page route declarations (React Router `<Route>`, Next.js file-routes, Angular route config, SvelteKit `+page`), and API route decorators (`@router.get/post`, `@Get/@Post`, `@GetMapping`, `app.MapGet`). Record what you inferred in the report so the user can confirm.

Read `notes/__layout__.md` (the composition root the first unit established) so you assemble into the existing layout, not a new one.

## Read the per-stack integration recipe

Try to Read `${CLAUDE_PLUGIN_ROOT}/frameworks/<state.target_stack.ui>.md` and locate its `## Integration` section (central router config location, nav assembly pattern, and — for strangler-fig — the proxy config recipe). For an API-only or unknown stack with no `## Integration` section, **do not block**: infer the idiomatic central-router location from the project layout and note that you did so. **Do not hard-code paths** — confirm the router/nav location with the user if it's ambiguous.

## Assemble (skip all writes under `--dry-run`)

1. **Central router** — reconcile the router file from the collected routes. **Reconcile, don't append**: routes whose unit is no longer `migrated`/`verified` (rolled back, reset) are removed; new ones added. Write the router file once.
2. **Nav / menu** — assemble nav entries from UI routes that carry a `label` (preserve legacy nav order/grouping when `notes/__layout__.md` records it). Write once.
3. **Strangler layer** — **only when `state.strategy == "strangler-fig"`**: generate/refresh a route table / reverse-proxy config (e.g. the framework recipe's proxy) mapping **migrated** routes → the new app and **everything else → legacy**. As more units migrate, more routes flip; this is the incremental cutover. Skip entirely for `big-bang` / `module-by-module`.
4. Record the assembly (router path, nav path, strangler path, decisions) in `.claude/modernize/notes/__integration__.md`.

The router/nav/proxy files are **shared** — they're now owned by the integration step, so `/web-modernize:rollback` will treat them as shared files (its safety check refuses to revert them out from under dependents without `--force-shared`).

## Whole-app smoke

Build + boot the composed app (UI: `npm run build && npm run typecheck` from `state.scaffold.ui.path`; API: boot + `/health` per the same recipe `unit-migrator` Part B §B7a uses). Then:
- Hit a **sample of migrated routes** (UI: confirm they render inside the layout; API: 2xx on a representative request).
- Assert the **nav renders** and there are **no broken imports** and **no dangling links** to not-yet-migrated pages (a nav entry pointing at a route with no migrated unit is a finding).

On smoke failure: print the failure, write nothing further, and stop — do not record a `complete` integration.

## Orphan + coverage report

Compute and print (and append to `notes/__integration__.md`):
- **Routed units** — migrated units now reachable in the composed app.
- **Orphaned units** — `migrated`/`verified` units with **no route / unreachable from nav** (flag for the team — likely a missing route registration or a dead unit).
- **Still on legacy** — in-scope routes not yet migrated (for strangler-fig, these are the proxy's legacy fallbacks).
- **Cutover coverage %** — migrated in-scope routes ÷ total in-scope routes.

## `--final` (end cutover)

When `--final` is set, tighten the smoke: **every in-scope route must resolve to the new app** — any remaining legacy fallback (orphan, unmigrated route, or strangler rule still pointing at legacy) is a hard failure with the list of offenders. Use this as the last step once `/web-modernize:verify` has driven everything to `verified` / `state.status == complete`.

## Write state (skip under `--dry-run`)

Update `.claude/modernize/state.json` — set the additive `integration` object:
```json
"integration": {
  "status": "<partial | complete>",
  "assembled_at": "<now>",
  "router_path": "<path>",
  "nav_path": "<path>",
  "strangler_config_path": "<path, only for strangler-fig>",
  "orphaned_units": [ <ids> ],
  "coverage_pct": <int>
}
```
`status = "complete"` only when there are no orphans and (under `--final`) no legacy fallbacks; otherwise `"partial"`. **Do not change top-level `state.status`** — integration is a reconciliation, not a phase transition. Bump `updated_at`.

## After writing

```
✓ Integrated <N> migrated unit(s).
  Router: <router_path>   Nav: <nav_path>
  <strangler: <path>  (migrated → new app, rest → legacy)   |  (no strangler — strategy is <strategy>)>
  Whole-app smoke: <passed | FAILED: …>
  Coverage: <pct>% of in-scope routes on the new app
  Orphaned units: <none | list>   Still on legacy: <count> route(s)
  Report: .claude/modernize/notes/__integration__.md

Suggested next steps:
  1. Resolve any orphaned units (add their routes, or mark out of scope).
  2. Re-run /web-modernize:integrate after the next batch of migrations (it reconciles).
  3. When everything is verified, run /web-modernize:integrate --final for the cutover.
```

## State transitions

- Pre: `state.status ∈ {foundation_done, in_progress, complete}`.
- Post: top-level `state.status` **unchanged**; `state.integration` written (unless `--dry-run`). Re-runnable any number of times.
