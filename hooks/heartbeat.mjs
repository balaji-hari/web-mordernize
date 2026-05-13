#!/usr/bin/env node
// web-modernize heartbeat hook (schema v3)
//
// Fires on every Write/Edit. For each unit file under
// .claude/modernize/units/*.json that has status == "in_progress" AND an
// in_flight block claimed by the *current* developer (matching by git user
// email + hostname), updates its in_flight.last_heartbeat to "now" so
// /web-modernize:status can detect genuine stalls vs. active work.
//
// Scope-narrow rule (added v0.8.2):
// Only bump units where in_flight.by == git config user.email AND
// in_flight.host == os.hostname(). This avoids two bugs:
//   1. Performance — scanning + rewriting every in_progress unit on every
//      Write becomes O(units) fs work per tool call. With 50+ units this
//      adds hundreds of ms per Write on Windows.
//   2. Cross-dev misattribution — without the filter, Alice's local Write
//      events refresh Bob's unit's heartbeat (because she has Bob's unit
//      in_progress in her local checkout from a recent git pull), then she
//      commits and Bob sees a heartbeat he didn't make.
//
// Designed to fail silently — a missing state.json, missing units directory,
// a git binary not on PATH, or any error reading/writing must not block the
// tool call that triggered it.
//
// Importantly, this hook does NOT touch state.json itself. Heartbeat-only
// writes go to the per-unit files, keeping state.json conflict-free in the
// multi-developer workflow.
//
// Requirements: Node >= 16. If Node is unavailable, the plugin still works;
// only stale-session detection becomes less precise.

import { readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { hostname } from 'node:os';
import { execSync } from 'node:child_process';

function findModernizeDir(startDir) {
  // Walk up from startDir looking for .claude/modernize/ (containing state.json).
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

function getGitEmail() {
  try {
    return execSync('git config user.email', {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return null; // no git, no config, no problem — we just skip
  }
}

try {
  const cwd = process.cwd();
  const modernizeDir = findModernizeDir(cwd);
  if (!modernizeDir) process.exit(0); // not a web-modernize repo; nothing to do

  const unitsDir = join(modernizeDir, 'units');
  if (!existsSync(unitsDir)) process.exit(0); // pre-v3 state or fresh init; nothing to do

  const me = getGitEmail();
  const myHost = hostname();
  if (!me) process.exit(0); // no git identity to match — skip the whole pass

  const now = new Date().toISOString();

  const entries = readdirSync(unitsDir);
  for (const name of entries) {
    if (!name.endsWith('.json')) continue;
    const path = join(unitsDir, name);

    let unit;
    try {
      unit = JSON.parse(readFileSync(path, 'utf8'));
    } catch {
      continue; // malformed file; skip silently
    }

    if (unit.status !== 'in_progress') continue;
    if (!unit.in_flight || typeof unit.in_flight !== 'object') continue;

    // Scope-narrow: only bump units claimed by *this* dev on *this* host.
    if (unit.in_flight.by !== me) continue;
    if (unit.in_flight.host && unit.in_flight.host !== myHost) continue;

    unit.in_flight.last_heartbeat = now;
    // Preserve a stable 2-space indent for git friendliness.
    writeFileSync(path, JSON.stringify(unit, null, 2) + '\n', 'utf8');
  }
} catch (err) {
  // Silent failure: never break the tool call that triggered us.
  // Optionally log to stderr for debugging.
  process.stderr.write(`[web-modernize heartbeat] ${err.message}\n`);
}

process.exit(0);
