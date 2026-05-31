---
name: vbscript-asp-classic
display_name: Classic ASP (VBScript)
role: source
---

## Detection

Strong signals:

- `*.asp` files (NOT `.aspx` — that's WebForms)
- VBScript inside `<% ... %>` tags
- `global.asa` at app root

Weak signals:

- `Server.CreateObject(...)` calls
- `Response.Write`, `Request.QueryString` patterns
- IIS hosting

## Entry-point heuristic

Each top-level `.asp` page is one entry point. `kind = "page"`. Include any `<!--#include file="..." -->` fragments in `files`.

## Recommended target

`react-vite-ts` (UI) + a new API. Classic ASP has been EOL since the early 2000s — the migration is overdue. Pair the API with `dotnet-minimal-api` if the team wants to stay on the .NET stack, otherwise `fastapi` or `nestjs` are good neutral choices.
