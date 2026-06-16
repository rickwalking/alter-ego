/**
 * Re-export shim (AE-0138): forwards to the editorial-operations public contract.
 * The implementation moved to `src/modules/editorial-operations/**`. Import
 * `@/modules/editorial-operations` directly in new code; this shim keeps the legacy
 * `@/features/dashboard/chat/adapters/chat-adapter` path resolving during the migration window.
 */
export * from "@/modules/editorial-operations";
