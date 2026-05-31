---
description: "Force-clear a stale advisory lock on state.json (requires typing 'force-clear'). Use when /plan or /scaffold refuses due to a stale lock. Triggers: 'unlock', 'clear the lock', 'release the lock', 'stuck lock', 'lock is stuck', 'force unlock'."
disable-model-invocation: false
---

# `/web-modernize:unlock`

You are the **unlock** skill. Your job is to force-clear a stuck advisory lock so the team can keep working.

## Preflight

1. Read `.claude/modernize/state.json`. If the file doesn't exist, print "No web-modernize state in this repo. Did you run /web-modernize:init?" and stop.
2. Read `state.json.lock`. Possible shapes:
   - `null` or missing → print "No lock held — nothing to clear." and stop. **Do not** edit `state.json`.
   - An object with `holder`, `session_id`, `acquired_at`, `expires_at` → continue to "Show what's held."

## Show what's held

Print a clear summary so the user can decide whether force-clearing is appropriate:

```
Current lock on state.json:
  Holder:        <lock.holder>
  Session ID:    <lock.session_id>
  Acquired at:   <lock.acquired_at>      (<age in human terms, e.g. "12 minutes ago">)
  Expires at:    <lock.expires_at>       (<expired Xm ago | expires in Xm>)

This lock blocks /web-modernize:plan and /web-modernize:scaffold from
running. The normal flow is to wait until expires_at and try again — but
if you know the holder's process crashed (or it's been long enough that
the lock is plainly stale), force-clearing is safe.
```

If the lock is **not yet expired** (`expires_at > now`), add this extra caveat before asking to confirm:

```
⚠ The lock is still within its TTL. Forcibly clearing it while the holder
  is still actively writing can corrupt state.json. Only do this if you
  are certain the holder's process died.
```

## Confirm

Ask the user to type exactly `force-clear` (case-sensitive). Anything else aborts. This is intentional friction — the lock exists for a reason; a one-letter `y` would be too easy to type by accident.

If the user types anything other than `force-clear`, print "Aborted. Lock unchanged." and stop.

## Clear

If confirmed, mutate `state.json`:

1. Set `state.lock = null`.
2. Set `state.updated_at = "<now ISO>"`.
3. Append to `state.history` (additive field; create the array if missing — this does **not** require a schema bump because adding optional top-level fields is forward-compatible per the schema's `additionalProperties: true` setting, but if `additionalProperties` is `false`, write into `state.notes.lock_history` instead):
   ```json
   {
     "at": "<now>",
     "by": "<git config user.email or 'unknown'>",
     "action": "force_clear_lock",
     "previous_lock": { <the cleared lock object verbatim> }
   }
   ```
4. Write `state.json` atomically (write to `state.json.tmp`, then rename — most filesystems guarantee atomic rename within the same directory).

## Confirm to user

Print:

```
✓ Lock cleared.

  Previous holder: <holder>
  Cleared by:      <git user.email>
  At:              <now>

Recorded in state.history for audit. You can now retry /web-modernize:plan
or /web-modernize:scaffold. If the original holder's session was actually
still alive (rare), expect a state.json merge conflict on their next write
— resolve by keeping the version with the cleared lock.
```

Then suggest the next action based on `state.status`:

| state.status | Suggestion |
|---|---|
| `planned` | `/web-modernize:scaffold` |
| `scaffolded` or later | `/web-modernize:next` |
| `analyzed` | `/web-modernize:plan` |
| anything else | "Check /web-modernize:status to see where you are." |

## What this skill never does

- Never touches per-unit files in `units/`. The advisory lock on `state.json` is the only thing this clears.
- Never bumps `state.status`. That's a workflow decision; unlocking is purely a recovery action.
- Never claims a new lock for itself. Subsequent skill invocations acquire their own locks fresh.
- Never runs without explicit `force-clear` confirmation, even if the lock is expired by TTL — that's `/status`'s job to *report*, not unlock's job to assume.
