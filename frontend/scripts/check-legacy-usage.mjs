#!/usr/bin/env node
/**
 * Enforces frontend legacy removal rules from docs/plans/frontend-legacy-removal.md
 *
 * Usage:
 *   node scripts/check-legacy-usage.mjs           # import + route guards (blocking)
 *   node scripts/check-legacy-usage.mjs --inventory  # scheduled file deletion (Phase 1)
 */

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const MANIFEST_PATH = join(ROOT, "scripts/legacy-removal-manifest.json");
const DASHBOARD_APP = join(ROOT, "src/app/dashboard");

const inventoryMode = process.argv.includes("--inventory");

/** @type {import('./legacy-removal-manifest.json')} */
const manifest = JSON.parse(readFileSync(MANIFEST_PATH, "utf8"));

const errors = [];

/**
 * @param {string} dir
 * @returns {string[]}
 */
function walkTsFiles(dir) {
  if (!existsSync(dir)) {
    return [];
  }
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkTsFiles(full));
      continue;
    }
    if (/\.(tsx?|jsx?)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

function checkForbiddenRouteDirectories() {
  for (const relDir of manifest.forbiddenRouteDirectories) {
    const abs = join(ROOT, relDir);
    if (existsSync(abs)) {
      errors.push(
        `Forbidden route directory still exists: ${relDir} (remove per docs/plans/frontend-legacy-removal.md)`,
      );
    }
  }
}

/**
 * @param {string} content
 * @param {string} symbol
 */
function usesForbiddenLegacySymbol(content, symbol) {
  const patterns = [
    new RegExp(`import\\s*\\{[^}]*\\b${symbol}\\b`),
    new RegExp(`import\\s+${symbol}\\b`),
    new RegExp(`<${symbol}[\\s/>]`),
    new RegExp(`\\b${symbol}\\s*\\(`),
  ];
  return patterns.some((re) => re.test(content));
}

function checkDashboardImports() {
  const files = walkTsFiles(DASHBOARD_APP);
  for (const file of files) {
    const rel = relative(ROOT, file);
    const content = readFileSync(file, "utf8");

    for (const symbol of manifest.forbiddenImportsInDashboard) {
      if (usesForbiddenLegacySymbol(content, symbol)) {
        errors.push(
          `${rel}: forbidden legacy usage "${symbol}" in dashboard app code`,
        );
      }
    }

    for (const importPath of manifest.forbiddenImportPathsInDashboard) {
      if (content.includes(`from "${importPath}"`) || content.includes(`from '${importPath}'`)) {
        errors.push(
          `${rel}: forbidden import path "${importPath}" in dashboard app code`,
        );
      }
    }

    const legacyPrefixes = manifest.forbiddenLegacyImportPathPrefixes ?? [];
    for (const prefix of legacyPrefixes) {
      if (content.includes(`from "${prefix}`) || content.includes(`from '${prefix}`)) {
        errors.push(
          `${rel}: forbidden legacy module import "${prefix}" in dashboard app code`,
        );
      }
    }
  }
}

function checkScheduledDeletionFiles() {
  for (const rel of manifest.scheduledDeletionFiles) {
    const abs = join(ROOT, rel);
    if (existsSync(abs)) {
      errors.push(
        `Scheduled deletion file still present: ${rel} (Phase 1 — see docs/plans/frontend-legacy-removal.md §1)`,
      );
    }
  }

  const createConstants = join(ROOT, "src/app/dashboard/create/constants.ts");
  if (existsSync(createConstants)) {
    const content = readFileSync(createConstants, "utf8");
    for (const symbol of manifest.scheduledDeletionSymbolsInCreateConstants) {
      if (content.includes(`export const ${symbol}`)) {
        errors.push(
          `src/app/dashboard/create/constants.ts: remove static export ${symbol}`,
        );
      }
    }
  }

  const chatConstantsFeature = join(
    ROOT,
    "src/features/dashboard/chat/constants.ts",
  );
  if (existsSync(chatConstantsFeature)) {
    const content = readFileSync(chatConstantsFeature, "utf8");
    for (const symbol of manifest.scheduledDeletionSymbolsInChatConstants) {
      if (content.includes(`export const ${symbol}`)) {
        errors.push(
          `features/dashboard/chat/constants.ts: remove demo export ${symbol} after mock-data deletion`,
        );
      }
    }
  }
}

function checkMockImportInApp() {
  const appDir = join(ROOT, "src/app");
  for (const file of walkTsFiles(appDir)) {
    const rel = relative(ROOT, file);
    const content = readFileSync(file, "utf8");
    if (
      content.includes("mock-data") &&
      (content.includes("MOCK_DASHBOARD") || content.includes("MOCK_BLOG_POSTS"))
    ) {
      errors.push(`${rel}: must not import dashboard mock-data in app routes`);
    }
  }
}

if (inventoryMode) {
  checkScheduledDeletionFiles();
} else {
  checkForbiddenRouteDirectories();
  checkDashboardImports();
  checkMockImportInApp();
}

if (errors.length > 0) {
  console.error(
    inventoryMode
      ? "Legacy inventory check failed:\n"
      : "Legacy usage guard failed:\n",
  );
  for (const err of errors) {
    console.error(`  - ${err}`);
  }
  console.error(
    "\nSee docs/plans/frontend-legacy-removal.md for removal details and replacements.",
  );
  process.exit(1);
}

console.log(
  inventoryMode
    ? "Legacy inventory check passed (all scheduled deletions complete)."
    : "Legacy usage guard passed (no forbidden dashboard imports or routes).",
);
