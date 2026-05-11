#!/usr/bin/env node
// web-modernize heartbeat hook (schema v3)
//
// Fires on every Write/Edit. For each unit file under
// .claude/modernize/units/*.json that has status == "in_progress" and an
// in_flight block, updates its in_flight.last_heartbeat to "now" so
// /web-modernize:status can detect genuine stalls vs. active work.
//
// Designed to fail silently — a missing state.json, missing units directory,
// or any error reading/writing must not block the tool call that triggered it.
//
// Importantly, this hook does NOT touch state.json itself. Heartbeat-only
// writes go to the per-unit files, keeping state.json conflict-free in the
// multi-developer workflow.
//
// Requirements: Node >= 16. If Node is unavailable, the plugin still works;
// only stale-session detection becomes less precise.

import { readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';

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

try {
  const cwd = process.cwd();
  const modernizeDir = findModernizeDir(cwd);
  if (!modernizeDir) process.exit(0); // not a web-modernize repo; nothing to do

  const unitsDir = join(modernizeDir, 'units');
  if (!existsSync(unitsDir)) process.exit(0); // pre-v3 state or fresh init; nothing to do

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
