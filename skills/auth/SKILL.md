---
description: "Migrate authentication as the first slice — wires up login/logout/session-refresh, seeds dev users, reads stack-specific auth notes from frameworks/<api>.md. Use when state.status is 'scaffolded'. Triggers: 'migrate auth', 'do auth first', 'set up login on the new side', 'wire up authentication', 'auth migration'."
disable-model-invocation: false
---

# `/web-modernize:auth`

You are the **auth** skill. Your job is to migrate authentication end-to-end so feature units can rely on a working identity layer.

## Preflight

1. Read `.claude/modernize/state.json`. Require `status == "scaffolded"`.
   - If earlier, redirect to the missing skill.
   - If later (`auth_done`, `in_progress`), tell the user auth has already been migrated and confirm before re-running.
2. Read `migration.md §7` — current and target auth provider, identity store, session model, claims/roles.
3. Read `migration.md §3` (target UI framework) and `§4` (target API framework — relevant if you need a backend auth handler).
4. Read `state.json.scaffold` to know target paths.

## Treat auth as a special unit

Create or update `.claude/modernize/units/__auth__.json` with the synthetic auth unit:

```json
{
  "id": "__auth__",
  "kind": "service",
  "source_paths": [ <discovered auth-related legacy files> ],
  "target_paths": [],
  "depends_on": [],
  "phase": 1,
  "effort": "M",
  "status": "in_progress",
  "history": [{ "at": "<now>", "by": "<user>", "from": "pending", "to": "in_progress", "session_id": "..." }],
  "in_flight": {
    "started_at": "<now>", "by": "<user>", "host": "<hostname>", "session_id": "...",
    "last_heartbeat": "<now>", "current_step": "discovering auth surface", "files_touched_so_far": []
  },
  "notes_path": ".claude/modernize/notes/__auth__.md",
  "retry_count": 0,
  "last_retry_prompt": null,
  "rollback_info": null
}
```

Also ensure `__auth__` is at the start of `state.json.unit_ids[]` (insert if missing). Save state.json after the insert.

## Discovery

Find every auth-relevant artifact in the legacy code:

| Pattern | Where to look |
|---------|---------------|
| Login endpoint / controller / page | search for `login`, `signin`, `authenticate` in file names + symbols |
| Session storage | session/cookie/JWT issuance code |
| Authorization checks | `[Authorize]` attributes (ASP.NET), `@Secured` (Spring), `requireAuth()` (custom) |
| User model | a class/entity holding user identity, often `User`, `Account`, `Identity` |
| Password hashing | `BCrypt`, `PBKDF2`, custom — flag for review if custom |
| OAuth/OIDC client config | client IDs, redirect URIs (sanitize in notes — do not commit secrets) |

Record each in `notes/__auth__.md` under "Source code map".

## Migration

Based on `migration.md §7 Target`, scaffold the target auth wiring.

### Common patterns

#### Target: same provider, modern client

E.g., legacy uses Azure AD with ADAL, target uses Azure AD with MSAL. Install MSAL into the target UI, wire `MsalProvider`/equivalent, set up redirect handling, expose a `useAuth` (or framework-equivalent) hook returning `{user, signIn, signOut, getAccessToken}`.

#### Target: JWT-based stateless auth

In target API: add a token issuance endpoint (`POST /auth/login`) + middleware that validates a Bearer header. Use a well-known library (e.g., `jsonwebtoken` for Node, `Microsoft.AspNetCore.Authentication.JwtBearer` for .NET).

In target UI: add an HTTP client wrapper that attaches `Authorization: Bearer ${token}` and refreshes on 401.

#### Target: cookie-based session

Target API issues a `Set-Cookie` with HttpOnly + Secure + SameSite=Lax. Target UI relies on `credentials: 'include'` (or framework-default).

#### Target: identity provider (Okta / Auth0 / etc.)

Install the IdP's SDK in the UI, configure callback route, document the IdP-side config the team needs to do (do not commit secrets).

