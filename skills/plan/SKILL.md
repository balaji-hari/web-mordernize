---
description: >
  Validates that migration.md has all required fields filled in, then generates
  .claude/modernize/plan.md (human-readable migration plan), seeds one file per
  unit under .claude/modernize/units/<id>.json from analysis.json, and records
  the ordered id list in state.json.unit_ids. Refuses to run if migration.md
  is incomplete; produces a numbered list of missing fields with section anchors.
  This is the gate between "exploration" and "execution".
disable-model-invocation: false
---

# `/web-modernize:plan`

You are the **plan** skill. Your job is to convert the team's intent (in `migration.md`) plus the detected source stack (in `analysis.json`) into an executable, ordered migration plan with one file per unit.

## Plugin-version skew check

Read `state.json.plugin_version` (treat absent/null as "old/unknown"). Read the running plugin's version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. Parse both as `MAJOR.MINOR.PATCH`. If `state.plugin_version`'s major **or** minor differs from the running version (patch differences are fine), print **before** anything else and **continue** (warn, do not refuse):

```
⚠ Plugin version skew detected.
   State written by: <state.plugin_version or "unknown">
   Running version:  <running.version>
   Teammates on different plugin versions writing to the same state can
   produce shape mismatches. Recommended: have everyone run
   /plugin uninstall web-modernize && /plugin install web-modernize, then continue.
```

Refusing would block the team until the slowest updater catches up — that's a worse failure mode than a warned-but-continued run. On successful exit (right before the "✓ done" message), set `state.plugin_version = "<running version>"` so the warning self-resolves after one synchronized run.

## Preflight — validate migration.md

Read `migration.md` and `analysis.json`. Then check the following REQUIRED fields are filled in (not blank, not the template placeholder `<!-- fill in -->`):

| Required field | Section | Allowed values |
|----------------|---------|----------------|
| Target UI framework | §3, "Framework" line | one of: react-vite-ts, next-app-router, vue3-vite, angular, svelte-kit, or custom |
| Target UI language | §3, "Language" line | TypeScript or JavaScript |
| Migration strategy | §6, "Strategy" line | strangler-fig, big-bang, module-by-module |
| Current auth provider | §7 | any non-empty value |
| Target auth provider | §7 | any non-empty value |
| Acceptance criteria | §10 | at least 3 unchecked checkbox items |
| UI test framework | §12, "UI test framework" line | one of: vitest, jest, karma-jasmine, or `other: <name>` |
| API test framework | §12, "API test framework" line | one of: pytest, xunit, junit5, jest, nunit, mstest, `other: <name>`, or `n/a` (only if §4 Framework is `none` or `reuse-existing`) |
| Target coverage % | §12, "Target coverage %" line | integer 0–100 |

If **any** required field is missing or still has the template placeholder, **STOP**. Do not write `plan.md`, do not touch state, do not write any per-unit files. Print a numbered failure report:

```
✗ Cannot generate plan — migration.md is incomplete.

Missing required fields:
  1. §3 "Framework" — not filled in (currently blank or template placeholder).
  2. §6 "Strategy" — invalid value: <what they wrote>. Use one of: strangler-fig, big-bang, module-by-module.
  3. §10 — only 1 acceptance criterion. Add at least 2 more.

Open migration.md, fix these, then re-run /web-modernize:plan.
```

Be specific about which line is wrong. Do not summarize; list every issue.

## Acquire advisory lock

Before writing, set `state.json.lock`:

```json
{
  "holder": "<git config user.email or 'unknown'>",
  "session_id": "<current Claude session id if you can determine it, else timestamp>",
  "expires_at": "<ISO now + 10 minutes>"
}
```

If a non-expired lock already exists held by **someone other than the current user**, warn:

```
WARNING: <lock.holder> started planning <N> minutes ago and the lock has not yet expired.
  Running /plan now risks conflicting changes when you both commit.
  Override anyway? (yes/no)
```

Wait for confirmation.

## Generate plan.md

Read `${CLAUDE_PLUGIN_ROOT}/templates/plan.md` and substitute placeholders. Key transformations:

### Phase assignment

Based on `migration.md §6 Strategy`:

- **strangler-fig**: Phase 1 = scaffold + auth. Phase 2 = read-only / low-risk units (typically dashboards, listing pages). Phase 3 = form-heavy / write-path units. Phase 4 = admin / batch / reporting. Phase N = cutover.
- **big-bang**: Phase 1 = scaffold + auth. Phase 2 = ALL remaining units in parallel-ready order. Phase 3 = cutover. (Mark this strategy as "small-app only" in the plan summary.)
- **module-by-module**: Phase 1 = scaffold + auth. Phase 2-N = one phase per top-level module/area discovered in analysis.json.

