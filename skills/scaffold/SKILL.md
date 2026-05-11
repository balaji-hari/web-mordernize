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

1. Parse `$ARGUMENTS`:
   - Empty → run the full scaffold (UI + API + DB + assets).
   - `--assets-only` → run **only** the "Copy legacy assets" step below. Skip the framework scaffolder, API, DB, and `verify.config.json` updates. Use case: a team mid-migration whose `/scaffold` ran before v0.3.1 (no asset copy) and needs to backfill missing images, fonts, favicon. Requires `state.status >= "scaffolded"` — see the precondition below.

2. Read `state.json`. Mode-dependent precondition:
   - **Full scaffold** (no flag): require `status == "planned"` (or `"scaffolded"` for re-runs of incomplete scaffolds). Otherwise redirect:
     - If `status` is earlier (`uninitialized`, `initialized`, `analyzed`): print "Run /web-modernize:<missing-skill> first." and stop.
     - If `status` is later (`auth_done`, `in_progress`, `complete`): tell user scaffolding is already done. To re-scaffold, they must `/web-modernize:abandon` first.
   - **`--assets-only`**: require `status >= "scaffolded"` (`scaffolded`, `auth_done`, `in_progress`, or `complete`). If earlier, redirect: "Asset backfill needs a target scaffold to copy into. Run /web-modernize:scaffold (without --assets-only) first."

3. Read `migration.md` §3 (UI), §4 (API), §5 (DB), §8 (constraints — esp. deployment target). For `--assets-only`, you only need §3 (specifically the optional "Asset directories" field, if present).

4. Read `.claude/modernize/plan.md` (for context, not strictly required).

5. Decide target directories. Default convention (use unless §8 says otherwise):
   - UI: `apps/web-new/`
   - API: `apps/api-new/`
   - DB: `db/migrations/`

6. If any of these directories already exist and are non-empty (full scaffold only), ask the user before touching them.

If `--assets-only`, skip directly to "Copy legacy assets" below; do not run the per-subsystem checklist or update `verify.config.json`.

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

## Copy legacy assets

Migrated pages will reference images, fonts, and favicons from the legacy app. Without this step those references 404. Run this **after** the UI scaffold (so `<scaffold.ui.path>/public/` exists) but before declaring the scaffold complete.

This step also runs as the only action when `--assets-only` is passed.

### 1. Determine the source list

If `migration.md §3` contains a non-empty **"Asset directories"** field (one path per bullet), treat that list as authoritative — use exactly the declared paths and skip the heuristic scan below. Print a one-line note: `Using migration.md §3 asset declarations: <list>`.

Otherwise, scan the working directory for these patterns (case-insensitive). Match directories first, then top-level files:

