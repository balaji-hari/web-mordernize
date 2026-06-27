# What web-modernize can borrow from code-modernization

A gap analysis of the sibling Claude Code plugin **`code-modernization`** (cm, an official
Anthropic plugin for enterprise/portfolio legacy modernization) against **`web-modernize`**
(wm, this plugin — per-unit web-UI migration at team scale).

These are the **remaining** items from the original 10-point analysis — the open work, ranked by
value-to-effort. Each is *upstream of or around* the translation (understanding, verification
rigor, presentation), not the per-unit execution loop, which is wm's strength.

> **#1–#6 already shipped in v0.12.0** — untrusted-input defense, secret-masking, the
> migration-quality critic + `/quality-check`, the parity-reviewer refute pass, the security-parity
> dimension, and the `/scaffold` toolchain preflight. See `CHANGELOG.md`.

> Companion analysis: the inverse list (what wm has that cm lacks — multi-dev coordination,
> resumable state machine, live execution gates, behavioural-parity reviewer, etc.) is wm's moat
> and is intentionally **not** duplicated here.

## Priority summary (remaining)

| # | Gap | Verdict | Effort | Value | Lands in |
|---|-----|---------|:------:|:-----:|----------|
| 7 | Workflow-tool orchestration | strategic | L | med | new `workflows/*.js` + `/analyze`, `/verify` |
| 8 | Business-rule capture (Given/When/Then) | adapt | M | med | `templates/notes-template.md`, `agents/unit-migrator.md` |
| 9 | Artifact-drift staleness | adapt | S | med | `skills/status/SKILL.md` |
| 10 | Dependency/topology visualization | adapt | M | low | `skills/report/SKILL.md`, `templates/report.md` |

---

## 7. Workflow-tool orchestration

**What cm does:** The biggest architectural difference. cm's heavy phases run as deterministic JS
**Workflow scripts** that fan out specialist agents with loop-until-dry discovery, per-finding
referees, judge panels, budget guards, and fence() injection defense — using a graceful
"Method A (Workflow if available) / Method B (subagent fallback)" pattern.

**Why it matters:** A single subagent pass misses the tail. On a 300-page app one
`legacy-analyzer` run won't enumerate every entry point; loop-until-dry will. Fan-out also makes
deep adversarial verification affordable.

**Gap in wm:** wm uses no Workflow orchestration anywhere — `/analyze` is one pass,
`parity-reviewer` is single-pass, `/verify` is sequential.

**How it'd land:** Largest lift — trial where payoff is clearest first: `/analyze` entry-point
discovery (loop-until-dry, current single pass as the Method-B fallback), then deepen `/verify`
(referee panel per high finding — the full version of the shipped refute pass). New `workflows/*.js`
+ skill prose. Strategic, not a quick win.

## 8. Business-rule capture (Given/When/Then)

**What cm does:** `/extract-rules` + `business-rules-extractor` mine domain logic into Rule
Cards: plain-English name, Given/When/Then with concrete values, `file:line`, P0/P1/P2 priority,
parameters (masked credentials), edge cases, suspected defects, confidence + SME question. P0
rules become the behavior contract the migration must prove equivalent against.

**Why it matters:** Institutional knowledge locked in code (and retiring engineers' heads) made
inspectable and testable — the spec that should survive a rewrite.

**Gap in wm:** `unit-migrator` translates "semantics not syntax" but the extracted semantics are
never written down — they live only in the model's head for one run.

**How it'd land:** The wm-sized form — an **optional** `## Behaviour contract (Given/When/Then)`
section in `templates/notes-template.md`, populated by `unit-migrator` from the legacy unit before
translation, read by `parity-reviewer` as the spec when source/target disagree. Optional per unit
(a CRUD page may have no rules worth a contract). Not cm's whole-app `BUSINESS_RULES.md`.

## 9. Artifact-drift staleness detection

**What cm does:** `/status` flags when discovery moved but downstream artifacts didn't — brief
older than assessment/topology/rules; `TOPOLOGY.html` older than `topology.json`; transform notes
older than rules — and tells you what to regenerate.

**Why it matters:** On a long migration you silently keep working from a stale plan, or migrate
against legacy files that later changed. Drift is invisible until it bites.

**Gap in wm:** `/status` detects heartbeat staleness and version skew, but not artifact drift
(e.g. re-`/analyze` without re-`/plan`, or `migration.md` changed after `plan.md`).

**How it'd land:** A "Staleness" section in `skills/status/SKILL.md` with two robust checks:
`analysis.json` newer than the unit files it seeded → nudge `/plan`; `migration.md` newer than
`plan.md`. *Drop* the "legacy file changed under a verified unit" mtime check — git doesn't
preserve mtimes in the shared-state model (false positives); if wanted later, make it
git-commit-time based.

## 10. Dependency/topology visualization

**What cm does:** `/map` builds a real dependency graph (direct + dynamic edges, data lineage,
entry points, dead-end suppression) into `topology.json`, then renders a self-contained
interactive `TOPOLOGY.html` — zoomable circle-pack sized by LOC, edges colored by kind, search,
per-node sidebar, persona-flow walkthroughs — with HTML-escaped data and a strict CSP.

**Why it matters:** The map an engineer needs before touching anything, and the bridge to
non-technical approvers; also helps plan parallel work.

**Gap in wm:** Dependencies reduce to a per-unit `depends_on[]` array and a one-paragraph
summary — no whole-migration view of ordering, fan-in/out, or bottleneck units.

**How it'd land:** *Not* the interactive circle-pack (cm-scale over-reach) and *not* a separate
`topology.json` (duplicates state, creates drift). A **Mermaid dependency graph in `/report`**,
built from each unit's `depends_on[]`, colored by status, via a `{{DEPENDENCY_GRAPH}}` placeholder
in `templates/report.md`. Lowest-value item (presentation, not correctness) but supports wm's
offline standup-coordination model.

---

*Source: gap analysis of `code-modernization` vs `web-modernize`, with each candidate graded
against wm's actual current files and design principles (pattern-level rules over per-scenario
features; offline multi-dev; additive schema only; one-file frameworks).*
