---
description: >
  Prints a progress dashboard for the web-modernize migration. Read-only and safe
  to run at any time. Shows current workflow phase, counts of pending/in-progress/
  migrated/verified units, what is currently in flight (and by whom), the next
  unit /web-modernize:next would pick, and any blockers or stale sessions.
disable-model-invocation: false
---

# `/web-modernize:status`

You are the **status** skill. You are **read-only**. Do not modify any files.

## What to read

1. `.claude/modernize/state.json` — required. If it does not exist, tell the user "No web-modernize state found. Run `/web-modernize:init` to start." and stop.
2. `.claude/modernize/plan.md` — optional. If it exists, you can reference phase names.
3. The current ISO-8601 UTC time.

## What to print

Format the output as a dashboard with these sections, in this order. Use plain ASCII tables; no emojis (per project conventions).

### 1. Header

```
web-modernize status — <PROJECT_NAME from migration.md §1, or repo dir name>
state.json: <relative path>     schema_version: <n>     plugin_version: <v>
workflow phase: <state.status>     updated_at: <state.updated_at> (<relative time>)
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

Count units by status:

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

**Stale detection**: if `last_heartbeat` is more than 15 minutes ago, append on a new line `    ⚠ POSSIBLY STALLED — heartbeat is <N> min old. /web-modernize:next will offer to take over.` (Use the word STALLED in plain text — no emoji is fine; the ⚠ here is just an example; if your environment does not render it, use `WARNING:`.)

### 6. Next up

If `state.status` is `in_progress` (or later) and there are pending units, determine the next unit `/web-modernize:next` would pick:

- Filter `units` to those with `status: "pending"` AND all `depends_on` already in `{"migrated", "verified"}`.
- Sort by `phase` asc, then list order.
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

If `state.lock` is non-null and `expires_at` is in the future, print:

```
advisory lock held by <lock.holder> until <lock.expires_at> (<minutes> min remaining)
```

Otherwise omit.

### 9. Recent activity (last 5)

Across all units, gather the last 5 `history[]` entries by timestamp and print them most recent first:

```
recent activity:
  <at>  <by>  <unit.id>: <from> → <to>
  ...
```

If no history, print `recent activity: (none)`.

## After printing

Do not modify state. Do not suggest a next command unless the user is clearly at a transition point — and even then keep it to a one-liner.
