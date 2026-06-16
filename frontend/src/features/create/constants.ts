/**
 * Re-export shim (AE-0138): forwards to the editorial public contract.
 * The implementation moved to `src/modules/editorial/**`. Import
 * `@/modules/editorial` directly in new code; this shim keeps the legacy
 * `@/features/create/constants` path resolving during the migration window.
 *
 * Surface is honest: it re-exports exactly the editorial barrel's PUBLIC API.
 * The `FAILED_CARD_*` constants live in `editorial/workspace/constants` and are
 * intentionally NOT on the barrel — they are module-internal and were never
 * imported cross-context via this legacy path (verified: no `@/features/create`
 * consumer outside this folder). A deep `@/modules/editorial/<internal>` import
 * here would violate the module public-contract boundary, so it is avoided; if
 * an internal symbol ever needs cross-context reach, add it to the barrel.
 */
export * from "@/modules/editorial";