### Password hashing — read the per-stack notes from the framework file

If the legacy app stored hashed passwords locally (not via an IdP), the target API must hash them too.

1. Try to Read `${CLAUDE_PLUGIN_ROOT}/frameworks/<state.target_stack.api>.md` and look for its `## Auth notes` section. That section names the per-stack default library (e.g., `bcrypt` for FastAPI with explicit 72-byte truncation, `BCryptPasswordEncoder` for Spring Boot, `PasswordHasher<TUser>` for .NET, `bcrypt` npm for NestJS / Express / Hono).
2. **Always also Read `agents/permanent-gotchas.md`** for cross-cutting rules — bcrypt 72-byte truncation, `passlib[bcrypt]` ban for Python, CSRF defaults, etc. These are load-bearing regardless of stack and override any contrary guidance from current framework docs.
3. **If the framework file does NOT exist** (unknown target API), do NOT block. Skip the prebuilt code template entirely; instruct the user (in the closing message) to consult `agents/permanent-gotchas.md` and OWASP password-storage guidance, then proceed with the rest of the auth migration. Record this in `units/__auth__.json.tests.notes`: `"auth template skipped — unsupported API stack <name>; user implemented per permanent-gotchas + OWASP."`

Document the chosen library (or the deferred-to-user note) in `notes/__auth__.md`. If the team wants arbitrary-length passwords (no 72-byte truncation), use SHA-256 pre-hash before `bcrypt.hashpw` and note that legacy bcrypt hashes won't verify on first login.

### Always do

- A **`useAuth`** hook (React) / **`useAuthStore`** (Vue) / **`AuthService`** (Angular) — single source of truth for "who is the user, am I authenticated."
- A **protected-route** primitive (e.g., `<RequireAuth>` wrapper, route guard, middleware).
- A **login page** at `/login` and **logout** action.
- A **token/session refresh** path so users aren't kicked out on minute one.
- A **role/claim mapping** if the legacy app uses roles — preserve the role names so authorization checks port cleanly later.

## Pre-seed dev users (local-password-store only)

If `migration.md §7` "Target" is a **local password store** (not an IdP like Okta / Auth0 / Azure AD), seed a small set of known dev users so the team can log in immediately without reverse-engineering the `/auth/register` payload shape. Skip this step entirely when the target is an external IdP — the IdP owns its own users.

### Pick the credentials

Use these three users by default. They satisfy the common password-policy minimums (mixed case + digit + symbol, ≥ 12 chars):

| Email | Password | Role |
|---|---|---|
| `admin@dev.local` | `Dev!Admin#2026` | admin |
| `user@dev.local` | `Dev!User#2026` | user |
| `readonly@dev.local` | `Dev!ReadOnly#2026` | readonly |

If the migrated auth doesn't have a roles concept, drop the `readonly` user and keep `admin` + `user` only. If the legacy app uses different role names, mirror them in the seeded users so authorization checks port cleanly later.

### Write the seed script

Pick the shape based on `state.target_stack.api`. The script must be **idempotent** (use `INSERT ... ON CONFLICT DO NOTHING` or `findOrCreate` — never overwrite an existing row, never duplicate). It must call the same `hash_password` / `BCryptPasswordEncoder` / `PasswordHasher<TUser>` the live `/auth/register` endpoint uses, so seeded users can log in immediately.

| Target API stack | Script path | Run command |
|---|---|---|
| `fastapi` | `apps/api-new/scripts/seed_dev_users.py` | `python scripts/seed_dev_users.py` |
| `spring-boot-3` | `apps/api-new/src/main/java/<base-package>/devseed/DevUserSeeder.java` (with `@Profile("dev")` + `CommandLineRunner`) | auto-runs on `./mvnw spring-boot:run` with `-Dspring-boot.run.profiles=dev` |
| `dotnet-minimal-api` | `apps/api-new/Scripts/SeedDevUsers.cs` (registered behind a `--seed` CLI flag in `Program.cs`) | `dotnet run -- --seed` |
| `nestjs` | `apps/api-new/scripts/seed-dev-users.ts` | `npx ts-node scripts/seed-dev-users.ts` |

