#!/usr/bin/env node
// scripts/lint-frameworks.mjs
//
// Sections-consistency lint for frameworks/*.md.
//
// Reads every frameworks/*.md file, parses its frontmatter `role`, and
// asserts that the required `## Section` headings for that role are
// present. Prints every file that's missing a required section; exits
// non-zero if any file has a gap, else exits 0.
//
// Plain Node, built-ins only — no npm dependencies. Run with:
//   node scripts/lint-frameworks.mjs

import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRAMEWORKS_DIR = path.resolve(__dirname, "..", "frameworks");

// Required sections per frontmatter `role`. Keep in sync with the
// "Standard sections" list in CLAUDE.md's "Framework files" section.
const REQUIRED_SECTIONS = {
  source: ["## Detection", "## Entry-point heuristic", "## Recommended target"],
  "target-ui": [
    "## Scaffold",
    "## Test framework",
    "## Dev server",
    "## Verify commands",
    "## Integration",
  ],
  "target-api": [
    "## Scaffold",
    "## Test framework",
    "## Dev server",
    "## Auth notes",
    "## Verify commands",
    "## Data migration",
  ],
};

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function parseFrontmatterRole(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!match) {
    return { error: "no frontmatter block found" };
  }
  const frontmatter = match[1];
  const roleMatch = frontmatter.match(/^role:\s*(.+?)\s*$/m);
  if (!roleMatch) {
    return { error: "frontmatter has no 'role' key" };
  }
  // Strip optional surrounding quotes, e.g. role: "source".
  const role = roleMatch[1].trim().replace(/^["']|["']$/g, "");
  return { role };
}

function findMissingSections(text, requiredSections) {
  return requiredSections.filter((heading) => {
    const re = new RegExp(`^${escapeRegExp(heading)}\\s*$`, "m");
    return !re.test(text);
  });
}

function main() {
  let files;
  try {
    files = readdirSync(FRAMEWORKS_DIR)
      .filter((f) => f.toLowerCase().endsWith(".md"))
      .sort();
  } catch (err) {
    console.error(`Cannot read frameworks directory at ${FRAMEWORKS_DIR}: ${err.message}`);
    process.exit(1);
    return;
  }

  if (files.length === 0) {
    console.error(`No frameworks/*.md files found at ${FRAMEWORKS_DIR}`);
    process.exit(1);
    return;
  }

  let hadFailure = false;
  let checkedCount = 0;
  const roleCounts = {};

  for (const file of files) {
    const filePath = path.join(FRAMEWORKS_DIR, file);
    const text = readFileSync(filePath, "utf8");

    const { role, error } = parseFrontmatterRole(text);
    if (error) {
      console.log(`✗ ${file}: ${error}`);
      hadFailure = true;
      continue;
    }

    const requiredSections = REQUIRED_SECTIONS[role];
    if (!requiredSections) {
      console.log(
        `✗ ${file}: unrecognized role '${role}' (expected one of: ${Object.keys(REQUIRED_SECTIONS).join(", ")})`
      );
      hadFailure = true;
      continue;
    }

    checkedCount++;
    roleCounts[role] = (roleCounts[role] || 0) + 1;

    const missing = findMissingSections(text, requiredSections);
    if (missing.length > 0) {
      console.log(`✗ ${file} (role: ${role}) missing: ${missing.join(", ")}`);
      hadFailure = true;
    }
  }

  console.log("---");
  const roleSummary = Object.entries(roleCounts)
    .map(([r, n]) => `${n} ${r}`)
    .join(", ");
  console.log(`Checked ${checkedCount}/${files.length} framework file(s): ${roleSummary}`);

  if (hadFailure) {
    console.log("FAIL: one or more framework files are missing required sections.");
    process.exit(1);
    return;
  }

  console.log("PASS: every framework file has its role's required sections.");
  process.exit(0);
}

main();
