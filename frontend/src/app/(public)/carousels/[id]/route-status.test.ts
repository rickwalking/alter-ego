/**
 * AE-0446: `/carousels/<unknown id>` must answer HTTP 404, not a soft 404.
 * Gherkin: tests/features/public-carousel-404-status-ae0446.feature
 *
 * A `loading.tsx` on this segment or any ancestor wraps the page in a route
 * Suspense boundary, so Next.js streams the shell (status 200) before the page
 * calls `notFound()`. The list page keeps its skeleton inside the `(list)`
 * route group, which does not wrap this route.
 */
import { existsSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const APP_DIR = join(import.meta.dirname, "..", "..", "..");
const VIEWER_SEGMENT_DIRS = [
  "",
  "(public)",
  join("(public)", "carousels"),
  join("(public)", "carousels", "[id]"),
];
const LOADING_FILES = [
  "loading.tsx",
  "loading.ts",
  "loading.jsx",
  "loading.js",
];

function loadingBoundaries(): string[] {
  return VIEWER_SEGMENT_DIRS.flatMap((dir) =>
    LOADING_FILES.map((file) => join(APP_DIR, dir, file)),
  ).filter((path) => existsSync(path));
}

describe("public carousel viewer route status (AE-0446)", () => {
  // Scenario: An unknown carousel id answers a real 404
  it("has no loading boundary above the viewer page", () => {
    const found = loadingBoundaries().map((path) => relative(APP_DIR, path));
    expect(found).toEqual([]);
  });

  // Scenario: The carousel gallery keeps its loading skeleton
  // (also proves APP_DIR resolves, so the check above is not vacuous)
  it("keeps the gallery skeleton inside the (list) route group", () => {
    const listLoading = join(APP_DIR, "(public)", "carousels", "(list)");
    expect(existsSync(join(listLoading, "loading.tsx"))).toBe(true);
  });
});
