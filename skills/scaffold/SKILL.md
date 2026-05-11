---
description: >
  Creates the target project skeleton (UI, optional API, optional DB migrations
  directory) per the target stack in migration.md. Each subsystem is tracked
  independently in state.json.scaffold so partial completion is safe to resume.
  Does NOT migrate any features — just lays down the empty modern project so
  /web-modernize:auth and /web-modernize:next have somewhere to write to.
disable-model-invocation: false
---

# `/web-modernize:scaffold`

You are the **scaffold** skill. Your job is to bring up the modern project's skeleton — directory layout, package files, base configuration — without porting any feature code.

## Preflight

1. Read `state.json`. Require `status == "planned"` (or `"scaffolded"` for re-runs of incomplete scaffolds). Otherwise redirect:
   - If `status` is earlier (`uninitialized`, `initialized`, `analyzed`): print "Run /web-modernize:<missing-skill> first." and stop.
   - If `status` is later (`auth_done`, `in_progress`, `complete`): tell user scaffolding is already done. To re-scaffold, they must `/web-modernize:abandon` first.
2. Read `migration.md` §3 (UI), §4 (API), §5 (DB), §8 (constraints — esp. deployment target).
3. Read `.claude/modernize/plan.md` (for context, not strictly required).
4. Decide target directories. Default convention (use unless §8 says otherwise):
   - UI: `apps/web-new/`
   - API: `apps/api-new/`
   - DB: `db/migrations/`
5. If any of these directories already exist and are non-empty, ask the user before touching them.

## Per-subsystem checklist

Process each subsystem in order: UI → API → DB. For each, set `state.json.scaffold.<subsystem>` to `{"status": "in_progress", "path": "...", "started_at": "..."}` before starting, then to `{"status": "done", ...}` when complete. This makes resume-after-interruption straightforward.

### UI scaffold

Based on `migration.md §3 Framework`:

#### `react-vite-ts`

1. Confirm Node ≥ 18 is available (`node --version`). If not, ask user how to proceed.
2. Run: `npm create vite@latest apps/web-new -- --template react-ts` (or whatever directory was decided).
3. `cd apps/web-new && npm install`.
4. Add libraries based on §3 "State management" and "Styling":
   - State: `redux-toolkit + react-redux` | `zustand` | (none)
   - Styling: `tailwindcss postcss autoprefixer` + run `npx tailwindcss init -p` | `@mui/material @emotion/react @emotion/styled` | (none)
5. Add scripts to `apps/web-new/package.json` (or confirm they exist): `dev`, `build`, `lint`, `typecheck`, `test`.
6. Add a minimal `apps/web-new/src/App.tsx` placeholder reading `Legacy app migration in progress — managed by web-modernize plugin`.

#### `next-app-router`

`npx create-next-app@latest apps/web-new --typescript --tailwind --eslint --app --no-src-dir` (adjust flags per §3 styling answer).

#### `vue3-vite`

`npm create vite@latest apps/web-new -- --template vue-ts`, install Vue Router and Pinia if §3 state management says so.

#### `angular-17`

`npx @angular/cli@17 new apps/web-new --routing --style=<scss|css> --strict --skip-git`.

#### `svelte-kit`

`npm create svelte@latest apps/web-new`, prompt non-interactively for skeleton project + TS.

#### Custom / other

Tell the user the plugin doesn't have a recipe for this framework. Ask them to scaffold manually, then confirm completion so the plugin can record `scaffold.ui.status = "done"` and move on.

### API scaffold

Only run if `state.target_stack.api != "none"` AND `!= "reuse-existing"`. Otherwise set `scaffold.api = {"status": "skipped", "reason": "target API = <value>"}` and move to DB.

Based on `target_stack.api`:

- `dotnet-minimal-api`: `dotnet new webapi --use-minimal-apis -o apps/api-new`
- `spring-boot-3`: use start.spring.io API (see legacy-analyzer or instruct user; offer to provide curl command)
- `nestjs`: `npm i -g @nestjs/cli` then `nest new apps/api-new` (use the `--package-manager npm --skip-git --skip-install` flags then `npm install` afterward to keep state.json consistent)
- `fastapi`: create `apps/api-new/` with `pyproject.toml` + `app/main.py` skeleton

Add a `/health` endpoint that returns `200 OK` so deployment smoke tests work immediately.

### DB scaffold

Only run if `state.target_stack.db != "unchanged"`. Otherwise mark skipped.

- `schema-migrate-to-<X>`: create `db/migrations/` with a placeholder migration `0001_init.sql` and a README explaining the migration tool the team chose.
- `replatform-to-<Y>`: create `db/` with a `README.md` describing the source → target plan; defer actual migration scripts to a later phase.

## Update verify.config.json

Now that target paths exist, update `.claude/modernize/verify.config.json`:
- Replace `${ui_root}` defaults with the actual UI path (e.g., `apps/web-new`).
- Replace `${api_root}` with actual API path or `null` if skipped.
- Keep the user's manual edits if they edited the file already — diff and ask.

## Commit suggestion

After scaffolding, suggest (but do not execute) a commit:

```
Suggested commit:
  git add apps/ .claude/modernize/ db/ verify.config.json
  git commit -m "scaffold: target project skeleton via web-modernize"
```

## After writing

Print:

```
✓ Scaffold complete.

  UI:  <ui.status> at <ui.path>
  API: <api.status> at <api.path or "(skipped)">
  DB:  <db.status>

Verification config updated. Edit .claude/modernize/verify.config.json if your scripts differ.

Next: /web-modernize:auth   (migrates the auth provider before any feature units)
```

## State transition

- Pre: `state.status` == `planned`
- Post: `state.status` = `scaffolded` (only when all non-skipped subsystems are `done`)
