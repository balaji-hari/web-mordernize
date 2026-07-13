#!/usr/bin/env node
// web-modernize legacy-source guard hook (schema v3)
//
// PreToolUse hook for Write / Edit / NotebookEdit. "Never edit legacy
// source — migrate into the new app instead" is implied throughout this
// plugin's skill prompts but was previously unenforced. This hook is a
// mechanical backstop for that rule, not a replacement for it.
//
// ALLOWED write zones (never blocked), resolved against the repo root
// (the directory containing .claude/):
//   - .claude/                               — all plugin state + config
//                                              (supersedes .claude/modernize/)
//   - .github/                               — CI / workflow config
//   - apps/web-new/                          — default new-UI root
//   - state.scaffold.ui.path / .api.path / .db.path — read from state.json
//     when present, so a custom scaffold location (or the default
//     apps/api-new/ once /web-modernize:scaffold has recorded it) is
//     covered too.
//   - any file sitting DIRECTLY at the repo root (depth-0 only) — root
//     package.json (monorepo workspace wiring), tsconfig.json, .gitignore,
//     vite.config.ts, README.md, migration.md, ... These are project-level
//     config a migration legitimately edits. NOT files in subdirectories.
// The rule targets LEGACY APP SOURCE specifically — which always lives in
// a subdirectory (Controllers/, src/, WebForms .aspx, JSP folders, ...).
// So anything in a subdirectory that isn't one of the zones above is
// treated as legacy source and denied; root-level config is not.
//
// CROSS-REPO SOURCE (.claude/modernize/source_root.local.json — gitignored,
// per-developer, see skills/_shared/source-root-resolve.md): when the legacy
// tree lives outside repoRoot, the target repo holds no legacy source at all
// — the whole repo becomes new-app workspace (rule 2 below), and the external
// source_root itself is protected instead (rule 1). No local file (the
// common case) leaves everything above unchanged (rule 3). Note this is a
// SEPARATE file from state.json, with its own fail-safe semantics: missing or
// unparseable here means "no external source" (rule 3 still applies, guard
// stays active) — NOT the same as state.json's fail-*all*-open contract below,
// where an unparseable file allows the write outright. Getting these two
// confused would silently disable this entire guard for every same-repo
// developer whenever the (optional, usually-absent) local file has a typo.
//
// FAIL OPEN, deliberately (same posture as heartbeat.mjs): this is a
// backstop, not a security gate. A missing .claude/modernize/state.json
// (not a web-modernize repo, or pre-/init), an unparseable state.json, a
// target path we can't determine, a stdin read that never completes, or
// literally any thrown error all result in silently allowing the write
// (no output, exit 0). A false-allow just means this backstop missed
// one case; a false-block can stall a developer's entire session — the
// asymmetry is intentional.
//
// Deny mechanism: emits the current documented PreToolUse JSON control
// shape on stdout —
//   {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}
// — and additionally sets the older top-level {"decision":"block","reason":"..."}
// fields in the same payload as a defense-in-depth fallback in case the
// running Claude Code build only understands the pre-hookSpecificOutput
// convention. Exit code is always 0; the JSON payload alone carries the
// decision (see the caller's return value for a note on verifying this
// against a live runtime).
//
// Requirements: Node >= 16. If Node is unavailable, the plugin still
// works; this backstop just isn't there (same posture as heartbeat.mjs).

import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname, join, relative, isAbsolute } from 'node:path';

const STDIN_TIMEOUT_MS = 3000;

