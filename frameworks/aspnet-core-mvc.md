---
name: aspnet-core-mvc
display_name: ASP.NET Core MVC
role: source
---

## Detection

Strong signals:

- `Program.cs` calling `AddControllersWithViews` or `AddRazorPages`
- `*.csproj` with `Microsoft.NET.Sdk.Web` SDK reference
- `Startup.cs` (older Core 3.x layout) configuring MVC

Weak signals:

- Razor `*.cshtml` pages under `Pages/` or `Views/`
- `appsettings.json` + `appsettings.Development.json`

## Entry-point heuristic

Every controller class is one entry point. Unit `id` = controller class name; `kind = "controller"`. Include the controller `.cs` and views under `Views/<ControllerName>/` or Razor pages under `Pages/<ControllerName>/`.

## Recommended target

`next-app-router` — the team is already used to .NET conventions and Next's App Router has a similar mental model. `react-vite-ts` if a thinner UI is preferred.
