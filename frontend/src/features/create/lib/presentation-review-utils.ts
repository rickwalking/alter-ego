/**
 * Re-export shim (AE-0138): forwards to the editorial public contract.
 * The implementation moved to `src/modules/editorial/**`. Import
 * `@/modules/editorial` directly in new code; this shim keeps the legacy
 * `@/features/create/lib/presentation-review-utils` path resolving during the migration window.
 */
export * from "@/modules/editorial";
