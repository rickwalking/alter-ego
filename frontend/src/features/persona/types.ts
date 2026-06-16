/**
 * Re-export shim (AE-0139): forwards to the persona public contract.
 * The implementation moved to `src/modules/persona/**` (consolidating the
 * former `features/persona` + `features/personas` duplication). Import
 * `@/modules/persona` directly in new code; this shim keeps the legacy
 * `@/features/persona/types` path resolving during the migration window.
 */
export * from "@/modules/persona";
