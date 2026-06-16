#!/usr/bin/env node
/**
 * App-Router URL inventory (AE-0136).
 *
 * Enumerates every App Router `app/**\/page.tsx` (a URL-rendering page),
 * `app/**\/route.ts` (a Route Handler), and the metadata routes
 * `app/**\/sitemap.ts` / `app/**\/robots.ts` (which Next.js serves as real
 * `/sitemap.xml` and `/robots.txt` URLs), together with each route segment
 * config export — `dynamic`, `revalidate`, `runtime`, `dynamicParams`,
 * `fetchCache`. Emits a STABLE JSON snapshot so behavior-preserving Phase 7
 * migrations can prove URLs + segment config are byte-identical before vs after
 * a refactor.
 *
 * Usage:
 *   node scripts/url-inventory.mjs           # regenerate the snapshot
 *   node scripts/url-inventory.mjs --check    # fail if live != committed snapshot
 *
 * npm scripts: `url:inventory` (regenerate) and `url:check` (verify).
 *
 * Scope note: this is a static text scan (no bundler), intentionally
 * dependency-free. It reports literal segment-config values; non-literal
 * configs are recorded verbatim so any change still shows up in the diff.
 */

import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const APP_DIR = join(ROOT, "src/app");
const SNAPSHOT_PATH = join(ROOT, "scripts/url-inventory.snapshot.json");

/** Route segment config exports tracked for behavior preservation. */
const SEGMENT_CONFIG_KEYS = [
  "dynamic",
  "revalidate",
  "runtime",
  "dynamicParams",
  "fetchCache",
];

const PAGE_FILE = "page.tsx";
const ROUTE_FILE = "route.ts";
const SITEMAP_FILE = "sitemap.ts";
const ROBOTS_FILE = "robots.ts";

/**
 * App Router metadata route files and the public URL Next.js serves them at.
 * These contribute real URLs and must be tracked for behavior preservation.
 */
const METADATA_ROUTE_URLS = {
  [SITEMAP_FILE]: "/sitemap.xml",
  [ROBOTS_FILE]: "/robots.txt",
};

/** Route file names enumerated by the inventory (pages, handlers, metadata). */
const ROUTE_FILE_NAMES = new Set([
  PAGE_FILE,
  ROUTE_FILE,
  SITEMAP_FILE,
  ROBOTS_FILE,
]);

/**
 * @param {string} absPath
 * @returns {string} ROOT-relative POSIX path
 */
function toRelativePosix(absPath) {
  return relative(ROOT, absPath).split(sep).join("/");
}

/**
 * @param {string} dir
 * @returns {string[]} absolute paths of page.tsx / route.ts / sitemap.ts /
 *   robots.ts under `dir`
 */
function walkRouteFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkRouteFiles(full));
      continue;
    }
    if (ROUTE_FILE_NAMES.has(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

/**
 * Whether a path segment is a route group `(group)` or a parallel/intercept
 * marker that does NOT contribute to the URL.
 *
 * @param {string} segment
 * @returns {boolean}
 */
function isNonUrlSegment(segment) {
  return segment.startsWith("(") && segment.endsWith(")");
}

/**
 * Derive the public URL path for a route file relative to `src/app`.
 * Route groups `(group)` are dropped; the trailing file name is removed.
 * Metadata routes (`sitemap.ts` / `robots.ts`) resolve to the fixed public URL
 * Next.js serves them at (`/sitemap.xml`, `/robots.txt`), prefixed by any
 * URL-contributing parent segments.
 *
 * @param {string} relPosixPath e.g. `src/app/(public)/blog/[id]/page.tsx`
 * @returns {string} e.g. `/blog/[id]`
 */
function urlOf(relPosixPath) {
  const afterApp = relPosixPath.slice("src/app/".length);
  const parts = afterApp.split("/");
  const fileName = parts.pop(); // drop page.tsx / route.ts / metadata file
  const urlParts = parts.filter((segment) => !isNonUrlSegment(segment));
  const metadataUrl = METADATA_ROUTE_URLS[fileName];
  if (metadataUrl) {
    urlParts.push(metadataUrl.slice(1)); // strip leading "/" before joining
  }
  return `/${urlParts.join("/")}`.replace(/\/+$/, "") || "/";
}

/**
 * Classify a route file by kind for the snapshot.
 *
 * @param {string} relPosixPath
 * @returns {"page" | "route" | "metadata"}
 */
function kindOf(relPosixPath) {
  if (relPosixPath.endsWith(`/${ROUTE_FILE}`)) {
    return "route";
  }
  if (
    relPosixPath.endsWith(`/${SITEMAP_FILE}`) ||
    relPosixPath.endsWith(`/${ROBOTS_FILE}`)
  ) {
    return "metadata";
  }
  return "page";
}

/**
 * Extract literal route segment-config values from file contents.
 * Captures `export const <key> = <value>` for each tracked key; the raw
 * right-hand side (trimmed, trailing `;` removed) is recorded so ANY change is
 * visible in the diff, literal or not.
 *
 * @param {string} content
 * @returns {Record<string, string>} key -> raw value (only present keys)
 */
function extractSegmentConfig(content) {
  /** @type {Record<string, string>} */
  const config = {};
  for (const key of SEGMENT_CONFIG_KEYS) {
    const re = new RegExp(
      `export\\s+const\\s+${key}\\s*(?::[^=]+)?=\\s*([^\\n;]+)`,
    );
    const match = content.match(re);
    if (match) {
      config[key] = match[1].trim();
    }
  }
  return config;
}

/**
 * @returns {{ generatedFrom: string, count: number, routes: object[] }}
 */
function buildInventory() {
  const routes = walkRouteFiles(APP_DIR)
    .map((absPath) => {
      const file = toRelativePosix(absPath);
      const content = readFileSync(absPath, "utf8");
      return {
        url: urlOf(file),
        kind: kindOf(file),
        file,
        segmentConfig: extractSegmentConfig(content),
      };
    })
    .sort(
      (a, b) =>
        a.url.localeCompare(b.url) ||
        a.kind.localeCompare(b.kind) ||
        a.file.localeCompare(b.file),
    );

  return {
    $comment:
      "GENERATED by scripts/url-inventory.mjs (npm run url:inventory). App Router URL + route-segment-config baseline for behavior-preserving Phase 7 migrations (AE-0136). Verify with `npm run url:check`.",
    count: routes.length,
    routes,
  };
}

function serialize(inventory) {
  return `${JSON.stringify(inventory, null, 2)}\n`;
}

function main() {
  const checkMode = process.argv.includes("--check");
  const inventory = buildInventory();
  const serialized = serialize(inventory);

  if (!checkMode) {
    writeFileSync(SNAPSHOT_PATH, serialized, "utf8");
    process.stdout.write(
      `Wrote ${toRelativePosix(SNAPSHOT_PATH)} with ${inventory.count} App Router route(s).\n`,
    );
    return;
  }

  let committed;
  try {
    committed = readFileSync(SNAPSHOT_PATH, "utf8");
  } catch {
    process.stderr.write(
      `URL inventory snapshot missing at ${toRelativePosix(SNAPSHOT_PATH)}. ` +
        `Run \`npm run url:inventory\` to generate it.\n`,
    );
    process.exit(1);
  }

  if (committed !== serialized) {
    process.stderr.write(
      "\nURL inventory check FAILED: live App Router inventory differs from the committed snapshot.\n" +
        "App Router URLs and/or route segment config changed. Phase 7 must be behavior-preserving.\n" +
        "If the change is intentional, run `npm run url:inventory` and review the diff.\n",
    );
    process.exit(1);
  }

  process.stdout.write(
    `URL inventory check OK: ${inventory.count} App Router route(s) match the committed snapshot.\n`,
  );
}

main();
