---
name: coldfusion
display_name: ColdFusion (CFM / CFC)
role: source
---

## Detection

Strong signals:

- `*.cfm` files (ColdFusion templates)
- `*.cfc` files (ColdFusion components)
- `Application.cfc` at app root

Weak signals:

- `<cfquery>`, `<cfoutput>`, `<cfinclude>`, `<cfset>` tags in markup
- `cfide/` administrative directory at web root

## Entry-point heuristic

Each top-level `.cfm` page is one entry point. `kind = "page"`. Include any `<cfinclude>`-referenced fragments plus relevant `.cfc` components in `files`.

## Recommended target

`react-vite-ts` (UI) + a new API stack. ColdFusion is on a long deprecation curve; teams should plan to leave the runtime entirely. Pair with `fastapi` or `spring-boot-3` for the API depending on team skills.
