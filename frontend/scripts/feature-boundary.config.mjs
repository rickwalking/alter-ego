/**
 * Shared configuration for the frontend feature/module-boundary ratchet.
 *
 * Mirrors the backend import ratchet (AE-0082): existing cross-context internal
 * imports are grandfathered via a committed baseline; NEW ones fail the build.
 * See AE-0083 (features), AE-0136 (modules + app consumer), and ADR-0009.
 *
 * A "context" is the top-level segment under an OWNER layer's source dir:
 *   - `src/features/<X>/...`  → owner context `@/features/<X>`  (legacy layer)
 *   - `src/modules/<X>/...`   → owner context `@/modules/<X>`   (Phase 7 target)
 *
 * A cross-context INTERNAL import is any `<prefix><other>/...` import (e.g.
 * `@/features/<other>/...` or a DEEP `@/modules/<other>/<internal>`) from a file
 * that belongs to a different top-level context.
 *
 * The module layer additionally enforces a PUBLIC CONTRACT: a module exposes
 * only its barrel `@/modules/<X>` (or `@/modules/<X>/index`); reaching past it
 * into `@/modules/<X>/<internal>` is a boundary violation from ANY scanned
 * layer — another module, the app consumer layer (`src/app`), and the
 * `features` layer (which during the migration window will import from modules
 * and is therefore also a module consumer limited to public contracts). A
 * module may still freely import its OWN internals.
 *
 * Shared layers (`components/`, `lib/`, `constants/`, `i18n/`, `schemas/`) and a
 * context's own files are always allowed and are never reported here.
 */

import { join } from "node:path";
import { fileURLToPath } from "node:url";

/** Repository-relative frontend root (the `frontend/` directory). */
export const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");

/** Committed baseline/allowlist of grandfathered cross-context imports. */
export const BASELINE_PATH = join(
  ROOT,
  "scripts/feature-boundary-baseline.json",
);

/** File extensions that participate in the boundary check. */
export const SOURCE_EXTENSIONS = [".ts", ".tsx"];

/**
 * Files excluded from the boundary check (tests and Storybook stories are not
 * shipped context internals).
 */
export const EXCLUDE_PATTERNS = [".test.", ".stories.", ".spec."];

/**
 * Import prefix for the module layer's public contract. The barrel itself
 * (`@/modules/<X>` or `@/modules/<X>/index`) is the ONLY allowed cross-module /
 * app entry point; any deeper specifier is an internal-reach violation.
 */
export const MODULE_IMPORT_PREFIX = "@/modules/";

/**
 * @typedef {object} OwnerLayer
 * @property {string} name          short layer id (for messages)
 * @property {string} dir           absolute source dir to walk
 * @property {string} relDir        ROOT-relative POSIX dir (display + owner derivation)
 * @property {string} importPrefix  import specifier prefix identifying this layer
 * @property {boolean} publicContract  if true, only the `<prefix><X>` barrel is
 *                                     allowed cross-context; deeper paths are
 *                                     internal-reach violations (modules). If
 *                                     false, any `<prefix><other>/...` is a
 *                                     cross-context import (legacy features).
 */

/**
 * Owner layers scanned for cross-context imports. Each file's owning context is
 * the segment immediately under `relDir` (e.g. `src/features/dashboard/...` →
 * `dashboard`; `src/modules/publishing/...` → `publishing`).
 *
 * Both `features` and `modules` are scanned during the Phase 7 migration window.
 *
 * @type {OwnerLayer[]}
 */
export const OWNER_LAYERS = [
  {
    name: "features",
    dir: join(ROOT, "src/features"),
    relDir: "src/features",
    importPrefix: "@/features/",
    publicContract: false,
  },
  {
    name: "modules",
    dir: join(ROOT, "src/modules"),
    relDir: "src/modules",
    importPrefix: MODULE_IMPORT_PREFIX,
    publicContract: true,
  },
];

/**
 * The consumer layer. It owns no context (so it never appears as `from`), but
 * may import module PUBLIC CONTRACTS only — a deep `@/modules/<X>/<internal>`
 * import from `app/` is a violation. App imports of `@/features/...` are not
 * inspected (the legacy features layer has no public-contract barrel yet).
 *
 * @type {{ name: string, dir: string, relDir: string }}
 */
export const APP_CONSUMER = {
  name: "app",
  dir: join(ROOT, "src/app"),
  relDir: "src/app",
};

// ---------------------------------------------------------------------------
// Backwards-compatible aliases (kept so any external callers / older imports of
// the AE-0083 names keep resolving; the features layer is OWNER_LAYERS[0]).
// ---------------------------------------------------------------------------

/** @deprecated use OWNER_LAYERS — absolute features source dir. */
export const FEATURES_DIR = OWNER_LAYERS[0].dir;
/** @deprecated use OWNER_LAYERS — ROOT-relative features dir. */
export const FEATURES_REL = OWNER_LAYERS[0].relDir;
/** @deprecated use OWNER_LAYERS — features import prefix. */
export const FEATURE_IMPORT_PREFIX = OWNER_LAYERS[0].importPrefix;
