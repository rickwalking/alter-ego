/**
 * Re-export shim (AE-0139): forwards to the conversation public contract.
 * The implementation moved to `src/modules/conversation/**`. Import
 * `@/modules/conversation` directly in new code; this shim keeps the legacy
 * `@/features/chat/types` path resolving during the migration window.
 */
export * from "@/modules/conversation";
