/**
 * braces <=3.0.3 (GHSA-vfj7-8cjw-p6xm) overflows the stack on deep patterns.
 * The patched copy must still expand ordinary patterns and reject depth 257.
 */
import { createRequire } from "node:module";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const require = createRequire(import.meta.url);
const BRACES_DIR = join(
  import.meta.dirname,
  "..",
  "..",
  "scripts",
  "braces-patched",
);
const braces = require(BRACES_DIR) as (
  pattern: string,
  options?: { expand?: boolean },
) => string[];

const SHALLOW_PATTERN = "{a,b}";
const EXPAND = { expand: true };
const SAFE_DEPTH = 256;
const OVER_DEPTH = 257;
const PATCHED_VERSION = "3.0.4";

function nested(depth: number): string {
  return `${"{".repeat(depth)}a${"}".repeat(depth)}`;
}

describe("patched braces", () => {
  it("expands a shallow pattern", () => {
    expect(braces(SHALLOW_PATTERN, EXPAND)).toEqual(["a", "b"]);
  });

  it("accepts nesting at the depth cap", () => {
    expect(() => braces(nested(SAFE_DEPTH))).not.toThrow();
  });

  it("throws when nesting exceeds the depth cap", () => {
    expect(() => braces(nested(OVER_DEPTH))).toThrow(SyntaxError);
  });

  it("reports a version outside the vulnerable range", () => {
    const pkg = require(join(BRACES_DIR, "package.json")) as {
      version: string;
    };
    expect(pkg.version).toBe(PATCHED_VERSION);
  });
});