- `Pics/`, `pics/`
- `images/`, `Images/`, `img/`
- `Content/` and any sub-directories under it (ASP.NET MVC convention) — typically `Content/images/`, `Content/Pics/`, `Content/fonts/`, `Content/css/`
- `wwwroot/` and any sub-directories (ASP.NET Core static files) — typically `wwwroot/images/`, `wwwroot/css/`, `wwwroot/lib/`, `wwwroot/fonts/`
- `assets/`, `assets/img/`, `assets/images/`, `assets/fonts/`
- `fonts/`, `font/`
- `static/` (Django, Jekyll, Hugo)
- `public/` (some older Express / Node legacy apps — careful not to confuse with the target's `public/`)
- `src/main/webapp/resources/` (Java)
- Top-level files: `favicon.ico`, `favicon.png`, `apple-touch-icon.png`, `robots.txt`, `sitemap.xml`

Skip these directories entirely (they are output / dependency / plugin-managed): `.git/`, `node_modules/`, `bin/`, `obj/`, `dist/`, `build/`, `out/`, `target/`, `.next/`, `.svelte-kit/`, `__pycache__/`, `.venv/`, `vendor/`, `.claude/`, `packages/`, `.idea/`, `.vscode/`, and the existing target scaffold directories (`apps/web-new/`, `apps/api-new/`, `db/`).

### 2. Copy each discovered directory or file into the target's `public/`

Use the target UI's `public/` directory (typically `<scaffold.ui.path>/public/` — Vite, Next.js, Astro, SvelteKit, etc.). For Angular, use `<scaffold.ui.path>/src/assets/` instead — Angular's static asset convention differs.

Preserve sub-structure under the destination:

- `<legacy>/Pics/` → `<scaffold.ui.path>/public/Pics/`
- `<legacy>/wwwroot/images/` → `<scaffold.ui.path>/public/images/`
- `<legacy>/Content/images/` → `<scaffold.ui.path>/public/images/`
- `<legacy>/fonts/` → `<scaffold.ui.path>/public/fonts/`
- `<legacy>/favicon.ico` → `<scaffold.ui.path>/public/favicon.ico`

Use `cp -r` (or platform-equivalent) — do **not** move or delete the source. The legacy tree is still the source-of-truth for units that haven't migrated yet.

### 3. Idempotency

If a destination file already exists in `public/`, **skip it** and add a one-line "(exists, skipped: `<path>`)" to the summary. Do not overwrite — the team may have manually adjusted assets after a previous scaffold run.

If a destination directory exists but contains different files than the source, copy only the missing ones; don't synchronize deletions.

### 4. Detect absolute-URL references in the legacy CSS

Grep the legacy CSS/SCSS/LESS files (use the same set this skill found in step 1 of the scan) for `url('/...')` patterns — absolute URLs starting with `/`. If any are found, print a warning naming the affected stylesheet(s) and lines:

```
WARNING: legacy CSS uses absolute URLs that may not resolve under the target framework:
  Content/site.css:42:   url('/Content/Pics/promo.png')
  Content/site.css:118:  url('/fonts/icons.woff2')

After this asset copy, the files exist at <scaffold.ui.path>/public/Content/Pics/promo.png
and <scaffold.ui.path>/public/fonts/icons.woff2.

Confirm your target framework serves /public/ at the URL root:
  - Next.js: respect `basePath` in next.config.js
  - Vite: confirm `base: '/'` in vite.config.ts
  - Angular: assets live at /assets/, NOT /public/ — see below

If the target uses a different base path, the migration agent (/next, /migrate)
will need to rewrite these references when porting each affected unit. The
agent reads this warning from the unit's notes file when planning translations.
```

Also append the warning verbatim to `.claude/modernize/notes/__scaffold__.md` (create the file if missing) so the migration agent can read it later.

### 5. Print a summary

```
✓ Copied legacy assets to <scaffold.ui.path>/public/:
  - Pics/ (47 files, 12.3 MB)
  - Content/images/ (18 files, 2.1 MB)
  - fonts/ (3 files, 240 KB)
  - favicon.ico

  Skipped (already exists in target):
  - public/robots.txt

  Absolute URL references in legacy CSS: 2 (see notes/__scaffold__.md)
```

If no assets were discovered (no matching directories, no `migration.md §3` declarations, no top-level favicon), print:

```
(no legacy asset directories detected — nothing to copy)
```

and continue. This is normal for some legacy stacks (e.g., a pure API).

## Update verify.config.json

Now that target paths exist, update `.claude/modernize/verify.config.json`:
- Replace `${ui_root}` defaults with the actual UI path (e.g., `apps/web-new`).
- Replace `${api_root}` with actual API path or `null` if skipped.
- Keep the user's manual edits if they edited the file already — diff and ask.

## Commit suggestion

After a full scaffold, suggest (but do not execute) a commit:

```
Suggested commit:
  git add apps/ .claude/modernize/ db/ verify.config.json
  git commit -m "scaffold: target project skeleton via web-modernize"
```

For `--assets-only`, suggest a narrower commit:

```
Suggested commit:
  git add apps/<ui-path>/public/ .claude/modernize/notes/__scaffold__.md
  git commit -m "scaffold: backfill legacy assets via web-modernize"
```

## After writing

For a **full scaffold**, print:

```
✓ Scaffold complete.

  UI:  <ui.status> at <ui.path>
  API: <api.status> at <api.path or "(skipped)">
  DB:  <db.status>
  Assets: <count of directories copied>, <count of files skipped> (see notes/__scaffold__.md if any warnings)

Verification config updated. Edit .claude/modernize/verify.config.json if your scripts differ.

Next: /web-modernize:auth   (migrates the auth provider before any feature units)
```

For **`--assets-only`**, print:

```
✓ Asset backfill complete.

  Copied: <count of files> across <count of directories>
  Skipped: <count> (already present)
  CSS absolute-URL warnings: <count> (see notes/__scaffold__.md)

Top-level state.status unchanged (<state.status>). Re-run /web-modernize:verify on any
recently-migrated unit to confirm asset references now resolve.
```

## State transition

- **Full scaffold**:
  - Pre: `state.status` == `planned` (or `scaffolded` for a re-run of an incomplete scaffold).
  - Post: `state.status` = `scaffolded` (only when all non-skipped subsystems are `done`).
- **`--assets-only`**:
  - Pre: `state.status >= "scaffolded"` (any phase from `scaffolded` onward).
  - Post: top-level `state.status` unchanged. Only `state.updated_at` is bumped. No per-subsystem scaffold block is touched.
