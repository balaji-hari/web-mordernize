---
name: aspnet-webforms
display_name: ASP.NET WebForms
role: source
---

## Detection

Strong signals (any single match ≥ 0.85 confidence):

- `*.aspx` files present
- `*.aspx.cs` code-behind files present (or a sibling .NET source-language extension — see `legacy-analyzer.md`'s Language-variant siblings rule)
- `*.ascx` user-control files present
- `Global.asax` at repo root or app root
- `Web.config` containing `<system.web>` section

Weak signals (boost confidence when combined with one strong signal):

- `<asp:` server-control tags in markup files
- `App_Code/`, `App_GlobalResources/`, `App_LocalResources/` directories

## Entry-point heuristic

Every `*.aspx` page is one entry point. Unit `id` = file name without extension; `kind = "page"`. Include both the markup file and its code-behind (e.g. `<name>.aspx.cs`; resolve to whichever .NET source-language extension is actually present per the Language-variant siblings rule) in `files`.

Importance ranking: pages registered in `Web.config <routes>` or in master-page nav menus first, then largest files by LOC.

## Recommended target

`react-vite-ts` is the safest default (broad ecosystem, low friction for teams new to JS frontends). `next-app-router` is a good fit if the legacy app has heavy SEO requirements or many static pages.
