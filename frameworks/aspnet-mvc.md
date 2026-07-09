---
name: aspnet-mvc
display_name: ASP.NET MVC (full framework)
role: source
---

## Detection

Strong signals:

- `Controllers/*.cs` directory present alongside `Views/**/*.cshtml` (or a sibling .NET source-language extension — see `legacy-analyzer.md`'s Language-variant siblings rule; views may be `.vbhtml` instead of `.cshtml`)
- `App_Start/RouteConfig.cs` present
- `*.csproj` referencing `System.Web.Mvc` (or `*.vbproj`)

Weak signals:

- `[HttpGet]`, `[HttpPost]`, `[Route]` attributes on controller actions
- `Views/Shared/_Layout.cshtml` master view

## Entry-point heuristic

Every controller class is one entry point. Unit `id` = controller class name (e.g., `OrderController`); `kind = "controller"`. Include the controller source file (`.cs` or a sibling .NET source-language extension, per the Language-variant siblings rule) and every view under `Views/<ControllerName>/`.

Importance: controllers registered in `RouteConfig.cs` first, then controllers referenced from navigation/master pages, then largest by LOC.

## Recommended target

`next-app-router` — the file-based routing model maps naturally from MVC's convention-over-configuration controllers. `react-vite-ts` if the team prefers a thinner UI shell with a separate API.
