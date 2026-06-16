/**
 * Re-export shim (AE-0139): forwards to the quality public contract.
 * The implementation moved to `src/modules/quality/**`. Import
 * `@/modules/quality` directly in new code; this shim keeps the legacy
 * `@/features/rubrics/hooks/use-rubrics` path resolving during the migration window.
 */
export * from "@/modules/quality";
