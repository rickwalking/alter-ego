/**
 * Re-export shim (AE-0137): forwards to the publishing public contract.
 * The implementation moved to `src/modules/publishing/**`. Import
 * `@/modules/publishing` directly in new code; this shim keeps the legacy
 * `@/features/publish/components` path resolving during the migration window.
 */
export * from "@/modules/publishing";
