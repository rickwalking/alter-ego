// Re-export shim (AE-0164): canonical home is @/modules/identity (guards).
export {
  ROLES,
  PUBLIC_ROUTES,
  COOKIE_ACCESS_TOKEN,
  STATIC_FILE_PATTERN,
  isPublicRoute,
  isPublicChatRoute,
  isAuthRoute,
  isAdminRoute,
  isDashboardRoute,
  isLegacyEditorRoute,
  isEditorDashboardRoute,
  isEditorRoute,
  isStaticAsset,
} from "@/modules/identity";
