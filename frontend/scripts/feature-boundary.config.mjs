/**
 * Shared configuration for the frontend feature-boundary ratchet.
 *
 * Mirrors the backend import ratchet (AE-0082): existing cross-feature
 * internal imports are grandfathered via a committed baseline; NEW ones
 * fail the build. See AE-0083 and ADR-0009.
 *
 * A "feature" is the top-level segment under `src/features/`
 * (e.g. `features/dashboard/workflow/...` belongs to the `dashboard` feature).
 * A cross-feature INTERNAL import is any `@/features/<other>/...` import from a
 * file that lives in a different top-level feature.
 *
 * Shared layers (`components/`, `lib/`, `constants/`, `i18n/`, `schemas/`) and a
 * feature's own files are always allowed and are never inspected here.
 */

import { join } from "node:path";
import { fileURLToPath } from "node:url";

/** Repository-relative frontend root (the `frontend/` directory). */
export const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");

/** Source directory holding all feature modules. */
export const FEATURES_DIR = join(ROOT, "src/features");

/** Committed baseline/allowlist of grandfathered cross-feature imports. */
export const BASELINE_PATH = join(ROOT, "scripts/feature-boundary-baseline.json");

/**
 * Path (relative to ROOT) regex used to display violations consistently.
 * Uses POSIX separators regardless of platform.
 */
export const FEATURES_REL = "src/features";

/** File extensions that participate in the boundary check. */
export const SOURCE_EXTENSIONS = [".ts", ".tsx"];

/**
 * Files excluded from the boundary check (tests and Storybook stories are not
 * shipped feature internals).
 */
export const EXCLUDE_PATTERNS = [".test.", ".stories.", ".spec."];

/**
 * Import specifier prefix that identifies a feature-internal import.
 * Only `@/features/...` specifiers are inspected; shared layers such as
 * `@/components`, `@/lib`, `@/constants`, `@/i18n`, `@/schemas` are ignored.
 */
export const FEATURE_IMPORT_PREFIX = "@/features/";
