---
description: "Show progress, in-flight units, blockers, and the recommended next command. Read-only. Use any time. Triggers: 'where are we', 'show status', 'progress', 'how's the migration going', 'what's the state', 'dashboard', 'migration status'."
disable-model-invocation: false
---

# `/web-modernize:status`

You are the **status** skill. You are **read-only**. Do not modify any files.

## What to read

1. `.claude/modernize/state.json` — required. If it does not exist, tell the user "No web-modernize state found. Run `/web-modernize:init` to start." and stop.
2. Every `.claude/modernize/units/*.json` in the order given by `state.unit_ids[]`. If `unit_ids` is empty, skip the unit-related sections.
3. `.claude/modernize/plan.md` — optional. If it exists, you can reference phase names.
4. The current ISO-8601 UTC time.

## What to print

Format the output as a dashboard with these sections, in this order. Use plain ASCII tables; no emojis (per project conventions).

### 1. Header

```
web-modernize status — <PROJECT_NAME from migration.md §1, or repo dir name>
state.json: <relative path>     schema_version: <n>     plugin_version: <v>
workflow phase: <state.status>     updated_at: <state.updated_at> (<relative time>)
unit files: .claude/modernize/units/  (<count of unit_ids> tracked)
```

### 2. Stack

```
source: <source_stack.primary> (confidence <source_stack.confidence>)
target: ui=<target_stack.ui>   api=<target_stack.api>   db=<target_stack.db>
strategy: <strategy>
```

If `source_stack` is null, print `source: not analyzed yet — run /web-modernize:analyze`.
If `target_stack` is null, print `target: not planned yet — run /web-modernize:plan`.

### 3. Scaffold

```
scaffold:  ui=<ui.status> @ <ui.path>     api=<api.status> @ <api.path>     db=<db.status>
```

If `scaffold` is null, print `scaffold: not run yet — run /web-modernize:scaffold`.

### 4. Unit counts

Aggregate across every `units/*.json` you read. Count by status:

```
units:  <total> total   <pending> pending   <in_progress> in-flight   <migrated> migrated   <verified> verified   <blocked> blocked   <skipped> skipped   <failed> failed
```

### 5. In flight

For every unit with `status: "in_progress"`, print a block:

```
  in flight: <unit.id>
    started: <in_flight.started_at> (<relative time>)
    by:      <in_flight.by> on <in_flight.host>
    step:    <in_flight.current_step>
    last heartbeat: <in_flight.last_heartbeat> (<relative time>)
    files touched: <count> (<first 3>...)
```

**Stale detection**: if `last_heartbeat` is more than 15 minutes ago, append on a new line `    WARNING: POSSIBLY STALLED — heartbeat is <N> min old. /web-modernize:next will offer to take over.`

### 6. Next up

If `state.status` is `auth_done` or `in_progress` and there are pending units, determine the next unit `/web-modernize:next` would pick by iterating `state.unit_ids` in order and reading each `units/<id>.json`:

- Filter to those with `status: "pending"` AND all `depends_on` ids satisfied (other units with status `migrated`/`verified`, plus `__auth__` if `state.status >= auth_done`).
- Take the first.

Print:

```
next up: <unit.id> (kind=<kind>, phase=<phase>, effort=<effort>)
  depends on: <comma-separated, all satisfied>
  source:  <source_paths joined>
  target:  <target_paths joined or "(to be determined)">
```

If no pending units have all dependencies satisfied, print:

```
next up: nothing immediately runnable.
  blocked units waiting on: <list of unsatisfied dependency ids>
```

If `state.status` is earlier than `auth_done`, print instead:

```
next up: not in migration phase yet. Run /web-modernize:<next-skill-in-flow>.
```

…where `<next-skill-in-flow>` is determined by `state.status`:
- `uninitialized` → `init`
- `initialized` → `analyze`
- `analyzed` → `plan`
- `planned` → `scaffold`
- `scaffolded` → `auth`
- `auth_done` → `next`
- `complete` → (print "Migration complete — nothing to do.")

### 7. Blockers

For every unit with `status: "blocked"` or `status: "failed"`, print:

```
  <status>: <unit.id> — <failure.diagnostic or "no diagnostic recorded">
```

If none, print `blockers: none.`

### 8. Lock

If `state.lock` is non-null, print one of:

**A — fresh lock (not expired, no obvious staleness signal)**:
```
advisory lock held by <lock.holder> until <lock.expires_at> (<minutes> min remaining)
```

**B — expired lock** (`now > lock.expires_at`):
```
⚠ stale lock — held by <lock.holder>, expired <minutes> min ago
  No active session matches this lock. Recover with:
    /web-modernize:unlock
```

**C — current-user lock with no matching in-flight session** (the lock's `holder` matches `git config user.email` but no `units/<id>.json` has an `in_flight` block with the same `session_id`):
```
⚠ stale lock — held by you in a previous session (<lock.session_id>) since <lock.acquired_at>
  No in-flight unit matches this session id, so the holder's process likely died.
  Recover with:
    /web-modernize:unlock
```

If `state.lock` is null, omit this section.

### 9. Recent activity (last 5)

Across every per-unit file you read, gather all `history[]` entries (carry the unit id alongside each entry) and print the 5 most recent by timestamp:

```
recent activity:
  <at>  <by>  <unit.id>: <from> → <to>
  ...
```

If no history, print `recent activity: (none)`.

### 10. Staleness

Discovery can move without the downstream plan being regenerated. Detect this with **git commit times** — *not* file mtimes, because git does not preserve mtimes across clone/pull, so mtimes are unreliable for teammates. The last commit time for a path is `git log -1 --format=%ct -- <path>` (epoch seconds; empty output means the path is untracked or has no commits). This is read-only.

Compute the commit time of `.claude/modernize/analysis.json`, `migration.md`, and `.claude/modernize/plan.md`, then:

- If `plan.md` has no commit time (untracked / not yet committed), **skip this whole section** — there's nothing to compare against. Likewise skip any individual comparison whose other file is untracked.
- If `analysis.json` is **newer** than `plan.md`:
  ```
  ⚠ staleness: analysis.json was committed after plan.md.
    You re-ran /web-modernize:analyze but not /web-modernize:plan — the unit list may be stale.
    Run /web-modernize:plan to regenerate it (it preserves progress on existing units).
  ```
- If `migration.md` is **newer** than `plan.md`:
  ```
  ⚠ staleness: migration.md was committed after plan.md.
    The configuration changed since the plan was generated.
    Run /web-modernize:plan to regenerate the plan from the updated migration.md.
  ```

If neither is newer (or there's nothing to compare), print nothing for this section. These are advisory nudges only — `/status` never modifies state.

## After printing

Do not modify state. Do not suggest a next command unless the user is clearly at a transition point — and even then keep it to a one-liner.
