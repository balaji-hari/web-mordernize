Resolve `SOURCE_ROOT` — the root of the legacy (source) tree, which may live outside the target/working repo:

1. Check for `.claude/modernize/source_root.local.json` at the target repo root (the directory containing `.claude/`; never cwd). This file is **gitignored and per-developer** — it is never committed, so its value can differ machine to machine.
2. If it exists and parses with a non-empty `source_root` string, that raw string is `SOURCE_ROOT_RAW`. Otherwise `SOURCE_ROOT_RAW = null` (same-repo — the common case, and the default when no local file has been created).
3. Resolve to an absolute path: `null` → the target repo root itself; an absolute path → used as-is; a relative path → resolved against the target repo root (never cwd).
4. A missing or unparseable `source_root.local.json` is **not an error** — treat it exactly like `null`. Only `/web-modernize:analyze` does deeper validation (existence, not-inside-target-repo, git-repo detection for `state.source_repo` provenance) — every other consumer just resolves and reads.

Every skill/agent that reads legacy files resolves `source_paths[]` (and any legacy sibling it follows — stylesheets, master pages, test files) against this resolved `SOURCE_ROOT`, not the working directory.
