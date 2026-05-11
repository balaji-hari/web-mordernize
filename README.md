# web-modernize

A Claude Code plugin that guides software teams through migrating legacy web applications — ASP.NET WebForms / MVC, Java JSP / Struts / Spring MVC, AngularJS 1.x, classic PHP, ColdFusion, jQuery-spaghetti, and similar — to a modern stack of the team's choosing. The plugin handles the workflow: analysis, plan generation, target scaffolding, auth migration, then unit-by-unit feature porting with verification. State is held in a git-tracked JSON ledger, so migrations span days and multiple developers without losing context.

> **Repo URL note**: this repo is named `web-mordernize` (typo). The plugin itself is correctly named **`web-modernize`** (no typo). The install commands below use both — the repo name for the marketplace, the plugin name for installation. We're keeping the repo name as-is to avoid breaking links in flight.

---

## Install

```sh
# 1. Add this repository as a marketplace (one-time, per developer machine):
/plugin marketplace add balaji-hari/web-mordernize

# 2. Install the plugin:
/plugin install web-modernize
```

After install, the plugin's commands appear under the `/web-modernize:` namespace. Type `/` in Claude Code and start typing `web-modernize` to discover them.

### Requirements

| Tool | Version | Why |
|------|---------|-----|
| Claude Code | latest | Plugin host |
| Node.js | ≥ 16 | The optional heartbeat hook (stale-session detection). Plugin still works without Node, just less precise about stalled migrations. |
| git | any modern version | All migration state is git-tracked |

The target stack you migrate **to** decides additional tooling (Node + npm for React/Vue/Svelte targets, .NET SDK for .NET targets, JDK for Spring Boot targets, etc.). The plugin uses your local toolchain; nothing is installed cloud-side.

---

## The five-step workflow

Once installed, every legacy repo follows the same shape:

```
1. /web-modernize:init       ← bootstrap scaffolding in this repo
2. (edit migration.md)       ← team fills target framework, strategy, auth, acceptance criteria
3. /web-modernize:analyze    ← detect source stack + entry points
4. /web-modernize:plan       ← generate plan.md and unit list
5. Loop:
     /web-modernize:scaffold    (once)
     /web-modernize:auth        (once)
     /web-modernize:next        (repeat, one unit at a time)
     /web-modernize:verify      (after each unit, or batch)
   Until /web-modernize:status reports "complete".
```

Concretely, after step 1 your repo will contain:

```
your-repo/
├── migration.md                        ← team-editable configuration
├── .claude/modernize/
│   ├── state.json                      ← progress ledger (git-tracked)
│   ├── plan.md                         ← generated migration plan (git-tracked)
│   ├── analysis.json                   ← source-stack analysis (git-tracked)
│   ├── verify.config.json              ← verification commands per target stack
│   └── notes/<unit-id>.md              ← per-unit design notes (git-tracked)
├── apps/web-new/                       ← target UI scaffold (created by /scaffold)
├── apps/api-new/                       ← target API scaffold (optional)
└── (existing legacy source untouched)
```

Commit the `.claude/modernize/` directory. That's how Alice on Monday and Bob on Wednesday see the same progress.

---

## Slash command reference

| Command | Purpose | When you run it |
|---------|---------|-----------------|
| `/web-modernize:init` | Bootstrap `migration.md` + `.claude/modernize/` | Once per legacy repo |
| `/web-modernize:analyze` | Detect source stack and entry points | After `/init`, before filling out the rest of `migration.md` |
| `/web-modernize:plan` | Validate `migration.md`, generate `plan.md`, seed unit list | After `migration.md` is complete |
| `/web-modernize:scaffold` | Create target project skeleton (UI, optional API, optional DB) | Once, after `/plan` |
| `/web-modernize:auth` | Migrate authentication as a distinct first slice | Once, after `/scaffold` |
| `/web-modernize:next` | Pick next pending unit and migrate it | In a loop until migration is complete |
| `/web-modernize:migrate <id>` | Migrate a specifically named unit | When you need to jump to a unit out of order (debug, retry) |
| `/web-modernize:verify [id]` | Lint + typecheck + test a migrated unit, record evidence | After each `/next`, or in batch |
| `/web-modernize:status` | Print progress dashboard | Anytime — read-only |
| `/web-modernize:abandon` | Two-step rollback (`--soft`, `--hard`, `--unit <id>`) | When you need to reset state or drop a unit |

---

## Editing `migration.md`

`/web-modernize:init` writes a template with 11 sections. Sections marked **REQUIRED** must be filled in before `/web-modernize:plan` will run.

