/**
 * AE-0277: responsive-dashboard regression gate.
 *
 * The AE-0272 epic migrated layout-critical inline `style={{}}` on the dashboard
 * surface to Tailwind responsive utilities. This checker stops a future edit from
 * silently re-freezing those layouts. It scans an explicit allow-list (the files
 * the epic touched) for layout-freezing inline-style patterns and exits non-zero
 * on a violation.
 *
 * Branches (each has a rule-fires fixture in check-responsive-dashboard.test.ts):
 *   A. inline `gridTemplateColumns` — frozen grid; must be a Tailwind grid class.
 *   B. px `marginLeft`/`margin-left` >= 64 — frozen shell/content offset.
 *   C. fixed px `width` >= 200 on a flex/grid layout container — frozen pane width.
 *
 * Intentionally NOT a branch: a bare inline `display:"flex"` with no width. The
 * epic deliberately left non-layout-critical inline flex rows in place, so flagging
 * every inline flex would false-positive on the intended end state (and isn't the
 * regression we guard). "Layout container" is therefore defined narrowly as an
 * element whose inline style sets display flex/grid AND a fixed width >= 200px.
 *
 * Override the scanned set with RESPONSIVE_DASHBOARD_FILES (comma-separated paths,
 * relative to the frontend root) — used by the rule-fires test.
 */
import { readFileSync, existsSync } from "node:fs";
import { isAbsolute, join } from "node:path";

const FRONTEND_ROOT = join(import.meta.dirname, "..");

/** Files the AE-0272 epic made responsive (AE-0273/0274/0275/0276). */
export const ALLOW_LIST = [
  "src/app/dashboard/layout.tsx",
  "src/components/organisms/neon-sidebar.tsx",
  "src/components/organisms/neon-top-bar.tsx",
  "src/app/dashboard/create/page.tsx",
  "src/app/dashboard/create/[id]/page.tsx",
  "src/app/dashboard/create/[id]/publish/page.tsx",
  "src/app/dashboard/create/create-progress-steps.tsx",
  "src/app/dashboard/create/workspace/create-template-section.tsx",
  "src/app/dashboard/create/workspace/create-theme-section.tsx",
  "src/app/dashboard/page.tsx",
  "src/app/dashboard/analytics/page.tsx",
  "src/app/dashboard/blog-posts/page.tsx",
  "src/app/dashboard/blog-posts/blog-posts-grid.tsx",
  "src/app/dashboard/personas/page.tsx",
  "src/app/dashboard/palettes/page.tsx",
  "src/app/dashboard/rubrics/rubric-panel.tsx",
  "src/app/dashboard/calendar/calendar-grid.tsx",
  "src/app/dashboard/calendar/calendar-header.tsx",
  "src/app/dashboard/calendar/calendar-toolbar.tsx",
  "src/modules/publishing/distribution/components/regenerate-strategy-section.tsx",
  "src/app/dashboard/chat/chat-sidebar.tsx",
  "src/app/dashboard/chat/chat-header.tsx",
  "src/app/dashboard/chat/dashboard-chat-view.tsx",
  "src/modules/editorial-operations/board/workflow/components/neon-kanban-board.tsx",
];

const MARGIN_LEFT_MIN_PX = 64;
const LAYOUT_WIDTH_MIN_PX = 200;

/** Extract the inner text of every `style={{ ... }}` object via brace balancing. */
function styleBlocks(source) {
  const blocks = [];
  const marker = "style={{";
  let index = source.indexOf(marker);
  while (index !== -1) {
    let depth = 2; // we start just after the two opening braces
    let i = index + marker.length;
    const start = i;
    while (i < source.length && depth > 0) {
      const ch = source[i];
      if (ch === "{") depth += 1;
      else if (ch === "}") depth -= 1;
      i += 1;
    }
    const inner = source.slice(start, i - 2);
    const line = source.slice(0, index).split("\n").length;
    blocks.push({ inner, line });
    index = source.indexOf(marker, i);
  }
  return blocks;
}

