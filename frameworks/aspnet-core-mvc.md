---
name: aspnet-core-mvc
display_name: ASP.NET Core MVC
role: source
---

## Detection

Strong signals:

- `Program.cs` calling `AddControllersWithViews` or `AddRazorPages` (or a sibling .NET source-language extension — see `legacy-analyzer.md`'s Language-variant siblings rule)
- `*.csproj` with `Microsoft.NET.Sdk.Web` SDK reference (or `*.vbproj`)
- `Startup.cs` (older Core 3.x layout) configuring MVC (or its sibling-language equivalent)

Weak signals:

- Razor `*.cshtml` pages under `Pages/` or `Views/`
- `appsettings.json` + `appsettings.Development.json`

## Entry-point heuristic

Every controller class is one entry point. Unit `id` = controller class name; `kind = "controller"`. Include the controller source file (`.cs` or a sibling .NET source-language extension, per the Language-variant siblings rule) and views under `Views/<ControllerName>/` or Razor pages under `Pages/<ControllerName>/`.

## Recommended target

`next-app-router` — the team is already used to .NET conventions and Next's App Router has a similar mental model. `react-vite-ts` if a thinner UI is preferred.
