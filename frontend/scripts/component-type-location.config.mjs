/**
 * Shared configuration for the frontend component-type-location ratchet
 * (AE-0144 — the "13x class" PR #21 review follow-up).
 *
 * Mirrors the feature/module-boundary ratchet (AE-0083/AE-0136): existing
 * convention violations are grandfathered via a committed baseline; NEW ones
 * fail the build, and the baseline count is DOWN-ONLY.
 *
 * ## The convention
 *
 * Inside the migrated bounded-context layer (`src/modules/**`), a **component**
 * (`*.tsx`) or **hook** (`use-*.ts`) file MUST NOT declare its TypeScript
 * object-shape types inline. Such types (component `Props`, hook option/return
 * shapes, domain DTOs) belong in a colocated `types.ts` — the convention the
 * codebase already follows in `modules/publishing/blog/types.ts`,
 * `modules/quality/types.ts`, `modules/persona/types.ts`, etc.
 *
 * A reviewer left the SAME comment ("move this interface to an external file")
 * 13 times on PR #21 across `modules/publishing/blog/**` and
 * `modules/knowledge/**` because nothing in the lint gate catches inline type
 * declarations. This config + scanner make the convention enforceable.
 *
 * ## What counts as a violation
 *
 * A NON-TRIVIAL object-shape type declared inline in a component/hook file:
 *   - `interface Foo { ... }`            (any interface block)
 *   - `type Foo = { ... }`               (object-literal type alias)
 *
 * ## What is NOT a violation (deliberately out of scope)
 *
 *   - Trivial type aliases that are not object shapes:
 *       `type ViewMode = "list" | "create";`  (union of literals)
 *       `type Resp = z.infer<typeof schema>;` (derived alias)
 *   - Declarations already living in a `types.ts` / `types-*.ts` file (the
 *     convention's destination — never flagged).
 *   - Non-component, non-hook module files (`constants.ts`, `queries.ts`,
 *     `adapters/*.ts`, `lib/*.ts`): they are not the "component interface" the
 *     review comment targets and have their own homes.
 *   - Test (`*.test.*`), spec (`*.spec.*`), and Storybook (`*.stories.*`) files.
 *   - Design-system Zod prop schemas in `src/schemas/neon-*.ts` (the
 *     established, legitimate prop pattern — a different convention).
 */

import { join } from "node:path";
import { fileURLToPath } from "node:url";

/** Repository-relative frontend root (the `frontend/` directory). */
export const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");

/** Source root the convention governs: the migrated bounded-context layer. */
export const MODULES_DIR = join(ROOT, "src/modules");

/** ROOT-relative POSIX form of {@link MODULES_DIR} (for stable keys). */
export const MODULES_REL = "src/modules";

/** Committed baseline/allowlist of grandfathered inline-type declarations. */
export const BASELINE_PATH = join(
  ROOT,
  "scripts/component-type-location-baseline.json",
);

/**
 * Files excluded from the scan (not shipped component/hook internals, or the
 * convention's own destination file).
 */
export const EXCLUDE_PATTERNS = [".test.", ".spec.", ".stories."];

/**
 * Whether a ROOT-relative POSIX path is a file the convention GOVERNS: a
 * component (`*.tsx`) or a hook (`use-*.ts`) under `src/modules/**`, excluding
 * the colocated `types.ts` destination itself and excluded patterns.
 *
 * @param {string} relPosixPath e.g. `src/modules/publishing/blog/components/x.tsx`
 * @returns {boolean}
 */
export function isGovernedFile(relPosixPath) {
  if (!relPosixPath.startsWith(`${MODULES_REL}/`)) {
    return false;
  }
  if (EXCLUDE_PATTERNS.some((pattern) => relPosixPath.includes(pattern))) {
    return false;
  }
  const fileName = relPosixPath.slice(relPosixPath.lastIndexOf("/") + 1);
  // The convention's destination is never flagged.
  if (fileName === "types.ts" || fileName.startsWith("types-")) {
    return false;
  }
  // Components: any *.tsx. Hooks: use-*.ts (not other plain *.ts module files).
  if (fileName.endsWith(".tsx")) {
    return true;
  }
  return fileName.startsWith("use-") && fileName.endsWith(".ts");
}
