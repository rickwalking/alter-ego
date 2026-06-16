/**
 * Re-export shim (AE-0139): forwards to the carousel-presentation public contract.
 * The implementation moved to `src/modules/carousel-presentation/**`. Import
 * `@/modules/carousel-presentation` directly in new code; this shim keeps the legacy
 * `@/features/carousel/queries` path resolving during the migration window.
 */
export * from "@/modules/carousel-presentation";
