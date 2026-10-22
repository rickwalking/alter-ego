/** Re-export shim: the canonical home is the ``@/modules/identity`` guards. */
export {
  ROLES,
  PUBLIC_ROUTES,
  COOKIE_ACCESS_TOKEN,
  STATIC_FILE_PATTERN,
  isPublicRoute,
  isAuthRoute,
  isAdminRoute,
  isDashboardRoute,
  isLegacyEditorRoute,
  isEditorDashboardRoute,
  isStaticAsset,
} from "@/modules/identity";
