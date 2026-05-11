---
description: >
  Migrates the application's authentication as a distinct first slice, because
  almost every feature unit depends on knowing who the user is. Reads the
  current and target auth providers from migration.md §7, wires up login/logout/
  session-refresh in the target stack, and records the design in
  notes/__auth__.md. Creates or updates the synthetic __auth__ unit file at
  .claude/modernize/units/__auth__.json. Runs after /web-modernize:scaffold
  and before any /web-modernize:next.
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

### Always do

- A **`useAuth`** hook (React) / **`useAuthStore`** (Vue) / **`AuthService`** (Angular) — single source of truth for "who is the user, am I authenticated."
- A **protected-route** primitive (e.g., `<RequireAuth>` wrapper, route guard, middleware).
- A **login page** at `/login` and **logout** action.
- A **token/session refresh** path so users aren't kicked out on minute one.
- A **role/claim mapping** if the legacy app uses roles — preserve the role names so authorization checks port cleanly later.

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

Next: /web-modernize:next  (begin migrating feature units one at a time)
```

## State transition

- Pre: `state.status` == `scaffolded`
- Post: `state.status` = `auth_done`; `units/__auth__.json.status` = `migrated`
