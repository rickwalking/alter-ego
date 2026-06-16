/**
 * Shared configuration for the frontend feature/module-boundary ratchet.
 *
 * Mirrors the backend import ratchet (AE-0082): existing cross-context internal
 * imports are grandfathered via a committed baseline; NEW ones fail the build.
 * See AE-0083, AE-0136, and ADR-0009.
 *
 * ## Owner layers
 *
 * An "owner layer" is a source root whose top-level segments each OWN a bounded
 * context. The owning context of a file is the segment directly under the
 * layer's relative dir (e.g. `src/features/dashboard/workflow/x.ts` belongs to
 * the `dashboard` context; `src/modules/publishing/index.ts` to `publishing`).
 *
 * | Layer      | dir            | importPrefix     | publicContract | Rule                                              |
 * | ---------- | -------------- | ---------------- | -------------- | ------------------------------------------------- |
 * | `features` | `src/features` | `@/features/`    | false          | legacy: a feature must not import another's internals (AE-0083) |
 * | `modules`  | `src/modules`  | `@/modules/`     | true           | a consumer must target the barrel, never a deep internal        |
 *
 * ## App consumer
 *
 * `src/app` owns no context — it is a consumer only. It is subject to the
 * public-contract rule of every owner layer that declares one (today: modules).
 *
 * Shared layers (`components/`, `lib/`, `constants/`, `i18n/`, `schemas/`) and a
 * context's own files are always allowed and are never inspected here.
 */

import { join } from "node:path";
import { fileURLToPath } from "node:url";

/** Repository-relative frontend root (the `frontend/` directory). */
export const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");

/** Committed baseline/allowlist of grandfathered cross-context imports. */
export const BASELINE_PATH = join(ROOT, "scripts/feature-boundary-baseline.json");

/** File extensions that participate in the boundary check. */
export const SOURCE_EXTENSIONS = [".ts", ".tsx"];

/**
 * Files excluded from the boundary check (tests and Storybook stories are not
 * shipped internals).
 */
export const EXCLUDE_PATTERNS = [".test.", ".stories.", ".spec."];

/**
 * @typedef {object} OwnerLayer
 * @property {string}  name           layer id (e.g. `features`, `modules`)
 * @property {string}  dir            absolute source root
 * @property {string}  relDir         ROOT-relative POSIX source root
 * @property {string}  importPrefix   specifier prefix identifying this layer
 * @property {boolean} publicContract when true, consumers may only import the
 *   per-context barrel (`<prefix><ctx>` / `<prefix><ctx>/index`), never a deep
 *   internal path; when false, the legacy cross-context rule applies instead.
 */

/**
 * Build an owner-layer descriptor.
 *
 * @param {{ name: string, relDir: string, importPrefix: string, publicContract: boolean }} spec
 * @returns {OwnerLayer}
 */
function ownerLayer(spec) {
  return {
    name: spec.name,
    dir: join(ROOT, spec.relDir),
    relDir: spec.relDir,
    importPrefix: spec.importPrefix,
    publicContract: spec.publicContract,
  };
}

/**
 * Owner layers scanned during the Phase 7 feature -> module migration window.
 * `features` is the legacy layer (cross-feature rule); `modules` is the target
 * layer (public-contract rule).
 *
 * @type {OwnerLayer[]}
 */
export const OWNER_LAYERS = [
  ownerLayer({
    name: "features",
    relDir: "src/features",
    importPrefix: "@/features/",
    publicContract: false,
  }),
  ownerLayer({
    name: "modules",
    relDir: "src/modules",
    importPrefix: "@/modules/",
    publicContract: true,
  }),
];

/**
 * A consumer source root that owns NO context (consumer only). It is checked
 * against every owner layer's public-contract rule.
 *
 * @typedef {object} ConsumerLayer
 * @property {string} name
 * @property {string} dir     absolute source root
 * @property {string} relDir  ROOT-relative POSIX source root
 */

/** @type {ConsumerLayer} */
export const APP_CONSUMER = {
  name: "app",
  dir: join(ROOT, "src/app"),
  relDir: "src/app",
};

/* ------------------------------------------------------------------------- *
 * Back-compat exports (do not remove): the original AE-0083 API. Other tools
 * and the baseline generator referenced these names; they remain valid for the
 * legacy `features` layer so nothing else breaks.
 * ------------------------------------------------------------------------- */

/** @deprecated Use `OWNER_LAYERS`. Source directory of the legacy `features` layer. */
export const FEATURES_DIR = OWNER_LAYERS[0].dir;

/** @deprecated Use `OWNER_LAYERS`. ROOT-relative POSIX path of the `features` layer. */
export const FEATURES_REL = OWNER_LAYERS[0].relDir;

/** @deprecated Use `OWNER_LAYERS`. Import prefix of the legacy `features` layer. */
export const FEATURE_IMPORT_PREFIX = OWNER_LAYERS[0].importPrefix;