### Unit seeding (with history preservation on re-runs)

The first time `/plan` runs, `.claude/modernize/units/` is empty (apart from `.gitkeep`) and this section just creates new per-unit files. On subsequent runs (when `state.status` is already `planned` or beyond), preserve the progress made on units that survive the regeneration.

#### Step 1 — Read the rename map from migration.md

Look for an optional `## 9b. Unit rename map` section in migration.md. Parse each bulleted line of the form:

```
- old_id → new_id
- AnotherOldId → AnotherNewId
```

Build a dict `rename = { old_id: new_id, ... }`. Empty if the section is absent. Reverse-lookup is built on the fly. Splits, merges, and "removed" markers are NOT supported in this version — perform those by hand-editing the affected per-unit files.

#### Step 2 — Build the candidate list from analysis.json

For each entry in `analysis.json.entry_points[]`, build a candidate unit (in-memory object):

```json
{
  "id": "<entry_point.id>",
  "kind": "<entry_point.kind>",
  "source_paths": <entry_point.files>,
  "target_paths": [],
  "depends_on": ["__auth__"],
  "phase": <assigned phase>,
  "effort": "<S|M|L|XL>",
  "status": "pending",
  "history": [],
  "in_flight": null,
  "notes_path": ".claude/modernize/notes/<id>.md",
  "retry_count": 0,
  "last_retry_prompt": null,
  "rollback_info": null
}
```

Heuristics for `effort`:
- Single file, <200 LOC → S
- 1-3 files, 200-800 LOC → M
- 3-10 files OR >800 LOC OR touches data layer → L
- Anything involving complex stateful UI (wizards, designers, real-time) → XL

#### Step 3 — Discover existing per-unit files