The script reads `SEED_DEV_USERS=1` (or `--seed` on .NET) to gate execution — accidentally running it in prod is a security issue, so it must refuse to run when `NODE_ENV` / `ASPNETCORE_ENVIRONMENT` / `SPRING_PROFILES_ACTIVE` is `production`. Refuse loudly: print "REFUSING: seed script disabled in production" and exit non-zero.

### Check the users table exists first

The script's **first action**, before any INSERT, is to verify the target users table exists and is reachable. The team may have configured DB credentials but not yet run their migration tool — without this check, the seed fails cryptically and auth marks done anyway, leaving the team to debug a "table doesn't exist" error on their first login attempt instead of at seed time.

Per-stack shape:

| Stack | Pre-flight check | If missing → exit code, message |
|---|---|---|
| `fastapi` (SQLModel / SQLAlchemy) | wrap `SELECT 1 FROM users LIMIT 1` in `try / except OperationalError, ProgrammingError` | exit 2, print "USERS_TABLE_MISSING: run your DB migrations (e.g. `alembic upgrade head`) first, then re-run `python scripts/seed_dev_users.py`." |
| `spring-boot-3` | `JdbcTemplate.queryForObject("SELECT 1 FROM users LIMIT 1", Integer.class)` in try/catch | exit 2, print "USERS_TABLE_MISSING: run `./mvnw flyway:migrate` (or your migration tool) first, then re-run with `-Dspring-boot.run.profiles=dev`." |
| `dotnet-minimal-api` | `db.Database.CanConnect() && db.Users.Any()` (the latter catches table-existence cheaply); wrap in try/catch on `Microsoft.Data.SqlClient.SqlException` | exit 2, print "USERS_TABLE_MISSING: run `dotnet ef database update` first, then re-run with `--seed`." |
| `nestjs` (TypeORM) | `await dataSource.query("SELECT 1 FROM users LIMIT 1")` in try/catch | exit 2, print "USERS_TABLE_MISSING: run `npm run typeorm migration:run` (or your migration tool) first, then re-run `npx ts-node scripts/seed-dev-users.ts`." |

The exit code `2` (distinct from `1` for "real failure") signals to `/auth`'s caller that this is a pre-requisite issue, not a code bug. `/auth` reads the exit code and handles `2` specially below.

### Refuse to seed if real data exists

If the users-table check passes, the script next checks whether any user already exists with one of the dev emails. If any match: print `seed skipped: <email> already exists` and exit 0. This is the safety mechanism — never overwrite a real account that happens to have a `@dev.local` address.

### Run it once

Execute the seed script as part of `/auth`'s flow. Capture exit code + stdout/stderr.

Decision tree:

