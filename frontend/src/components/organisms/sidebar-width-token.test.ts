/**
 * AE-0273 — guards the single-source-of-truth for the dashboard rail width.
 * The CSS custom property `--sidebar-width` (globals.css) and the JS constant
 * `SIDEBAR_WIDTH_PX` (constants.ts) must agree, or the responsive shell drifts.
 * Feature: responsive-dashboard-shell.feature — "sidebar width token stays in sync".
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { SIDEBAR_WIDTH_PX } from "@/components/organisms/constants";

// Vitest runs from the frontend package root.
const GLOBALS_CSS = resolve(process.cwd(), "src/app/globals.css");
const SIDEBAR_WIDTH_RE = /--sidebar-width:\s*(\d+)px/;

describe("--sidebar-width token", () => {
  it("matches the SIDEBAR_WIDTH_PX constant", () => {
    const css = readFileSync(GLOBALS_CSS, "utf8");
    const match = css.match(SIDEBAR_WIDTH_RE);
    expect(match).not.toBeNull();
    expect(Number(match![1])).toBe(SIDEBAR_WIDTH_PX);
  });
});