function findModernizeDir(startDir) {
  // Walk up from startDir looking for .claude/modernize/ (containing
  // state.json). Identical algorithm to heartbeat.mjs's own helper, so
  // both hooks agree on "where is this repo's web-modernize root."
  let dir = resolve(startDir);
  const root = resolve('/');
  while (dir !== root) {
    const candidate = join(dir, '.claude', 'modernize');
    if (existsSync(join(candidate, 'state.json'))) return candidate;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function readStdin(timeoutMs) {
  // Hook input arrives as a single JSON blob on stdin. Read it via the
  // stream events (not a synchronous fd-0 read) so this works reliably
  // when stdin is a pipe on Windows. Bounded by a timeout so a stalled
  // or absent stdin can never hang the tool call this hook is gating.
  return new Promise((resolvePromise, rejectPromise) => {
    let data = '';
    let settled = false;
    const settle = (fn, val) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fn(val);
    };
    const timer = setTimeout(
      () => settle(rejectPromise, new Error('timed out waiting for hook stdin')),
      timeoutMs
    );
    try {
      process.stdin.setEncoding('utf8');
    } catch {
      // ignore — the listeners below still work, or the timeout fires
    }
    process.stdin.on('data', (chunk) => {
      data += chunk;
    });
    process.stdin.on('end', () => settle(resolvePromise, data));
    process.stdin.on('error', (err) => settle(rejectPromise, err));
  });
}

function normalizeForCompare(absPath) {
  // Windows paths (and drive letters) are case-insensitive; POSIX paths
  // are case-sensitive. Only fold case on win32 so behaviour on
  // Linux/macOS checkouts doesn't change.
  return process.platform === 'win32' ? absPath.toLowerCase() : absPath;
}

function isInside(childAbs, parentAbs) {
  const child = normalizeForCompare(childAbs);
  const parent = normalizeForCompare(parentAbs);
  if (child === parent) return true;
  const rel = relative(parent, child);
  // rel === '' already handled above. rel starting with '..' means child
  // is an ancestor/sibling, not inside. isAbsolute(rel) catches the
  // Windows cross-drive case, where relative() returns an absolute path
  // instead of a '..'-prefixed one.
  return rel !== '' && !rel.startsWith('..') && !isAbsolute(rel);
}

function sameFile(aAbs, bAbs) {
  return normalizeForCompare(aAbs) === normalizeForCompare(bAbs);
}

function writeStdout(text) {
  return new Promise((resolvePromise) => {
    process.stdout.write(text, () => resolvePromise());
  });
}

async function main() {
  const raw = await readStdin(STDIN_TIMEOUT_MS);
  const input = JSON.parse(raw);

  const toolName = input && input.tool_name;
  if (toolName !== 'Write' && toolName !== 'Edit' && toolName !== 'NotebookEdit') return;

  const toolInput = input.tool_input || {};
  const targetPath = toolInput.file_path || toolInput.notebook_path;
  if (!targetPath || typeof targetPath !== 'string') return; // can't determine — allow

  const cwd = typeof input.cwd === 'string' && input.cwd ? input.cwd : process.cwd();
  const modernizeDir = findModernizeDir(cwd);
  if (!modernizeDir) return; // not a web-modernize repo, or pre-/init — nothing to guard yet

  const repoRoot = dirname(dirname(modernizeDir)); // <root>/.claude/modernize -> <root>/.claude -> <root>

  // Directory zones that don't depend on state.json content. .claude/
  // supersedes .claude/modernize/ (it contains it) so all plugin state +
  // config is covered; .github/ covers CI / workflow config; apps/web-new/
  // is the default new-UI root.
  const zoneDirs = [
    join(repoRoot, '.claude'),
    join(repoRoot, '.github'),
    join(repoRoot, 'apps', 'web-new'),
  ];

  // Layer in scaffold roots recorded by /web-modernize:scaffold (state.scaffold.{ui,api,db}.path
  // per templates/state.schema.json), when state.json is present and parseable.
  //
  // A missing state.json can't happen here (findModernizeDir just proved it exists via
  // existsSync), but an unparseable one means we can no longer trust our picture of this
  // repo's layout at all — per the fail-open contract, that's a reason to allow the write
  // entirely, not just fall back to the defaults above.
  let state;
  try {
    state = JSON.parse(readFileSync(join(modernizeDir, 'state.json'), 'utf8'));
  } catch {
    return; // unparseable state.json — fail (all the way) open
  }
  for (const sub of ['ui', 'api', 'db']) {
    const p = state && state.scaffold && state.scaffold[sub] && state.scaffold[sub].path;
    if (typeof p === 'string' && p.trim()) zoneDirs.push(resolve(repoRoot, p));
  }

  // Resolve the legacy source root from the gitignored, per-developer local file (NOT
  // state.json — see skills/_shared/source-root-resolve.md). This read gets its OWN
  // try/catch with its OWN fail-safe semantics: missing or unparseable here means "no
  // external source configured" (srcAbs stays null, rule 3 below still applies) — this
  // is deliberately NOT the state.json branch's "unparseable -> allow everything" contract.
  // A typo'd or not-yet-created local file (the default state for most developers) must
  // never disable the guard.
  let srcAbs = null;
  let externalSource = false;
  try {
    const localConfig = JSON.parse(readFileSync(join(modernizeDir, 'source_root.local.json'), 'utf8'));
    const rawSrc = localConfig && localConfig.source_root;
    if (typeof rawSrc === 'string' && rawSrc.trim()) {
      const resolved = isAbsolute(rawSrc) ? resolve(rawSrc) : resolve(repoRoot, rawSrc);
      // A source_root that IS the target repo root, or an ancestor containing it, is a
      // degenerate/misconfigured value (mirrors /web-modernize:analyze's "resolves to
      // exactly the target repo root -> harmless, treat as same-repo" rule, extended to
      // the ancestor case too) — isInside(repoRoot, resolved) is true for both. Protecting
      // a tree that contains the whole target repo would make rule 1 below deny every
      // write in the repo, which is never the intent. Leave srcAbs null (same-repo,
      // rule 3 applies) instead of engaging external-source handling.
      if (!isInside(repoRoot, resolved)) {
        srcAbs = resolved;
        externalSource = !isInside(srcAbs, repoRoot);
      }
    }
  } catch {
    // Missing file (the common case) or unparseable JSON — same-repo, guard stays active.
  }

  const targetAbs = resolve(targetPath);

  // 1. Always protect the legacy tree wherever it resolves to — this also covers an
  // absolute-path write into an external source_root that isn't under repoRoot at all.
  if (srcAbs && isInside(targetAbs, srcAbs)) {
    const reason = `web-modernize: refusing to edit legacy source ${targetPath} under source_root — it is read-only.`;
    await writeStdout(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'deny',
          permissionDecisionReason: reason,
        },
        decision: 'block',
        reason,
      }),
    );
    return;
  }

  // 2. External-source mode: the target repo holds no legacy source at all (it lives at
  // source_root, outside repoRoot), so the "deny non-zoned subdirectories" rule below would
  // only false-block legitimate new-app writes. Treat the whole target repo as new-app
  // workspace instead.
  if (externalSource && isInside(targetAbs, repoRoot)) return;

  // 3. Same-repo mode (source_root null, or absent): existing behaviour, unchanged.
  // Files sitting DIRECTLY at the repo root (depth-0 only) are allowed —
  // root package.json, tsconfig.json, .gitignore, vite.config.ts,
  // README.md, migration.md, etc. These are project-level config a
  // migration legitimately edits; legacy app source always lives in a
  // subdirectory, so this does not re-open the hole. A file nested in any
  // subdirectory is NOT covered by this rule.
  const isRepoRootFile = sameFile(dirname(targetAbs), repoRoot);

  const allowed = isRepoRootFile || zoneDirs.some((zone) => isInside(targetAbs, zone));
  if (allowed) return;

  const reason = `web-modernize: refusing to edit legacy source ${targetPath} — migrate into the new app (apps/web-new/) instead.`;
  const payload = JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
    // Defense-in-depth for older Claude Code builds that predate
    // hookSpecificOutput and only look at these top-level fields for
    // PreToolUse. Harmless to include both — see the caller's return
    // value for the uncertainty note on which one the running build reads.
    decision: 'block',
    reason,
  });
  await writeStdout(payload);
}

main()
  .catch((err) => {
    // Fail open: a bug in this guard must never block a legitimate write.
    try {
      process.stderr.write(`[web-modernize guard-legacy] ${err && err.message ? err.message : err}\n`);
    } catch {
      // even stderr can theoretically fail here; nothing more to do
    }
  })
  .finally(() => process.exit(0));
