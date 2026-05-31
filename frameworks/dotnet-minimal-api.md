---
name: dotnet-minimal-api
display_name: .NET Minimal API (.NET 8+)
role: target-api
---

## Scaffold

```sh
dotnet new webapi -o apps/api-new
```

Minimal API has been the default since .NET 8; `--use-minimal-apis` was removed in .NET 9. Resolve current CLI flags from `dotnet new webapi --help` if unsure; do not assume any pre-.NET-8 flags survive.

Then edit `apps/api-new/Program.cs` to add:

- `builder.Services.AddCors(...)` + `app.UseCors(...)` with the dev allow-list (`http://localhost:5173`, `http://localhost:3000`, `http://localhost:4200`).
- `app.MapGet("/health", () => Results.Ok(new { status = "UP" }));`
- `public partial class Program { }` at the bottom — required for `WebApplicationFactory<Program>` in the test project (top-level statements declare `Program` as `internal` otherwise).

## Test framework

`xunit` (default; `nunit` / `mstest` are alternates). Run all commands from repo root. Substitute the real project name for `<project>` (e.g., `api-new`):

```sh
dotnet new xunit -o tests/<project>.Tests
dotnet add tests/<project>.Tests reference apps/<project>/<project>.csproj
dotnet add tests/<project>.Tests package coverlet.collector
dotnet add tests/<project>.Tests package Microsoft.AspNetCore.Mvc.Testing
dotnet new sln -n <project>
dotnet sln add apps/<project>/<project>.csproj tests/<project>.Tests/<project>.Tests.csproj
```

Write `tests/<project>.Tests/HealthTests.cs` using `WebApplicationFactory<Program>` to assert `GET /health` returns 200. Coverage command: `dotnet test --collect:"XPlat Code Coverage"`.

Test smoke: `dotnet test --no-build`.

## Auth notes

Use **`Microsoft.AspNetCore.Identity.PasswordHasher<TUser>`** (the framework default) or **`BCrypt.Net-Next`** for bcrypt-compatible hashing. Both are well-maintained and integrate cleanly with .NET Identity middleware.

Seed dev users via a `--seed` CLI flag wired into `Program.cs`, gated on `ASPNETCORE_ENVIRONMENT != "production"`. Run with `dotnet run -- --seed`.

Refer to `agents/permanent-gotchas.md` for cross-cutting auth rules (bcrypt 72-byte truncation, CSRF defaults, etc.).

## Dev server

| Dev port | Install/activate | Dev command | URL | Health check |
|---|---|---|---|---|
| 5000 | `dotnet restore` | `dotnet run` | http://localhost:5000 *(or as printed in launchSettings.json)* | `curl http://localhost:5000/health` |

## Recommendation context

Natural fit for teams already on the .NET stack who are modernizing off WebForms / classic ASP / older MVC. Pairs well with `next-app-router` or `react-vite-ts` on the UI side.
