# Future Implementation: Subagent per Unit Migration

> **STATUS: ✅ STILL VALID** — not yet implemented (`unit-migrator` is still loaded inline). Now also
> the prerequisite for Workflow-based parallel migration (see
> `future-code-modernization-borrowings.md` #7) and for per-`kind` dispatch to a future
> `data-layer-migrator` (see `future-data-layer-migration.md`).

## Context

Currently `agents/unit-migrator.md` is loaded **inline** by `/next`, `/migrate`, and `/retry` — not as a true subagent. This was intentional (interactive collision dialog, file mutations, and git identity all need the same conversation), but it means context accumulates across every unit migration in a session, degrading focus and code quality on large codebases.

This document describes how to convert the unit-migrator to a genuine subagent while preserving all existing behaviour.

---

## Problem the change solves

After migrating N units inline, the calling conversation holds: source files from all N units, all their stylesheets, all target files written, smoke test output, per-unit notes — potentially hundreds of KB of accumulated context that bleeds into unit N+1. A subagent for each unit sees only that unit's sources, improving translation accuracy and reducing hallucination risk.

---

## Proposed architecture

```
/next skill (inline)
  ├─ 1. Read state.json, pick unit                    ← stays inline
  ├─ 2. Collision check (Case A/B/C) + user dialog    ← stays inline (moved here from agent)
  ├─ 3. Acquire unit (write in_progress to unit file) ← stays inline
  │
  └─ 4. Launch subagent (unit-migrator) with:
         - unit JSON (full object)
         - state.json snapshot (read-only context)
         - migration.md content
         - list of source file paths
         - mode (next/migrate/retry)
         - force_deps flag
         - retry_prompt (if retry mode)

         Subagent responsibilities:
           - Read all source files + stylesheets
           - Translate to target stack
           - Write target files (heartbeat hook fires here)
           - Run smoke tests and coverage
           - Return: status, target_paths[], notes content, unit JSON delta

  ├─ 5. Receive result                                ← back inline
  └─ 6. Write final unit JSON to units/<id>.json      ← stays inline
```

---

## Files to change

| File | Change |
|------|--------|
| `agents/unit-migrator.md` | Remove §1 (collision handling) and §2 (unit acquisition) — these move to calling skills. Remove §6 (return to caller). Convert to a self-contained subagent that receives context as input and returns a structured result. Add YAML frontmatter `model: sonnet` (or effort-based override). |
| `skills/next/SKILL.md` | Add collision handling (Case A/B/C) before launching subagent. Add unit acquisition (write `in_progress`). Launch subagent. Write final unit status from returned result. |
| `skills/migrate/SKILL.md` | Same as next — add pre-launch collision + acquisition. |
| `skills/retry/SKILL.md` | Same pattern. Move `diagnostic_history` append, `retry_count` increment, and `failure.diagnostic` clear to inline pre-launch step. |

---

## What moves inline (out of unit-migrator)

### Collision handling (currently unit-migrator §1)

All three Case A/B/C dialogs require interactive user input and cannot run inside a subagent. Move entirely into each calling skill's preflight, before the subagent is launched.

- **Case A** (resume own work, fresh heartbeat): resume metadata is passed to subagent as context; subagent re-reads `files_touched_so_far` and continues. Full step-level resume (`current_step`) becomes best-effort — subagent re-reads already-written files and skips re-writing them.
- **Case B** (another dev, fresh heartbeat): show wait/override/skip dialog inline. On override, proceed to launch.
- **Case C** (stale heartbeat): show reclaim/skip/abort dialog inline. On reclaim, proceed to launch.

### Unit acquisition (currently unit-migrator §2)

Write `status = "in_progress"` and the `in_flight` block to `units/<id>.json` **before** launching the subagent. This ensures concurrent `/status` runs see the unit as claimed immediately.

For retry mode: move `diagnostic_history` append, `retry_count` increment, `last_retry_prompt` set, and `failure.diagnostic` clear to the inline pre-launch step.

---

## What stays in the subagent (unit-migrator)

- §3: Full migration body (read sources, translate, write target files, design preservation, test translation/generation)
- §4: Stop conditions → produce `failed` status delta + diagnostic; return to caller
- §5a: Smoke-test gate
- §5b: Produce `migrated` status delta; return to caller

The subagent **returns** a structured result object instead of writing final state itself:

```json
{
  "final_status": "migrated" | "failed",
  "target_paths": ["apps/web-new/src/..."],
  "notes_content": "<markdown to write to notes/<unit.id>.md>",
  "unit_delta": { },
  "diagnostic": "<only present on failure>"
}
```

The calling skill merges `unit_delta` into `units/<id>.json` and writes `notes/<id>.md` from `notes_content`.

---

## Advantages gained

| Advantage | Detail |
|---|---|
| **Context isolation** | Each unit migration starts with a clean context window; no source-file bleed from prior units |
| **Model routing** | Calling skill can inspect `unit.effort` (S/M/L/XL) and select model accordingly (e.g. Opus for XL, Haiku for S) |
| **Parallel migration** | Independent units (no shared `depends_on`) can be launched as concurrent subagents; per-unit file architecture already makes state writes conflict-free |
| **Crash isolation** | A subagent OOM or context-limit failure affects only that unit, not the calling session |

---

## Trade-offs / what's lost

| Lost feature | Mitigation |
|---|---|
| Mid-unit step resume (`in_flight.current_step`) | Subagent re-reads `files_touched_so_far` on Case A and skips re-writing existing files. Full step resume not possible. |
| Streaming progress visible to user | Calling skill prints "Migrating \<unit.id\>…" before launch. Subagent returns only when done — no per-file progress stream. |
| Heartbeat identity inside subagent | Needs testing: confirm the hook correctly reads git `user.email` inside subagent context before relying on it. |

---

## Versioning

Skill prompt changes only — no state schema changes. Bump to next patch version and update `CHANGELOG.md`.

---

## Verification checklist

After implementing:

- [ ] `/web-modernize:next` on a test legacy repo — unit goes `pending → migrated` correctly
- [ ] `units/<id>.json` has correct `in_flight`, `smoke`, `tests`, and `history` fields
- [ ] Heartbeat hook fires during subagent execution (`last_heartbeat` updates while subagent writes files)
- [ ] Case B collision dialog still works (simulate concurrent `/next` in two terminals)
- [ ] `/web-modernize:retry` on a failed unit works end-to-end
- [ ] `/web-modernize:migrate <id> --force` passes `force_deps` correctly to subagent
