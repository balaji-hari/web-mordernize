<!--
  notes-template.md — copied by /web-modernize:next and /web-modernize:migrate

  One file per unit at .claude/modernize/notes/<unit-id>.md. The plugin appends
  to this file across sessions; everything here is git-tracked so other
  developers can read your reasoning later.
-->

# Unit: {{UNIT_ID}}

- **Kind**: {{UNIT_KIND}}
- **Source**: {{SOURCE_PATHS}}
- **Target**: {{TARGET_PATHS}}
- **Depends on**: {{DEPENDS_ON}}

## Design decisions

Document the non-obvious choices made while porting this unit. Future readers (and code reviewers) need the *why*, not the *what*.

- <!-- e.g., "Replaced the server-side ViewState bag with a useReducer hook because the legacy code mutated 4 fields atomically" -->

## Source code map

Map of the legacy file(s) → target file(s) at the symbol level. Helps reviewers verify nothing was dropped.

| Legacy symbol | Target symbol | Notes |
|---------------|---------------|-------|
|               |               |       |

## Gotchas

Anything that surprised you, broke unexpectedly, or that the next person should know.

- <!-- e.g., "LoginController.aspx.cs reads Session['ReturnUrl'] which the new SPA doesn't have — wired to ?next= query param instead" -->

## Verification

Filled in by `/web-modernize:verify`.

- **Lint**:
- **Typecheck**:
- **Unit tests**:
- **Manual test notes**:
- **Verified by / at**:

## History

Filled in automatically by the plugin. Most recent first.

- <!-- {{TIMESTAMP}} — {{USER}}: {{ACTION}} -->