List every file matching `.claude/modernize/units/*.json` (excluding `.gitkeep`). Read each into memory. This is the set of `existing_units` keyed by `unit.id` (which must match the file's basename).

#### Step 4 — Merge each candidate with the existing per-unit file

For each candidate `U_new`:

1. Look up the matching old unit. Resolution order:
   - If any entry in `rename` maps to `U_new.id` (reverse lookup): the predecessor's id is the key. Use that to look up `existing_units[<old_id>]`.
   - Else: look for `existing_units[U_new.id]`.
2. If a match exists:
   - Copy these fields from the existing unit (preserve progress): `status`, `history`, `in_flight`, `notes_path`, `target_paths`, `verification`, `failure`, `retry_count`, `last_retry_prompt`, `rollback_info`.
   - Append a history entry: `{ from: <status>, to: <status>, reason: "carried forward by /web-modernize:plan re-run", at: <now>, by: <user> }`. If renamed, the reason should be `"renamed from <old_id> by /plan"`.
   - Take these from `U_new` (refreshed by re-analyze): `source_paths`, `kind`, `depends_on`, `phase`, `effort`.
   - Use `U_new.id` (the new id wins).
   - Update `notes_path` to match the new id. If a notes file at the old path exists, rename it on disk (`git mv .claude/modernize/notes/<old_id>.md .claude/modernize/notes/<new_id>.md`).
   - If renamed, delete the old per-unit file (`git rm .claude/modernize/units/<old_id>.json`) after writing the new one — otherwise both will sit on disk.
3. If no match: use `U_new` verbatim as a brand-new unit.

#### Step 5 — Handle dropped units (existing files not in regenerated candidates)

For each entry in `existing_units` whose id (after applying the rename map) is not in the regenerated candidate list:

- If its `status == "pending"` and no rename was declared: silently delete the per-unit file (`git rm .claude/modernize/units/<id>.json`). The plan no longer wants it.
- If its `status` is anything else (`in_progress`, `migrated`, `verified`, `blocked`, `skipped`, `failed`): **keep the per-unit file** and print a warning:
  ```
  WARNING: existing unit `<id>` (status: <status>) is not in the regenerated plan.
    Possible causes:
      - The analyzer didn't re-detect it (source files moved or deleted).
      - The unit was renamed but migration.md §9b is missing the mapping.
      - The unit is genuinely out of scope now (declare it in §9 and re-run).
    Action taken: kept .claude/modernize/units/<id>.json as-is so progress is not lost.
    Add `<id> → <new_id>` to §9b Unit rename map, OR add `<id>` to §9 Out of scope, then re-run /web-modernize:plan.
  ```

Collect all warnings and print them as a block after the success banner — do not stop the plan generation.

#### Step 6 — Dependency repair after renames

For every unit's `depends_on[]`, if any entry references an old id that was renamed, replace it with the new id. If an entry references an id that no longer exists at all (and is not `__auth__`), drop it and warn:

```
WARNING: unit `<unit.id>` depended on `<missing_id>` which no longer exists in the plan.
  Pruned from depends_on. If this was a rename, declare it in §9b and re-run.
```

### `depends_on` graph

- All non-auth units depend on `__auth__`.
- If the analyzer's dependency_graph shows unit A imports symbols from unit B, add B to A's `depends_on`.
- Cut cycles by breaking on the larger unit (the assumption: the larger one will probably need refactoring during migration anyway).

### Open questions

Compose 3-5 open questions for the team based on:
- Items the analyzer flagged as warnings.
- Ambiguous mappings (e.g., legacy `MasterPage` → ???).
- Items in `migration.md §11 Risks & open questions` that look unresolved.

### Out of scope

Mirror `migration.md §9` list verbatim into the plan's "Out of scope" section.

## Write outputs

1. **`.claude/modernize/plan.md`** — fully rendered template. Overwrite any existing one (warn the user first if it exists and has been edited since last generation — detect by comparing the `Generated <timestamp>` header).

2. **`.claude/modernize/units/<id>.json`** — one file per merged unit. Each file contains the full unit object (the shape defined in `templates/unit.schema.json`). Use 2-space indent + trailing newline for git-friendly diffs.

3. **`.claude/modernize/state.json`** — update:

```json
{
  "status": "<see rule below>",
  "target_stack": {
    "ui": "<from §3>",
    "api": "<from §4 or 'none'>",
    "db": "<from §5 or 'unchanged'>"
  },
  "testing": {
    "ui_framework": "<from §12, e.g. vitest>",
    "api_framework": "<from §12, e.g. pytest, or 'n/a'>",
    "target_pct": <from §12, integer>
  },
  "strategy": "<from §6>",
  "scaffold": "<see rule below>",
  "unit_ids": [ <ordered list of unit ids, including any kept-but-warned units from Step 5> ],
  "out_of_scope": [ <from §9> ],
  "lock": null,
  "updated_at": "<ISO now>"
}
```

The `testing` block is the single source of truth for which runner `/scaffold` installs and which coverage bar the unit-migrator and `/verify` measure against. Re-plans overwrite this block from §12 — if a team needs to switch runners mid-migration they edit §12 and re-run `/plan`. (Note that switching runners mid-migration does not retroactively re-translate already-migrated units' tests; new units pick up the new framework.)

**`status` rule** — preserve forward progress on re-runs:
- If the current `state.status` is `analyzed`: set to `planned`.
- If the current `state.status` is `planned`, `scaffolded`, `auth_done`, `in_progress`, or `complete`: leave as-is. A re-plan never rewinds the workflow.

**`scaffold` rule** — only initialize if currently `null`:
- If `state.scaffold` is `null` (first plan run): seed `{ ui: {status: "pending"}, api: {status: "pending|skipped"}, db: {status: "pending|skipped"} }`.
- If `state.scaffold` is non-null (re-plan after scaffold ran): leave it alone. The scaffold has already been generated; changing its status here would lie about what's on disk.

**`unit_ids` ordering** — must match the canonical plan order: sort by `(phase asc, list_index asc)` where `list_index` reflects the analyzer's discovery order. Re-plans preserve relative order for kept units and append any new ones at their natural phase position.

Release the lock by setting `lock: null`.

## After writing

Print:

```
✓ Plan generated.

  Strategy: <strategy>
  Phases: <count>
  Total units: <count>   (S:<n> M:<n> L:<n> XL:<n>)
  API units: <count or "skipped (target API = none)">
  DB work: <skipped|migration|replatform>

  Per-unit files: .claude/modernize/units/*.json  (<count> files)

Review .claude/modernize/plan.md. If the unit list looks wrong, edit migration.md and re-run /web-modernize:plan.

Next: /web-modernize:scaffold
```

## Low-confidence path

If `state.source_stack.confidence < 0.5`:

- Generate `plan.md` with a header banner: "**WARNING — Skeleton plan: source framework was not confidently detected. Treat unit list as a starting suggestion only.**"
- Mark every unit with `effort: "L"` (conservative).
- Add a prominent open question: "Confirm or correct the unit list before running /web-modernize:scaffold."

## State transition

- Pre: `state.status` == `analyzed` (or anything later, for re-runs)
- Post: `state.status` = `planned` (or unchanged if already further)
