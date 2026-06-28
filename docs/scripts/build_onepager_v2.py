"""
build_onepager.py
Generates web-modernize-onepager.pptx — a single-slide leave-behind that
distills the pitch into three regions: Problem · Solution + flow diagram ·
Benefits. Reuses the palette and helpers from build_presentation.py.

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
        "Ad-hoc AI prompting doesn't scale — no consistency, no shared context, re-explained every session.",
        "20+ devs prompting in parallel → merge conflicts, duplicated work, skipped verification.",
        "Progress lives in chat and spreadsheets → no audit trail, no reliable ETA.",
    ]
    bullet_block(slide, CONTENT_L, 1.42, CONTENT_W, 1.32,
                 problem_bullets, RED)

    # ─── THE SOLUTION + FLOW ──────────────────────────────────────
    section_label(slide, 2.82, "THE SOLUTION", TEAL)
    add_text(slide, CONTENT_L + 0.02, 3.18, CONTENT_W, 0.30,
             "A framework-agnostic Claude Code plugin that turns any legacy web rewrite "
             "into a repeatable, auditable, team-scale workflow — all state lives in git.",
             size=12, italic=True, color=INK)

    # Legacy → Modern stacks line (a few examples; extensible to any stack)
    stacks_y = 3.48
    add_text(slide, CONTENT_L + 0.02, stacks_y, 0.95, 0.28, "Legacy",
             size=11, bold=True, color=RED)
    add_text(slide, CONTENT_L + 0.85, stacks_y, 5.55, 0.28,
             "ASP.NET · Java JSP · AngularJS · PHP · ColdFusion",
             size=11, color=INK)
    add_text(slide, 6.55, stacks_y, 0.45, 0.28, "➜",
             size=13, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    add_text(slide, 7.05, stacks_y, 1.05, 0.28, "Modern",
             size=11, bold=True, color=GREEN)
    add_text(slide, 7.95, stacks_y, 4.95, 0.28,
             "React · Next.js · Vue · Angular · SvelteKit",
             size=11, color=INK)
    add_text(slide, CONTENT_L + 0.02, stacks_y + 0.26, CONTENT_W, 0.22,
             "…  + any other stack drops in via a short follow-up.",
             size=10, italic=True, color=SLATE)

    # Command-lifecycle flow diagram
    flow_y = 3.96
    box_h = 0.54
    arrow_w = 0.34
    setup_cmds = ["/init", "/analyze", "/plan", "/scaffold", "/foundation"]
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

    add_text(slide, CONTENT_L, flow_y + box_h + 0.18, 8.0, 0.26,
             "Setup once, left → right.", size=11, italic=True, color=SLATE)
    add_text(slide, loop_x - 0.5, flow_y + box_h + 0.18, loop_w + 0.9, 0.26,
             "repeat per unit  ×  N  (parallel across the team)",
             size=11, bold=True, italic=True, color=NAVY,
             align=PP_ALIGN.CENTER)

    # ─── THE BENEFITS ─────────────────────────────────────────────
    section_label(slide, 4.92, "THE BENEFITS", NAVY)
    benefits = [
        ("Consistency, with undo / redo",
         "One workflow + a /verify gate (lint · types · tests · parity · security). Undo with /rollback; redo with /retry."),
        ("Durable git ledger",
         "Full audit trail — every attempt, retry, and rollback recorded in git."),
        ("Parallel, conflict-free",
         "20+ devs migrate at once — per-unit git files mean zero merge conflicts."),
        ("Leadership visibility",
         "/status kanban + /report burndown & ETA, straight from real git state."),
    ]
    card_y = 5.32
    card_h = 1.30
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
             "workflow on top.        Balaji Harikrishnan · Cognizant · v0.15.0",
             size=11, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ══════════════════════════════════════════════════════════════════════════════
# Build
# ══════════════════════════════════════════════════════════════════════════════

def build():
    prs = new_prs()
    print("Building 1-slide one-pager (v0.15.0)...")
    slide_onepager(prs)
    out = r"C:\1\web-mordernize\docs\decks\web-modernize-onepager-v2.pptx"
    prs.save(out)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    build()