const PX_NUMBER = /["'`]?(\d+)px/;
const BARE_NUMBER = /:\s*(\d+)\b/;
const DISPLAY_FLEX_GRID = /display\s*:\s*["'](?:flex|grid)["']/;

function pxValue(text, key) {
  const re = new RegExp(`${key}\\s*:\\s*([^,}]+)`);
  const match = text.match(re);
  if (!match) return null;
  const value = match[1];
  const px = value.match(PX_NUMBER);
  if (px) return Number(px[1]);
  const bare = `${key}: ${value}`.match(BARE_NUMBER);
  return bare ? Number(bare[1]) : null;
}

/** Return the list of violations for one file's source. */
export function findViolations(source, relPath) {
  const violations = [];
  for (const { inner, line } of styleBlocks(source)) {
    if (/gridTemplateColumns\s*:/.test(inner)) {
      violations.push({
        file: relPath,
        line,
        rule: "gridTemplateColumns",
        message: "inline gridTemplateColumns — use a Tailwind grid class",
      });
    }
    const marginLeft =
      pxValue(inner, "marginLeft") ?? pxValue(inner, "margin-left");
    if (marginLeft !== null && marginLeft >= MARGIN_LEFT_MIN_PX) {
      violations.push({
        file: relPath,
        line,
        rule: "marginLeft",
        message: `inline marginLeft ${marginLeft}px (>=${MARGIN_LEFT_MIN_PX}) — use lg:ml-[var(--sidebar-width)]`,
      });
    }
    const width = pxValue(inner, "width");
    if (
      width !== null &&
      width >= LAYOUT_WIDTH_MIN_PX &&
      DISPLAY_FLEX_GRID.test(inner)
    ) {
      violations.push({
        file: relPath,
        line,
        rule: "layout-width",
        message: `fixed width ${width}px on a flex/grid container — use a responsive class`,
      });
    }
  }
  return violations;
}

function scannedFiles() {
  const override = process.env.RESPONSIVE_DASHBOARD_FILES;
  if (override) {
    return override
      .split(",")
      .map((f) => f.trim())
      .filter(Boolean);
  }
  return ALLOW_LIST;
}

function main() {
  const files = scannedFiles();
  const usingAllowList = !process.env.RESPONSIVE_DASHBOARD_FILES;
  const allViolations = [];
  const missing = [];

  for (const rel of files) {
    const abs = isAbsolute(rel) ? rel : join(FRONTEND_ROOT, rel);
    if (!existsSync(abs)) {
      missing.push(rel);
      continue;
    }
    allViolations.push(...findViolations(readFileSync(abs, "utf8"), rel));
  }

  // Allow-list sync guard: a listed responsive file that no longer exists means
  // the allow-list drifted (file moved/renamed) and coverage was silently lost.
  if (usingAllowList && missing.length > 0) {
    process.stderr.write(
      `\nresponsive-dashboard allow-list out of sync — ${missing.length} listed ` +
        `file(s) not found (update check-responsive-dashboard.mjs):\n`,
    );
    for (const m of missing) process.stderr.write(`  ✗ ${m}\n`);
    process.exit(1);
  }

  if (allViolations.length > 0) {
    process.stderr.write(
      `\nresponsive-dashboard check FAILED — ${allViolations.length} layout-freezing ` +
        `inline style(s) reintroduced (AE-0277):\n`,
    );
    for (const v of allViolations) {
      process.stderr.write(
        `  ✗ ${v.file}:${v.line} [${v.rule}] ${v.message}\n`,
      );
    }
    process.stderr.write(
      `\nMigrate layout-critical inline styles to Tailwind responsive utilities ` +
        `(see docs/plans/ae-0272-responsive-dashboard-epic.md).\n`,
    );
    process.exit(1);
  }

  process.stdout.write(
    `responsive-dashboard check OK (${files.length} dashboard file(s) scanned).\n`,
  );
}

// Run as CLI when invoked directly (not when imported by the test).
if (
  process.argv[1] &&
  process.argv[1].endsWith("check-responsive-dashboard.mjs")
) {
  main();
}
