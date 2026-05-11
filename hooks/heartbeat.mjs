#!/usr/bin/env node
// web-modernize heartbeat hook
//
// Fires on every Write/Edit. If a migration unit is currently in_progress
// (state.json.units[].status == "in_progress"), updates its
// in_flight.last_heartbeat to "now" so /web-modernize:status can detect
// genuine stalls vs. active work.
//
// Designed to fail silently — a missing state.json, missing in-flight unit,
// or any error reading/writing must not block the tool call that triggered it.
//
// Requirements: Node >= 16. If Node is unavailable, the plugin still works;
// only stale-session detection becomes less precise.

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';

function findStateFile(startDir) {
  // Walk up from startDir looking for .claude/modernize/state.json.
  let dir = resolve(startDir);
  const root = resolve('/');
  while (dir !== root) {
    const candidate = join(dir, '.claude', 'modernize', 'state.json');
    if (existsSync(candidate)) return candidate;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

try {
  const cwd = process.cwd();
  const statePath = findStateFile(cwd);
  if (!statePath) process.exit(0); // not a web-modernize repo; nothing to do

  const raw = readFileSync(statePath, 'utf8');
  const state = JSON.parse(raw);
  if (!Array.isArray(state.units)) process.exit(0);

  const now = new Date().toISOString();
  let touched = false;

  for (const unit of state.units) {
    if (unit.status === 'in_progress' && unit.in_flight && typeof unit.in_flight === 'object') {
      unit.in_flight.last_heartbeat = now;
      touched = true;
    }
  }

  if (touched) {
    state.updated_at = now;
    // Preserve a stable 2-space indent for git friendliness.
    writeFileSync(statePath, JSON.stringify(state, null, 2) + '\n', 'utf8');
  }
} catch (err) {
  // Silent failure: never break the tool call that triggered us.
  // Optionally log to stderr for debugging.
  process.stderr.write(`[web-modernize heartbeat] ${err.message}\n`);
}

process.exit(0);
