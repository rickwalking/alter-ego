import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));

/** Committed grandfathered baseline of unused exports (down-only). */
export const BASELINE_PATH = resolve(HERE, "dead-code-baseline.json");

export const REGEN_HINT =
  "Run `npm run dead-code:baseline` to (re)generate it (only ever to ratchet DOWN).";
