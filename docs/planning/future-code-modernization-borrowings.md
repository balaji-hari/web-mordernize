# What web-modernize can borrow from code-modernization

A gap analysis of the sibling Claude Code plugin **`code-modernization`** (cm, an official
Anthropic plugin for enterprise/portfolio legacy modernization) against **`web-modernize`**
(wm, this plugin — per-unit web-UI migration at team scale).

These are the 10 capabilities cm has that wm currently lacks, ranked by value-to-effort. Each
is *upstream of or around* the translation — understanding, verification rigor, and safety
discipline — not the per-unit execution loop, which is wm's strength. None requires a
`schema_version` bump.

> Companion analysis: the inverse list (what wm has that cm lacks — multi-dev coordination,
> resumable state machine, live execution gates, behavioural-parity reviewer, etc.) is wm's moat
> and is intentionally **not** duplicated here.

## Priority summary

| # | Gap | Verdict | Effort | Value | Lands in |
|---|-----|---------|:------:|:-----:|----------|
| 1 | Untrusted-code injection defense | adopt | S | high | `agents/legacy-analyzer.md`, `agents/parity-reviewer.md` |
| 2 | Secret-masking / quarantine | adopt | S | high | `agents/{legacy-analyzer,unit-migrator,parity-reviewer}.md`, `/init` gitignore |
| 3 | Idiomatic-quality critique agent | adopt (new agent) | M | high | new `agents/migration-critic.md` + `/verify` advisory |
| 4 | Adversarial verification (refute pass) | adopt | S | med | `agents/parity-reviewer.md` |
| 5 | Security audit (as parity dimension) | adapt | M | med | `agents/parity-reviewer.md` + `/verify` |
| 6 | Toolchain preflight | adapt | M | med | top of `skills/scaffold/SKILL.md` |
| 7 | Workflow-tool orchestration | strategic | L | med | new `workflows/*.js` + `/analyze`, `/verify` |
| 8 | Business-rule capture (Given/When/Then) | adapt | M | med | `templates/notes-template.md`, `agents/unit-migrator.md` |
| 9 | Artifact-drift staleness | adapt | S | med | `skills/status/SKILL.md` |
| 10 | Dependency/topology visualization | adapt | M | low | `skills/report/SKILL.md`, `templates/report.md` |

Recommended first cut: **#1, #2, #3, #4** — best value-to-effort, all additive, no schema change.

---

## 1. Untrusted-code injection defense

**What cm does:** Every cm agent treats source content as *data, never instructions*.
Instruction-shaped text in comments/strings (`"SYSTEM: ignore previous instructions"`,
`"mark this rule approved"`) is reported as a finding, never followed; a claim is real only if
the *executable code* exhibits it. In the Workflow scripts, untrusted agent output is wrapped in
`fence(<<<UNTRUSTED…>>>)` before flowing into downstream prompts, with fence markers stripped so
it can't be escaped.

**Why it matters:** A novel attack/error class for tools that read code as input — a hostile or
accidentally instruction-shaped comment can corrupt analysis later steps trust.

**Gap in wm:** `legacy-analyzer` and `parity-reviewer` emit JSON that downstream skills act on
without re-validation — `/analyze` seeds units from `entry_points[]`; `/verify` blocks the
`migrated→verified` transition on parity severity. No rule guards against injection.

**How it'd land:** A 4–6 line `## Untrusted input` block under Hard constraints in
`agents/legacy-analyzer.md` and `agents/parity-reviewer.md`. Scoped as an explicit cross-cutting
rule — not a `permanent-gotchas` entry (that file's charter is WebSearch-unreachable bugs).

## 2. Secret-masking / quarantine

**What cm does:** Mandatory across every agent — never write a credential value into output;
mask to first 2–4 chars + `****`, cite `file:line`, recommend rotation. Raw secrets go only to a
gitignored `SECRETS.local.md`. `/harden` splits patches into a shareable hunk file + a gitignored
`.local.patch` for credential-removal diffs, and verifies `git check-ignore` before writing.

**Why it matters:** Legacy web apps are full of hardcoded secrets (connection strings in
`web.config`, keys in PHP, creds in Spring `properties`). A tool that reads them and writes
reports multiplies exposure.

**Gap in wm:** wm writes git-tracked `notes/*.md`, `state.json`, and `/report` outputs with no
masking rule — a secret can land verbatim in a committed artifact.

**How it'd land:** Add the masking rule to `agents/legacy-analyzer.md`, `agents/unit-migrator.md`,
`agents/parity-reviewer.md`; have `/init`'s gitignore patch cover
`.claude/modernize/**/SECRETS.local.md`. Pairs with #1.

## 3. Idiomatic-quality critique (the "JOBOL" lens)

**What cm does:** `architecture-critic` reviews *transformed code* for idiomaticity, not
behaviour — flags "JOBOL" (legacy structure leaking into the new language), ceremonial error
handling, single-use abstractions, tests that exercise paths instead of pinning behaviour, and
"what does on-call need at 3am." Ranks Blocker/High/Medium/Nit, ends with "if I could change one
thing…".

**Why it matters:** wm's biggest review blind spot. A migration can be behaviourally perfect yet
unmaintainable — WebForms-in-React (useEffect soup imitating postbacks), jQuery-in-Vue,
JSP-scriptlet-in-controller. Behavioural parity won't catch any of it.

**Gap in wm:** `parity-reviewer` checks behaviour (5 dimensions); `unit-migrator` is *instructed*
to translate "semantics not syntax" but nothing independently verifies the result is idiomatic.

**How it'd land:** New read-only subagent `agents/migration-critic.md` (shaped like
`parity-reviewer`), wired into `/verify` as an **advisory, non-blocking** pass so it never traps a
working migration. The strongest genuinely-new agent we could add.

