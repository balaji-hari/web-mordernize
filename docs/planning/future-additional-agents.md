# Plan: Additional agents to make migration faster or better

> **STATUS: 🟡 PARTIALLY SHIPPED** — Candidate 2 (behavioural-parity reviewer) shipped in v0.11.0,
> and the quality-grader idea shipped in v0.12.0 as `agents/migration-critic.md`. The two open
> candidates below — Candidate 1 (parallel migrator) and Candidate 3 (dependency preflight) —
> remain future work; see `future-code-modernization-borrowings.md`.

## Context

The plugin currently ships two functional agents (`legacy-analyzer`, `unit-migrator`) plus one knowledge document framed as an agent (`permanent-gotchas`). These subagent additions would deliver meaningful improvements without fragmenting the existing architecture. This doc captures them as future work — implementation is not committed.

**Design constraint** (from user memory: *"prefer pattern-level rules over per-scenario features"*): new agents earn their place only when they offer genuinely separable concerns — different context window, different tool set, or different failure mode. Specialised mini-agents that just split `unit-migrator` into pieces (test-translator, design-extractor, asset-extractor, etc.) are explicitly rejected.

---

## Candidate 1 — Parallel migrator coordinator  (speed)

> **Reshape (2026):** prefer implementing this via the **Workflow tool**
> (`future-code-modernization-borrowings.md` #7) — fan out `unit-migrator` as parallel subagents —
> rather than a bespoke coordinator agent. Depends on the subagent conversion in
> `future-subagent-unit-migrator.md`.

### Problem

`/next` migrates one unit per invocation. A team of 5 developers gets 5× parallelism, but each individual developer is still serial. After `/auth` there are typically 30–80 independent units; on a single dev box they migrate one at a time.

### Agent shape

New file `agents/parallel-migrator.md` (coordinator subagent). Algorithm:

1. Read `units/*.json`. Pick K independent pending units — no shared `depends_on`, no overlapping paths in their predicted `target_paths`.
2. Spawn K `unit-migrator` subagent invocations in parallel (Claude Code's subagent primitive runs each in its own context).
3. Sequence heartbeat writes and finalisation so per-unit files don't race.
4. Aggregate results into a single summary for the user.

### Surface

New skill `skills/next-batch/SKILL.md`. Defaults conservative (`--n=3`). Do **not** change `/next`'s default behaviour — exposed as a separate opt-in. User invocation: `/web-modernize:next-batch` or `/web-modernize:next-batch --n=5`.

### Why the per-unit-file split makes this safe

Schema v3 already proved per-unit files prevent multi-dev conflicts. Same shape applies to parallel agents on one box: agent A writing `units/PaymentProcessor.json` and agent B writing `units/LoginPage.json` touch zero shared files. Top-level `state.json` writes (heartbeats, transitions) are sequenced by the coordinator.

### Wins

- Roughly N× wall-clock speedup for the embarrassingly-parallel portion of the migration (most feature units after auth).
- No new state schema.
- Leadership-friendly demo: "one developer migrates 3 units in the time it took to migrate 1."

### Cost

- N× tokens during a batch. Cost is opt-in (separate command).
- Coordinator complexity for unit-selection (must reject sets with overlapping target paths, even if `depends_on` is clean).

---

## Candidate 3 — Pre-flight dependency analyzer  (both)

### Problem

Today `/next` and `/migrate` block on unmet `depends_on` (or stub with `--force`). The team learns about a missing dependency *when* migration starts. Worse, sometimes a unit's `depends_on` declaration is incomplete — the legacy code uses a helper that wasn't seeded as its own unit — and the migration fails or produces broken stubs.

### Agent shape

New file `agents/preflight.md`. Read-only. Algorithm:

1. Read the unit's `source_paths`.
2. Scan for imports / includes / references to other legacy files.
3. Cross-reference against `units/*.json` to map references to unit IDs.
4. Return a structured report:
   ```json
   {
     "unit_id": "Dashboard",
     "declared_deps": ["__auth__", "UserService"],
     "inferred_deps": ["UserService", "OrderService", "Layout"],
     "missing_deps": [
       { "ref": "OrderService.cs", "in_plan": false,
         "recommendation": "Add as a unit in /plan, or treat as cross-cutting" }
     ],
     "pending_deps": [
       { "id": "UserService", "status": "pending",
         "recommendation": "Migrate UserService first or use --force to stub" }
     ]
   }
   ```

### Surface

Runs automatically as a pre-step of `/next` and `/migrate`. Output goes to `notes/<unit-id>.md`. If `missing_deps` is non-empty, the skill warns and asks for confirmation before proceeding.

### Wins

- Cuts retry cycles by surfacing dependency issues before migration starts.
- Saves wall-clock + token cost on the failed-then-retry path.
- Improves migration success rate.

### Cost

- ~1 cheap agent invocation per `/next`. Read-only.
- Adds latency to every `/next` — could be made opt-out via flag if teams find it noisy.

---

## Anti-patterns explicitly rejected

These were considered and rejected:

- **Per-stack expert agents** (`dotnet-translator`, `java-translator`, etc.). Conflicts with the framework-file model (Part 3 of the v0.10.0 design). Per-stack knowledge belongs in `frameworks/*.md` as data, not in agent prompts that must be updated independently.
- **Specialised mini-agents fragmenting unit-migrator** (test-translator, design-extractor, visual-fidelity-checker, asset-extractor). Splits one concern across many files; coordination overhead exceeds the value. Keep `unit-migrator` generic and let it consult framework files + permanent-gotchas inline.
- **Documentation-generator agent**. `/report` already covers stakeholder reporting. A separate "tech docs" agent overlaps without adding clear new value.
- **Per-concern auditors** (security scanner, perf scanner, accessibility scanner) as always-on agents. Each is useful in isolation, but adding all inflates the surface area without proportionate value. Better as opt-in `/verify` post-checks that read `verify.config.json` rather than dedicated agents.
- **Translation-quality grader agent.** Tempting but subjective — would mostly restate what tests + parity-reviewer already capture, with worse signal-to-noise.
  - **Shipped (v0.12.0):** the code-modernization analysis (`future-code-modernization-borrowings.md` #3) reframed this as an *idiomatic-structure* critic (detecting "JOBOL" / WebForms-in-React leakage) rather than a subjective grade — objective and orthogonal to behavioural parity. It shipped as the advisory (non-blocking) `agents/migration-critic.md` + `/web-modernize:quality-check`.

---

## Recommended order

Of the two open candidates: do **Candidate 1 (parallel coordinator)** first — the biggest demonstrable speedup, and it fits cleanly on the existing per-unit-file architecture (safe by construction). Note the 2026 reshape above: prefer building it via the Workflow tool (`future-code-modernization-borrowings.md` #7), which itself depends on the `unit-migrator` subagent conversion in `future-subagent-unit-migrator.md`.

Hold **Candidate 3 (preflight)** until you observe retry patterns in real migrations indicating it would pay off. It's the most speculative — the cost is real (latency on every `/next`), and the benefit depends on how often dependency declarations are wrong, which is hard to predict without telemetry.

*(Candidate 2, the behavioural-parity reviewer, shipped in v0.11.0 and is no longer tracked here.)*

---

## Critical files (when implemented)

For each open candidate, the file footprint:

### Candidate 1 — parallel coordinator
| File | Change |
|---|---|
| `agents/parallel-migrator.md` | **NEW.** Coordinator agent. |
| `skills/next-batch/SKILL.md` | **NEW.** Exposes `/web-modernize:next-batch [--n=K]`. |
| `templates/state.schema.json` | No change. |
| Slash-command table in README + plugin.json `keywords` | Optional update. |

### Candidate 3 — preflight
| File | Change |
|---|---|
| `agents/preflight.md` | **NEW.** Read-only dependency analyser. |
| `skills/next/SKILL.md` + `skills/migrate/SKILL.md` | New pre-step: invoke preflight; warn on missing/pending deps before unit-migrator. |
| `templates/unit.schema.json` | Additive: `inferred_deps[]`, `missing_deps[]`. No schema bump. |

---

## Verification (when implemented)

Each candidate's verification is independent and can ship separately.

**Parallel coordinator**: in a workspace with ≥ 6 independent pending units, run `/web-modernize:next-batch --n=3`. Confirm 3 units migrate concurrently, each gets its own `in_flight` block, all finalise correctly. Time it; compare to 3 sequential `/next` invocations.

**Preflight**: create a unit with a deliberately-missing `depends_on` reference. Run `/web-modernize:next`. Confirm preflight surfaces the missing dep with a recommendation; user can proceed (`--force`) or fix the plan and re-run.
