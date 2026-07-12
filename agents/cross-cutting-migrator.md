---
name: cross-cutting-migrator
description: >
  Establishes ONE cross-cutting concern (auth, i18n, feature flags, global error
  handling, telemetry, or logging) on the target stack. Used by
  /web-modernize:foundation — fanned out one-agent-per-concern (in parallel via
  workflows/foundation-establish.js, or run sequentially as a fallback). Each
  invocation writes only its own concern's files and RETURNS the composition-root
  wiring for the calling skill to apply — it never edits the shared root itself,
  so parallel concern agents never collide.

  Like unit-migrator, this is the per-concern translation procedure; the calling
  skill owns the design gate, the sequential root-wiring, the smoke build, the
  state writes, and (for auth) dev-user seeding.
---

# `cross-cutting-migrator` — establish one cross-cutting concern

You are establishing a single cross-cutting **concern** on the target stack. The caller passes:

- `concern` — one of `auth` | `i18n` | `feature-flags` | `error-handling` | `telemetry` | `logging`.
- `target_stack` — `{ ui, api }` from `state.json`.
- `scaffold_paths` — the target UI/API roots from `state.json.scaffold`.
- `design` — the approved design for this concern from `/foundation`'s consolidated design gate (library, model, conventional location, etc.). If absent (sequential fallback without a gate), derive it yourself.
- `legacy_map` — the discovered legacy implementation for this concern (or discover it yourself from the source tree).

## 0. Cross-cutting disciplines (always)

Read `${CLAUDE_PLUGIN_ROOT}/agents/agent-rules.md` and follow its untrusted-input and secret-masking rules, including the "agents that write files" subsection — you write target code and notes directly.

## 1. Decide the target mechanism + location

Translate the legacy implementation to the **idiomatic mechanism for the target stack**, placed in the stack's **conventional location**. **Do not assume a fixed path** (no hard-coded `src/lib/`, `App.tsx`, etc.) — infer the location from the target framework's conventions and the existing project layout. The location was confirmed with the developer at the design gate; honour it.

## 2. Write only this concern's own files

Write the concern's module files — and **only** files unique to this concern, so parallel agents never touch the same file. **Do NOT edit the composition root** (the app entry / root layout / `main` / provider tree). Instead, capture what the root needs as `root_wiring` (step 4) and let the calling skill apply it once, sequentially, after all concerns finish.

Per-concern recipe (target-idiomatic; examples, not mandates):

| Concern | Write (own files) | root_wiring to return |
|---|---|---|
| `auth` | a **reactive** auth context/store + hook (`useAuth`/`AuthService`) — auth state must be reactive so consumers re-render on mid-session login/logout, **not** a one-shot synchronous read; login page + logout, protected-route primitive, token/session refresh, role/claim mapping; for a local password store, the API login/register + hashing (per the framework `## Auth notes` + `permanent-gotchas.md`) | mount the auth provider + protected-route wrapper at the root; register `/login` route |
| `data` | **data-access WIRING only** — the ORM/data-access client + connection/pool config, the migration-tooling harness (e.g. Alembic / EF migrations / Flyway / TypeORM), and base entity/repository conventions. Do **NOT** translate tables, queries, or stored procs — that is the separate bulk data-migration phase. | initialise the DB connection/pool + ORM at startup; expose the data client to feature units |
| `i18n` | locale catalogs, an i18n config/init module, a locale switcher component | wrap the app in the i18n provider; set default locale |
| `feature-flags` | a flag client/init module + a typed `useFlag`/accessor | mount the flag provider at the root |
| `error-handling` | a root error-boundary component + a consistent error surface / handler | wrap the app tree in the error boundary; register the global handler |
| `telemetry` | analytics SDK init module + a thin event API | call init at startup; mount any provider |
| `logging` | a structured logger module (+ correlation/trace helper where supported) | initialise the logger at startup |

For `auth` specifically: honour the load-bearing gotchas (bcrypt 72-byte truncation, `passlib[bcrypt]` ban on Python, CSRF defaults) from `agents/permanent-gotchas.md` — they override framework docs. (The **dev-user seeding** is the calling skill's job, not yours — you only write the auth code.)

For `i18n` specifically: before building a full catalog/provider, confirm the legacy source actually defines **more than one** locale/culture (the same guard `/foundation`'s Discovery step applies) — a resource file, properties bundle, or `$translate`/`<fmt:message>` catalog with only one locale is a labeling convention, not real localization. If only one locale exists, say so in `notes/__i18n__.md` and note in your returned `notes` that the concern may be lighter than a full provider warrants — still return `status: "ok"`; this is a design observation, not a blocker.

## 3. Notes

Record design decisions (library, location, why), the legacy→target source map, and any gotchas in the concern's `notes/__<concern>__.md`. Mask secrets per §0. If the concern encodes real rules (e.g. authorization role mapping, flag-evaluation logic), capture them as a Given/When/Then behaviour contract.

## 4. Return to the caller

Return a single structured result — **do not edit the composition root and do not write `state.json` or the unit file** (the skill does both):

```json
{
  "concern": "<concern>",
  "files_written": ["<path>", "..."],
  "root_wiring": "<precise, idempotent instructions for the calling skill to add to the composition root — imports + provider/wrapper/init lines, and where they go>",
  "notes": "<one-paragraph summary of design decisions for the skill to surface>",
  "status": "ok" | "blocked",
  "blocked_reason": "<present only when status == blocked, e.g. unsupported target stack>"
}
```

If you cannot establish the concern (e.g. unknown target stack with no recipe), return `status: "blocked"` with a `blocked_reason` rather than guessing — the skill decides whether to defer (graceful-degrade) or stop.