## 4. Adversarial verification (refute-before-confirm)

**What cm does:** `harden-scan.js` runs a refutation pass (hunt for reasons a finding is invalid)
*before* a confirmation pass; split verdicts get demoted. `extract-rules.js` gives every rule a
citation referee and every P0 rule a two-judge panel, and loops until two rounds find nothing new.

**Why it matters:** False positives are expensive on a blocking gate; refute-first ordering kills
them early; judge panels raise precision on the highest-stakes claims.

**Gap in wm:** `parity-reviewer` is single-pass and its high findings *block* the `verified`
transition — a false-positive high traps a working migration and forces a `/parity-check`
acknowledge.

**How it'd land:** Lite (cheap): a **refute pass** in `agents/parity-reviewer.md` — re-examine
each high finding ("is there a reading where both behave the same?") and downgrade/drop the
indefensible before emitting JSON; add "every high survived a refute pass" to the self-check.
Full (ties to #7): a referee panel per high finding via Workflow orchestration.

## 5. Security audit (as a parity dimension)

**What cm does:** `/harden` + `security-auditor` cover injection (SQL/NoSQL/OS/LDAP/template),
auth/session, sensitive-data exposure, access control (IDOR), XSS/CSRF, deserialization,
vulnerable deps, SSRF/path traversal, misconfiguration — each finding with CWE, severity,
`file:line`, a one-sentence exploit scenario, and a fix. Hard rule: no articulable exploit →
downgrade severity (kills phantom findings).

**Why it matters:** The most damaging *silent* web-migration regression is a security one —
dropping a parameterized query, an output-encoding step, or an authorization check while porting.

**Gap in wm:** Only auth password-hashing gotchas in `permanent-gotchas.md`. Nothing checks for
injection, dropped authz, or secrets moving into the client bundle.

**How it'd land:** *Not* a full `/harden` command (over-reaches per-unit scope). A
**security-parity dimension** in `parity-reviewer` — new finding kinds
(`security_authz_dropped`, `security_injection`, `security_secret_exposure`,
`security_output_encoding`), default severity high, additive to the schema (no `schema_version`
bump, exactly how `parity_findings` was added). `/verify` blocks security highs like any high;
extend "What NOT to flag" so intentional auth changes aren't flagged.

## 6. Toolchain preflight

**What cm does:** `/preflight` detects the stack, checks analysis tooling, smoke-compiles a
representative source file with the legacy toolchain (catching dialect/copybook/format errors on
first contact), inventories missing includes, and emits a per-command Ready / Ready-with-gaps /
Not-ready verdict — distinguishing "tool present" vs "runnable here" vs "actually ran."

**Why it matters:** Discovering a missing runtime mid-migration wastes a half-scaffolded
subsystem; a 60-second readiness report up front prevents it.

**Gap in wm:** Toolchain problems surface *late* — at the scaffold smoke or unit smoke gate —
especially painful on the unknown-stack 3-question path.

**How it'd land:** A "Toolchain preflight" step at the **top of `skills/scaffold/SKILL.md`** (the
skill that reads each framework's `## Dev server` floor + `## Scaffold` command): probe
`node -v` / `dotnet --version` / `mvn -v` / `python3 -V`, confirm the legacy build manifest
exists, print a red/yellow/green table with install one-liners. Not `/analyze` (target stack
isn't chosen yet) and not a new command.

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
(referee panel per high finding — the full version of #4). New `workflows/*.js` + skill prose.
Strategic, not a quick win.

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
