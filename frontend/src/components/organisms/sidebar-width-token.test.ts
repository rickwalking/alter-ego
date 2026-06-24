/**
 * AE-0273 — guards the single-source-of-truth for the dashboard rail width.
 * The Tailwind class literals (`w-[Npx]` in the sidebar, `lg:ml-[Npx]` in the
 * dashboard layout) must equal the JS constant `SIDEBAR_WIDTH_PX`, or the rail
 * and the content offset drift apart. (A CSS `--sidebar-width` var was dropped
 * because Tailwind v4 tree-shook the @theme declaration; literals are used now.)
 * Feature: responsive-dashboard-shell.feature — "sidebar width token stays in sync".
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { SIDEBAR_WIDTH_PX } from "@/components/organisms/constants";

const ROOT = process.cwd(); // vitest runs from the frontend package root
const SIDEBAR = resolve(ROOT, "src/components/organisms/neon-sidebar.tsx");
const LAYOUT = resolve(ROOT, "src/app/dashboard/layout.tsx");

describe("dashboard rail width token", () => {
  it("the sidebar w-[Npx] literal matches SIDEBAR_WIDTH_PX", () => {
    const src = readFileSync(SIDEBAR, "utf8");
    expect(src).toContain(`w-[${SIDEBAR_WIDTH_PX}px]`);
  });

  it("the layout content offset lg:ml-[Npx] matches SIDEBAR_WIDTH_PX", () => {
    const src = readFileSync(LAYOUT, "utf8");
    expect(src).toContain(`lg:ml-[${SIDEBAR_WIDTH_PX}px]`);
  });
});
