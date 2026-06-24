"""
build_onepager.py
Generates web-modernize-onepager.pptx — a 2-slide leave-behind:
  Page 1 — the pitch: Problem · Solution + flow diagram · Benefits.
  Page 2 — technical end-to-end flow: every command, agent, and artifact.
Reuses the palette and helpers from build_presentation.py.

Run: python build_onepager.py
"""

from build_presentation import (
    new_prs, blank_slide, add_rect, add_text, add_arrow_right,
    NAVY, COBALT, TEAL, WHITE, SLATE, INK, GREEN, RED,
    LIGHT_B, LIGHT_G, BAND_BG,
    FONT_BODY, FONT_MONO, FONT_HEADER, FONT_HEADER_LIGHT,
)
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


CONTENT_L = 0.40
CONTENT_W = 12.533


def section_label(slide, y, text, fill):
    """Thin full-width band acting as a section header."""
    add_rect(slide, CONTENT_L, y, CONTENT_W, 0.34, fill=fill)
    add_text(slide, CONTENT_L + 0.15, y + 0.01, CONTENT_W - 0.30, 0.32,
             text, size=13, color=WHITE, font=FONT_HEADER,
             anchor=MSO_ANCHOR.MIDDLE)


def bullet_block(slide, x, y, w, h, bullets, accent):
    """White card with ▸-prefixed bullets."""
    add_rect(slide, x, y, w, h, fill=WHITE, line=accent, line_w=0.75)
    by = y + 0.12
    step = (h - 0.20) / len(bullets)
    for b in bullets:
        add_text(slide, x + 0.18, by, 0.22, 0.30, "▸",
                 size=12, bold=True, color=accent)
        add_text(slide, x + 0.42, by, w - 0.60, step,
                 b, size=12, color=INK, anchor=MSO_ANCHOR.MIDDLE)
        by += step


# ══════════════════════════════════════════════════════════════════════════════
# The single slide
# ══════════════════════════════════════════════════════════════════════════════