- **Exit 0** — seed succeeded (or no-op'd because users existed). Proceed to write `.dev-credentials.md` and include the credentials in the closing message.
- **Exit 2 (USERS_TABLE_MISSING)** — DB migrations haven't been run yet. Record on `units/__auth__.json`:
  ```json
  "tests": {
    "seed_skipped_reason": "users-table missing — run DB migrations first",
    "seed_rerun_command": "<the per-stack run command>"
  }
  ```
  Replace the credentials block in the auth-done closing message with the explicit "run DB migrations, then re-run with `<command>`" instructions. **Still** bump `state.status` to `auth_done` — the auth code itself is fine; only the convenience seed is deferred.
- **Any other non-zero exit** — record failure in `units/__auth__.json.tests.seed_failed_reason` with the stderr tail, advise the user to investigate, but again don't block auth finalize.

Seeding is convenience; auth migration itself succeeded the moment the migrated `/auth/login`, `/auth/register`, and middleware compiled and the test smoke passed.

### Write `.claude/modernize/dev-credentials.md`

After successful seeding, write this file (the `.claude/modernize/` directory is in `.gitignore`, so credentials don't leak):

```markdown
# Dev credentials (web-modernize seed)

⚠ DEV ONLY — these accounts exist only on local databases. Delete the seed
script (`<seed script path>`) and rotate / remove these users before any
non-local deploy. The seed script refuses to run when NODE_ENV /
ASPNETCORE_ENVIRONMENT / SPRING_PROFILES_ACTIVE is "production".

| Email | Password | Role |
|---|---|---|
| admin@dev.local | Dev!Admin#2026 | admin |
| user@dev.local | Dev!User#2026 | user |
| readonly@dev.local | Dev!ReadOnly#2026 | readonly |

Seeded by: /web-modernize:auth at <ISO timestamp>
Script: <path>
Re-run: <run command>
```

### Include the credentials in the auth-done message

The "✓ Auth migrated" closing block in the Finalize step prints the seeded credentials so the team sees them in the terminal without having to find `.dev-credentials.md`. See the updated print block in the Finalize section.

## Update notes/__auth__.md

Use `${CLAUDE_PLUGIN_ROOT}/templates/notes-template.md` as the structure. Fill in:
- **Design decisions**: which library, which session model, why (one paragraph).
- **Source code map**: legacy file → target file pairs.
- **Gotchas**: anything surprising (e.g., legacy stored roles in Session, target uses JWT claims — translation needed).
- **Verification** (left blank for `/web-modernize:verify` to fill).

## Verify before finishing

Run the relevant pieces of `verify.config.json` against the auth files:
- Lint passes.
- Typecheck passes.
- A smoke test exists at minimum (e.g., "renders login form").

If anything fails, write `.claude/modernize/units/__auth__.json` with `status = "failed"` and `failure.diagnostic` set; leave the in-flight branch in place; stop. Do not advance `state.status`.

## Commit suggestion

```
Suggested commit:
  git add apps/web-new/src/features/auth/ apps/api-new/src/auth/ .claude/modernize/notes/__auth__.md .claude/modernize/units/__auth__.json .claude/modernize/state.json
  git commit -m "auth: migrate authentication via web-modernize"
```

## Finalize

Update `.claude/modernize/units/__auth__.json`:
- Set `status = "migrated"`.
- Append history entry.
- Clear `in_flight = null`.

Update `.claude/modernize/state.json`:
- Set top-level `state.status = "auth_done"`.
- `updated_at = "<now>"`.

Print:

```
✓ Auth migrated.

  Provider: <target>
  Identity store: <where>
  Sessions: <model>
  Files written: <count> (see notes/__auth__.md)
  Unit file: .claude/modernize/units/__auth__.json
```

If the seed step ran successfully (local password store, not IdP, users-table present), append:

```
Seeded 3 dev users:
  admin@dev.local     / Dev!Admin#2026     (role: admin)
  user@dev.local      / Dev!User#2026      (role: user)
  readonly@dev.local  / Dev!ReadOnly#2026  (role: readonly)

⚠ DEV ONLY — credentials saved to .claude/modernize/dev-credentials.md
  (gitignored). Delete <seed-script-path> and rotate these users before
  any non-local deploy.

Try logging in:
  curl -X POST http://localhost:<api-port>/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@dev.local","password":"Dev!Admin#2026"}'
```

If the seed deferred because the users table doesn't exist yet (exit code 2 from the seed script), append this **instead** of the credentials block:

```
⚠ Dev-user seeding deferred — users table not present.

Auth code is migrated and tests pass; only the convenience seed didn't run.
After applying your DB migrations, finish seeding with:

  <per-stack seed run command, e.g. python scripts/seed_dev_users.py>

The seed script is idempotent and safe to re-run. Credentials will be
written to .claude/modernize/dev-credentials.md once it succeeds.
```

Always close with:

```
Next: /web-modernize:next  (begin migrating feature units one at a time)
```

## State transition

- Pre: `state.status` == `scaffolded`
- Post: `state.status` = `auth_done`; `units/__auth__.json.status` = `migrated`