| Section | Required? | Notes |
|---------|-----------|-------|
| 1. Project identity | recommended | Just metadata — name, team, ticket |
| 2. Source stack | AUTO | Filled by `/analyze`; override if it got something wrong |
| 3. Target UI framework | **yes** | Pick from react-vite-ts, next-app-router, vue3-vite, angular-17, svelte-kit, or custom |
| 4. Target API framework | optional | Set to `none` for UI-only migrations — plan skips API work entirely |
| 5. Database | optional | `unchanged` is the most common; set if replatforming |
| 6. Migration strategy | **yes** | strangler-fig (default), big-bang (small apps), module-by-module |
| 7. Auth provider | **yes** | Current and target; drives `/web-modernize:auth` |
| 8. Constraints | recommended | Must-keep URLs, compliance, deployment target |
| 9. Out of scope | optional | Explicit "don't migrate this" list |
| 10. Acceptance criteria | **yes** | At least 3 items; drives `/verify`'s pass/fail bar |
| 11. Risks & open questions | free-form | Plugin reads but doesn't validate |

You can re-edit and re-run `/web-modernize:plan` at any time — the plan and unit list will regenerate. Note that existing units' progress (`status`, `history`, `notes_path`) is preserved across re-plans by unit `id`; if you rename a unit in the plan, you'll lose its history.

---

## Multi-developer workflow

The plugin assumes git is the source of truth. There is no central server; collaboration happens by committing and pulling.

### The contract

| Artifact | Git tracked? | Why |
|----------|--------------|-----|
| `migration.md` | yes | Shared configuration |
| `.claude/modernize/state.json` | yes | Shared progress ledger |
| `.claude/modernize/plan.md` | yes | Reviewable migration plan |
| `.claude/modernize/notes/` | yes | Per-unit design records |
| `.claude/modernize/verify.config.json` | yes | Team's verification commands |
| `CLAUDE.local.md` | **no** (gitignored) | Your personal scratch space |
| `.claude/settings.local.json` | **no** (gitignored) | Personal Claude Code settings |

### Concurrent work

If Alice runs `/web-modernize:next` on Monday and Bob runs `/web-modernize:next` on Wednesday, both will:
1. Re-read `state.json` (so Bob sees what Alice did)
2. Pick the next eligible pending unit based on `depends_on`
3. Record their work in `state.json.history[]` with their email

If Alice and Bob are working **simultaneously** on different machines:
- Both will pick what looks like the next unit. They may pick the same one if Alice hasn't pushed yet.
- The plugin sets `state.json.units[i].in_flight` when work starts. The optional heartbeat hook keeps `last_heartbeat` fresh.
- `/web-modernize:status` shows in-flight units, including who and where.
- When the second person pushes, git produces a merge conflict on `state.json`. **This is intentional** — git is your source of truth for "who got there first." Resolve the conflict in favor of the most-advanced status (`verified > migrated > in_progress > pending`).

### Advisory locks

`/plan` and `/scaffold` write a top-level `lock` block to `state.json` while they run, with a 10-minute TTL. If another developer runs the same skill while a lock is held, they'll see a warning naming the holder. This is advisory only — git is still the real arbiter.

### Recommended cadence

- Commit `.claude/modernize/state.json` and `notes/` after every successful unit migration. Small commits make conflicts trivial.
- Use a branch per unit if your team's policy allows: the `/next` skill creates `modernize/<unit-id>` branches automatically when git is clean.
- Run `/web-modernize:status` before starting work — it shows what's in-flight elsewhere.

---

## Resuming after interruption

Claude Code's `claude --continue` restores your last conversation, including which skill was active.

Every skill in this plugin re-reads `state.json` on entry, so it picks up where it left off:

- If a unit is `in_progress` with a fresh `last_heartbeat`, the active skill will resume from `current_step`.
- If `last_heartbeat` is more than 15 minutes old, `/web-modernize:status` flags it as "possibly stalled" and `/next` offers three options: reclaim, skip, or abort.
- If a migration crashed mid-write, the feature branch `modernize/<unit-id>` is left in place for human inspection.

You don't need to remember "what was I doing?" — running `/web-modernize:status` always tells you.

---

## Troubleshooting

### `/web-modernize:plan` refuses to run

It's protecting you from a half-empty `migration.md`. The error message will list every missing field by section number. Open `migration.md`, fix those, re-run.

### `/web-modernize:analyze` says my framework is `unknown`