def slide_onepager(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.333, 7.5, fill=LIGHT_G)

    # ─── Header band ──────────────────────────────────────────────
    add_rect(slide, 0, 0, 13.333, 0.92, fill=NAVY)
    add_rect(slide, 0, 0, 0.10, 0.92, fill=TEAL)
    add_text(slide, 0.30, 0.06, 8.0, 0.50, "web-modernize",
             size=30, color=WHITE, font=FONT_HEADER_LIGHT,
             anchor=MSO_ANCHOR.MIDDLE)
    add_text(slide, 0.33, 0.56, 8.0, 0.32,
             "Generic, framework-agnostic legacy → modern web migration  —  at a glance",
             size=12, italic=True, color=TEAL)
    add_text(slide, 8.40, 0.06, 4.60, 0.82,
             "A Claude Code plugin · works\nwith any web stack",
             size=12, color=WHITE, font=FONT_HEADER,
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

    # ─── THE PROBLEM ──────────────────────────────────────────────
    section_label(slide, 1.02, "THE PROBLEM", RED)
    problem_bullets = [
        "Legacy stacks (ASP.NET, Java JSP/Spring, AngularJS, PHP, ColdFusion) are costly and risky to rewrite.",
        "Ad-hoc AI prompting doesn't scale — no shared context, re-explained every session burns tokens and inflates modernization cost.",
        "20+ devs prompting in parallel → merge conflicts, duplicated work, skipped verification.",
        "Progress lives in chat and spreadsheets → no audit trail, no reliable ETA.",
    ]
    bullet_block(slide, CONTENT_L, 1.42, CONTENT_W, 1.20,
                 problem_bullets, RED)

    # ─── THE SOLUTION + FLOW ──────────────────────────────────────
    section_label(slide, 2.70, "THE SOLUTION", TEAL)
    # Longer, showcased description — crisp header face instead of light italic body.
    add_text(slide, CONTENT_L + 0.02, 3.08, CONTENT_W, 0.60,
             "A framework-agnostic Claude Code plugin — 16 skills (slash commands) and 4 AI agents — "
             "that turns any legacy web rewrite into a repeatable, auditable, team-scale workflow. "
             "It auto-detects the legacy stack, generates a sized backlog, scaffolds the modern target, "
             "migrates feature by feature with the AI, and verifies every unit against the original "
             "— with all state versioned in git.",
             size=11, color=NAVY, font=FONT_HEADER, anchor=MSO_ANCHOR.TOP)

    # Legacy → Modern stacks line (a few examples; extensible to any stack)
    stacks_y = 3.70
    add_text(slide, CONTENT_L + 0.02, stacks_y, 0.95, 0.24, "Legacy",
             size=11, bold=True, color=RED)
    add_text(slide, CONTENT_L + 0.85, stacks_y, 5.55, 0.24,
             "ASP.NET · Java JSP · AngularJS · PHP · ColdFusion · etc.",
             size=11, color=INK)
    add_text(slide, 6.55, stacks_y, 0.45, 0.24, "➜",
             size=13, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    add_text(slide, 7.05, stacks_y, 1.05, 0.24, "Modern",
             size=11, bold=True, color=GREEN)
    add_text(slide, 7.95, stacks_y, 4.95, 0.24,
             "React · Next.js · Vue · Angular · SvelteKit · etc.",
             size=11, color=INK)
    add_text(slide, CONTENT_L + 0.02, stacks_y + 0.24, CONTENT_W, 0.20,
             "…  + any other stack drops in via a short follow-up.",
             size=10, italic=True, color=SLATE)

    # Command-lifecycle flow diagram (shorter boxes to make room for the longer solution)
    flow_y = 4.20
    box_h = 0.46
    arrow_w = 0.34
    setup_cmds = ["/init", "/analyze", "/plan", "/scaffold", "/auth"]
    box_w = 1.45
    gap = arrow_w + 0.10
    x = CONTENT_L
    for i, cmd in enumerate(setup_cmds):
        add_rect(slide, x, flow_y, box_w, box_h, fill=COBALT)
        add_text(slide, x, flow_y, box_w, box_h, cmd,
                 size=12, bold=True, color=WHITE, font=FONT_MONO,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += box_w
        add_arrow_right(slide, x + 0.04, flow_y + 0.11, arrow_w, box_h - 0.22,
                        fill=TEAL)
        x += gap

    # Looping group: ( /next → /verify ) × N
    loop_x = x
    loop_w = 13.333 - CONTENT_L - loop_x
    add_rect(slide, loop_x, flow_y - 0.14, loop_w, box_h + 0.28,
             fill=None, line=NAVY, line_w=1.25)
    inner_w = (loop_w - arrow_w - 0.30) / 2
    nx = loop_x + 0.10
    add_rect(slide, nx, flow_y, inner_w, box_h, fill=NAVY)
    add_text(slide, nx, flow_y, inner_w, box_h, "/next",
             size=12, bold=True, color=WHITE, font=FONT_MONO,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    nx += inner_w + 0.05
    add_arrow_right(slide, nx, flow_y + 0.11, arrow_w, box_h - 0.22, fill=TEAL)
    nx += arrow_w + 0.05
    add_rect(slide, nx, flow_y, inner_w, box_h, fill=NAVY)
    add_text(slide, nx, flow_y, inner_w, box_h, "/verify",
             size=12, bold=True, color=WHITE, font=FONT_MONO,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    add_text(slide, CONTENT_L, flow_y + box_h + 0.18, 8.0, 0.20,
             "Setup once, left → right.", size=10.5, italic=True, color=SLATE)
    add_text(slide, loop_x - 0.5, flow_y + box_h + 0.18, loop_w + 0.9, 0.20,
             "repeat per unit  ×  N  (parallel across the team)",
             size=10.5, bold=True, italic=True, color=NAVY,
             align=PP_ALIGN.CENTER)

    # ─── THE BENEFITS ─────────────────────────────────────────────
    section_label(slide, 5.06, "THE BENEFITS", NAVY)
    benefits = [
        ("Consistency, with undo / redo",
         "One workflow + a /verify gate (lint, types, tests). Undo a unit with /rollback; redo with /retry."),
        # Merged: durable git ledger + parallel, conflict-free.
        ("Versioned & conflict-free",
         "Full audit trail — every attempt, retry & rollback in git. Per-unit files let 20+ devs migrate in parallel with zero merge conflicts."),
        # New highlight: the behavioural-parity safety net (flagship differentiator).
        ("Parity safety net",
         "A read-only AI compares each migrated unit to the legacy original and blocks silent regressions before they ship."),
        ("Leadership visibility",
         "/status kanban + /report burndown & ETA, straight from real git state."),
    ]
    card_y = 5.42
    card_h = 1.18
    card_gap = 0.18
    card_w = (CONTENT_W - card_gap * 3) / 4
    accents = [COBALT, GREEN, TEAL, COBALT]
    for i, (title, body) in enumerate(benefits):
        cx = CONTENT_L + i * (card_w + card_gap)
        add_rect(slide, cx, card_y, card_w, card_h, fill=WHITE,
                 line=accents[i], line_w=0.75)
        add_rect(slide, cx, card_y, 0.08, card_h, fill=accents[i])
        add_text(slide, cx + 0.18, card_y + 0.10, card_w - 0.28, 0.40,
                 title, size=12, bold=True, color=accents[i])
        add_text(slide, cx + 0.18, card_y + 0.52, card_w - 0.28, card_h - 0.62,
                 body, size=10, color=INK, anchor=MSO_ANCHOR.TOP)

    # ─── Takeaway footer strip ────────────────────────────────────
    add_rect(slide, CONTENT_L, 6.78, CONTENT_W, 0.40, fill=COBALT)
    add_text(slide, CONTENT_L + 0.10, 6.80, CONTENT_W - 0.20, 0.36,
             "Same Claude Code engine.  A structured, sprint-by-sprint migration "
             "workflow on top.        Balaji Harikrishnan · Cognizant · v0.11.0",
             size=11, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ══════════════════════════════════════════════════════════════════════════════
# Page 2 — Technical end-to-end flow (every command, agent, and artifact)
# ══════════════════════════════════════════════════════════════════════════════

def lane_label(slide, y, text, fill):
    add_rect(slide, CONTENT_L, y, CONTENT_W, 0.30, fill=fill)
    add_text(slide, CONTENT_L + 0.15, y + 0.005, CONTENT_W - 0.30, 0.29,
             text, size=12, color=WHITE, font=FONT_HEADER,
             anchor=MSO_ANCHOR.MIDDLE)


def tech_box(slide, x, y, w, h, title, caption, accent, is_agent=False):
    """Box with a colored header (command=accent, agent=navy) + caption body."""
    header_fill = NAVY if is_agent else accent
    add_rect(slide, x, y, w, h, fill=WHITE, line=header_fill, line_w=0.75)
    add_rect(slide, x, y, w, 0.30, fill=header_fill)
    title_font = FONT_MONO if title.startswith("/") else FONT_HEADER
    add_text(slide, x + 0.05, y + 0.005, w - 0.10, 0.29, title,
             size=10.5, bold=True, color=WHITE, font=title_font,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if is_agent:
        add_text(slide, x + 0.05, y + 0.28, w - 0.10, 0.16, "agent",
                 size=7.5, italic=True, color=SLATE, align=PP_ALIGN.CENTER)
    add_text(slide, x + 0.08, y + (0.46 if is_agent else 0.34), w - 0.16,
             h - (0.52 if is_agent else 0.40), caption,
             size=9, color=INK, anchor=MSO_ANCHOR.TOP)


def flow_row(slide, y, h, boxes, *, arrow_color=TEAL):
    """Render a left→right row of tech boxes evenly spaced with arrows between."""
    n = len(boxes)
    arrow_w = 0.26
    box_w = (CONTENT_W - (n - 1) * arrow_w) / n
    x = CONTENT_L
    for i, (title, caption, accent, is_agent) in enumerate(boxes):
        tech_box(slide, x, y, box_w, h, title, caption, accent, is_agent)
        x += box_w
        if i < n - 1:
            add_arrow_right(slide, x, y + h / 2 - 0.12, arrow_w, 0.24,
                            fill=arrow_color)
            x += arrow_w


def slide_technical_flow(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.333, 7.5, fill=LIGHT_G)

    # ─── Header band ──────────────────────────────────────────────
    add_rect(slide, 0, 0, 13.333, 0.80, fill=NAVY)
    add_rect(slide, 0, 0, 0.10, 0.80, fill=TEAL)
    add_text(slide, 0.30, 0.05, 9.5, 0.44,
             "How web-modernize Works  —  End-to-End Flow",
             size=22, color=WHITE, font=FONT_HEADER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(slide, 0.33, 0.49, 9.5, 0.28,
             "Every command, agent, and artifact across the migration lifecycle",
             size=11, italic=True, color=TEAL)
    add_text(slide, 9.90, 0.05, 3.10, 0.70,
             "all state versioned\nin git",
             size=11, color=WHITE, font=FONT_HEADER,
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

    # ─── Lane A — SETUP (run once, sequential) ────────────────────
    lane_label(slide, 0.92, "SETUP   ·   run once, in order", SLATE)
    flow_row(slide, 1.30, 0.95, [
        ("/init",     "Workspace + state.json; .gitignore patched.", COBALT, False),
        ("/analyze",  "legacy-analyzer + interactive interview → analysis.json; pre-fills migration.md.", COBALT, False),
        ("/plan",     "Validates config → plan.md + sized unit backlog (units/*.json) with dependencies.", COBALT, False),
        ("/scaffold", "Modern skeleton + test harness + smoke-build gate; copies legacy assets.", COBALT, False),
        ("/auth",     "Migrates login first (__auth__ unit); seeds dev users, prod-safe.", COBALT, False),
    ])

    # ─── Lane B — ITERATE (per unit, parallel) ────────────────────
    lane_label(slide, 2.48, "ITERATE   ·   per unit   ·   parallel across the team", TEAL)
    flow_row(slide, 2.86, 0.95, [
        ("/next  ·  /migrate", "Auto-pick or name a unit; resolves in-flight collisions via heartbeat.", COBALT, False),
        ("unit-migrator", "Translates source → target: UI + design fidelity, tests, per-unit smoke test.", TEAL, True),
        ("/verify", "Hard gate: lint · type-check · tests must pass.", COBALT, False),
        ("parity-reviewer", "Migrated vs legacy behaviour; high-severity findings block until acknowledged.", TEAL, True),
        ("verified ✓", "Unit done; state advances. Last unit → complete.", GREEN, False),
    ])

    # Failure / recovery path
    add_rect(slide, CONTENT_L, 3.95, CONTENT_W, 0.40, fill=WHITE,
             line=RED, line_w=0.75)
    add_rect(slide, CONTENT_L, 3.95, 0.08, 0.40, fill=RED)
    add_text(slide, CONTENT_L + 0.20, 3.96, CONTENT_W - 0.30, 0.38,
             "Failure path:   ↩  /retry  re-attempts with optional guidance (keeps diagnostics)   ·   "
             "/rollback  reverts the unit to pending   →   back into the loop.",
             size=10.5, bold=True, color=INK, anchor=MSO_ANCHOR.MIDDLE)

    # ─── Lane C — ALWAYS ON (state, coordination, reporting) ──────
    lane_label(slide, 4.50, "ALWAYS ON   ·   state, coordination & reporting", NAVY)
    cells = [
        ("State in git",
         "state.json (workflow ledger) + units/<id>.json (one file per unit) — diffable, conflict-free."),
        ("Heartbeat hook",
         "Stamps in-flight units after every save, so the team sees who's on what; stale > 15 min."),
        ("/sync",
         "Deterministic merge of parallel work: highest status, freshest heartbeat, union of units."),
        ("/status  ·  /report",
         "Real-time kanban; burndown, velocity, ETA & risk — all from real git history."),
    ]
    cell_gap = 0.18
    cell_w = (CONTENT_W - cell_gap * 3) / 4
    cell_y = 4.88
    cell_h = 1.05
    cell_accents = [COBALT, COBALT, COBALT, COBALT]
    for i, (title, body) in enumerate(cells):
        cx = CONTENT_L + i * (cell_w + cell_gap)
        add_rect(slide, cx, cell_y, cell_w, cell_h, fill=WHITE,
                 line=cell_accents[i], line_w=0.75)
        add_rect(slide, cx, cell_y, 0.08, cell_h, fill=cell_accents[i])
        add_text(slide, cx + 0.18, cell_y + 0.08, cell_w - 0.28, 0.30,
                 title, size=11, bold=True, color=NAVY,
                 font=(FONT_MONO if title.startswith("/") else FONT_HEADER))
        add_text(slide, cx + 0.18, cell_y + 0.40, cell_w - 0.28, cell_h - 0.50,
                 body, size=9, color=INK, anchor=MSO_ANCHOR.TOP)

    # Agents legend
    add_rect(slide, CONTENT_L, 6.08, CONTENT_W, 0.34, fill=BAND_BG)
    add_text(slide, CONTENT_L + 0.15, 6.09, CONTENT_W - 0.30, 0.32,
             "Agents:   legacy-analyzer (detect)   ·   unit-migrator (translate)   ·   "
             "parity-reviewer (compare behaviour)   ·   permanent-gotchas (known-pitfall catalog)",
             size=10, bold=True, color=INK, anchor=MSO_ANCHOR.MIDDLE)

    # ─── Footer ───────────────────────────────────────────────────
    add_rect(slide, CONTENT_L, 6.78, CONTENT_W, 0.40, fill=NAVY)
    add_text(slide, CONTENT_L + 0.10, 6.80, CONTENT_W - 0.20, 0.36,
             "16 skills  ·  4 agents  ·  31 frameworks  ·  schema-validated state in git        "
             "Balaji Harikrishnan · Cognizant · web-modernize v0.11.0",
             size=11, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ══════════════════════════════════════════════════════════════════════════════
# Build
# ══════════════════════════════════════════════════════════════════════════════

def build():
    prs = new_prs()
    print("Building 2-slide one-pager (v0.11.0)...")
    slide_onepager(prs);        print("  [1/2] Problem · Solution + flow · Benefits")
    slide_technical_flow(prs);  print("  [2/2] Technical end-to-end flow")
    out = r"C:\1\web-mordernize\docs\decks\web-modernize-onepager.pptx"
    prs.save(out)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    build()
