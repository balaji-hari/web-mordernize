---
name: dotnet-minimal-api
display_name: .NET Minimal API
role: target-api
---

## Scaffold

```sh
dotnet new webapi -o apps/api-new
```

Minimal API has been the project template default for a while now; older `--use-minimal-apis`-style flags from the pre-default era have since been removed. Resolve current CLI flags from `dotnet new webapi --help` if unsure; do not assume an older SDK's flags survive on a newer one.

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
```

Reuse an existing solution file if one already exists anywhere in the repo (`dotnet new webapi` does **not** create one as a side effect — check first, e.g. `find . -maxdepth 3 \( -name "*.sln" -o -name "*.slnx" \)` or platform-equivalent). This is the common case when migrating an existing .NET solution in place — a fresh `dotnet new sln` there collides with the repo's real solution file. Only create a new one if genuinely none exists:

```sh
dotnet new sln -n <project>   # only if no .sln/.slnx was found anywhere in the repo
dotnet sln add apps/<project>/<project>.csproj tests/<project>.Tests/<project>.Tests.csproj
```

Write `tests/<project>.Tests/HealthTests.cs` using `WebApplicationFactory<Program>` to assert `GET /health` returns 200. Coverage command: `dotnet test --collect:"XPlat Code Coverage"`.

Test smoke: `dotnet test --no-build`.

## Verify commands

**Working directory: the repo root** (where the `.sln`/`.slnx` lives, per `## Test framework` — all `dotnet` commands here operate on the solution, not a subdirectory). Unlike the Node UI stacks there is **no `--prefix`/cwd shuffle**, so these commands are *not* templated with a subsystem root; run them as-is from repo root.

Also unlike vitest, `dotnet test` has **no per-source-file scoping** — its `--filter` takes a test-name expression (e.g. `FullyQualifiedName~Foo`), never a file path. The plugin only knows a unit's `target_paths` (source files, not test names), so **do not substitute `${target_path}` into `--filter`** — run the whole API suite for API units and let `/verify` count results across it.

| Check | Command |
|---|---|
| lint | `dotnet format --verify-no-changes` |
| typecheck | `dotnet build` (the C# compiler is the type checker — there's no separate typecheck step) |
| test | `dotnet test` (whole solution; no per-file filter — see note above) |

## Auth notes

Use **`Microsoft.AspNetCore.Identity.PasswordHasher<TUser>`** (the framework default) or **`BCrypt.Net-Next`** for bcrypt-compatible hashing. Both are well-maintained and integrate cleanly with .NET Identity middleware.

Seed dev users via a `--seed` CLI flag wired into `Program.cs`, gated on `ASPNETCORE_ENVIRONMENT != "production"`. Run with `dotnet run -- --seed`.

Refer to `agents/permanent-gotchas.md` for cross-cutting auth rules (bcrypt 72-byte truncation, CSRF defaults, etc.).

## Data migration

Apply: `dotnet ef database update`
Status (read-only reachability probe): `dotnet ef migrations list` (connects to the configured database by default, which is what makes it useful as a reachability probe — not just a local metadata read)

## Dev server

| Dev port | Install/activate | Dev command | URL | Health check |
|---|---|---|---|---|
| 5000 | `dotnet restore` | `dotnet run` | http://localhost:5000 *(or as printed in launchSettings.json)* | `curl http://localhost:5000/health` |

## Recommendation context

Natural fit for teams already on the .NET stack who are modernizing off WebForms / classic ASP / older MVC. Pairs well with `next-app-router` or `react-vite-ts` on the UI side.