Your codebase didn't match any of the built-in heuristics with high confidence. Three options:
1. Edit `migration.md §2` manually with your best guess and re-run `/web-modernize:plan` — the plan will be skeleton-only but at least the workflow proceeds.
2. Look at `.claude/modernize/analysis.json` — `candidates[]` shows the analyzer's three best guesses. Pick one and override §2.
3. File an issue with a redacted sample so we can add detection support.

### A unit migration failed

The unit's status will be `failed` with `failure.diagnostic` populated. The plugin creates a `modernize/<unit-id>` branch when it starts work; that branch contains whatever it managed to write before stopping. Three options:
1. Inspect the branch, fix the underlying issue, then `/web-modernize:migrate <unit-id>` to retry.
2. Decide the unit is out of scope: `/web-modernize:abandon --unit <unit-id>`.
3. Mark it for human migration: edit `state.json` directly to set status `blocked` with a `failure.diagnostic` explaining why.

### I want to start over

`/web-modernize:abandon --hard` is the nuclear option. It is two-step (run once, confirm, run again to actually delete). It removes:
- `.claude/modernize/` (state, plan, analysis, notes)
- Target scaffold directories (`apps/web-new/`, etc.)

It does NOT touch `migration.md` (so you can re-run `/web-modernize:init` and pick up your configuration) and does NOT touch git history.

If you want to keep your design notes for postmortem, use `/web-modernize:abandon --soft` instead.

### Two developers' `state.json` conflict on merge

Standard git merge conflict. Rules of thumb:
- For each conflicting unit, keep the entry with the most-advanced `status` (`verified > migrated > in_progress > pending`).
- For `history[]`, concatenate both branches' entries and sort by `at` timestamp.
- For top-level `status`, keep the higher in this order: `complete > in_progress > auth_done > scaffolded > planned > analyzed > initialized > uninitialized`.
- After resolving, commit and run `/web-modernize:status` to verify.

### The heartbeat hook isn't firing

Check `node --version` resolves to ≥ 16. Without Node, the hook silently no-ops and stale-detection just relies on whatever heartbeat the active skill writes directly. The migration still works; you just lose the "minute-by-minute liveness" signal.

---

## FAQ

**Q: Does this plugin work on UI-only legacy apps (no backend)?**
A: Yes — first-class case. In `migration.md`, set §4 Target API framework to `none` and §5 Database to `unchanged`. The plan, scaffold, and unit list will skip API/DB work entirely.

**Q: Can I edit `plan.md` directly?**
A: You can, but `/web-modernize:plan` will overwrite it on next run. Better to edit `migration.md` (the source) and regenerate. If you need a per-unit override (e.g., move one unit to a different phase), edit `state.json` directly — the plugin honors manual edits.

**Q: What if my target framework isn't in the dropdown for §3?**
A: Pick `custom` and tell `/web-modernize:scaffold` you'll scaffold manually. After scaffolding by hand, mark `state.scaffold.ui.status = "done"` and continue.

**Q: My team uses GitLab / Bitbucket, not GitHub. Does this still work?**
A: Yes for the plugin itself — git host doesn't matter. The marketplace install is via GitHub today; teams behind GHE / GitLab need to clone this repo internally and use `/plugin marketplace add` with the local clone path.

**Q: Can I run multiple migrations in the same repo?**
A: Not concurrently — `state.json` is a single document. If you need to migrate two distinct legacy apps living in the same repo, treat each as a separate working directory (different `migration.md`, different `.claude/modernize/`).

**Q: How do I add a new framework to detection?**
A: Edit `agents/legacy-analyzer.md` — add a row to the framework-recognition table with signals. PR welcome.

**Q: Can I commit `.claude/modernize/notes/` selectively (e.g., keep some private)?**
A: They're git-tracked by default. If a unit's notes contain something sensitive (credentials, internal links), redact in the notes file or use `.gitignore` to exclude that specific file. The plugin never reads anything from notes — only writes — so excluding from git is safe.

---

## Contributing

Issues and PRs welcome at [github.com/balaji-hari/web-mordernize](https://github.com/balaji-hari/web-mordernize).

### Versioning policy

The plugin uses explicit semver. The `version` field in `.claude-plugin/plugin.json` is the source of truth; teams pull updates only when this is bumped. Bump:
- **Patch** (0.1.0 → 0.1.1) — bug fix, doc change, hook script tweak
- **Minor** (0.1.x → 0.2.0) — new skill, new framework support, additive schema change
- **Major** (0.x.x → 1.0.0) — `state.schema.json` breaking change, removed/renamed skill, changed slash-command name

`state.schema.json` is versioned independently via the `schema_version` integer. The plugin's `/init` (and any future `/migrate-schema`) handles migrations forward.

---

## License

MIT. See [LICENSE](LICENSE).
