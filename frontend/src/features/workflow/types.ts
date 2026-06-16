/**
 * Re-export shim (AE-0138): forwards to the editorial public contract.
 * The implementation moved to `src/modules/editorial/**`. Import
 * `@/modules/editorial` directly in new code; this shim keeps the legacy
 * `@/features/workflow/types` path resolving during the migration window.
 *
 * Surface is honest: it re-exports exactly the editorial barrel's PUBLIC API.
 * `NotificationItem` / `NotificationListResponse` live in
 * `editorial/workflow/types` and are intentionally NOT on the barrel — they are
 * module-internal (consumed only by `use-notifications`) and were never imported
 * cross-context via this legacy path (verified: no `@/features/workflow`
 * consumer outside this folder). A deep `@/modules/editorial/<internal>` import
 * here would violate the module public-contract boundary, so it is avoided; if
 * an internal type ever needs cross-context reach, add it to the barrel.
 */
export * from "@/modules/editorial";
