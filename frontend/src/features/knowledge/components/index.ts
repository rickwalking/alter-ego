/**
 * Re-export shim (AE-0139): forwards to the knowledge public contract.
 * The implementation moved to `src/modules/knowledge/**`. Import
 * `@/modules/knowledge` directly in new code; this shim keeps the legacy
 * `@/features/knowledge/components` path resolving during the migration window.
 */
export * from "@/modules/knowledge";
