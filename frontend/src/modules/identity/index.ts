/**
 * `identity` — bounded-context public contract (AE-0156).
 *
 * Owns the frontend auth/session surface — JWT verification/decoding, the
 * HttpOnly access-token cookie helpers, login-redirect sanitization, and the
 * client-side `useAuth` session hook — relocated from `lib/` and `hooks/` in a
 * behavior-preserving pass. This barrel is the ONLY import surface for
 * cross-context and `app/` consumers; everything else under
 * `modules/identity/**` is internal. Thin re-export shims remain at the old
 * paths (`@/lib/jwt-auth`, `@/lib/auth-cookie`) as a safety net only (the
 * `@/hooks/use-auth` shim was removed in AE-0154/QA cleanup — no importers).
 *
 * AE-0164 adds the route-level guard surface (role constants + route-class
 * predicates + the access-token cookie name + the static-asset matcher) used by
 * `middleware.ts` and the admin route group, with a shim at
 * `@/constants/middleware`.
 *
 * NOTE: `lib/authenticated-fetch` and `lib/server-fetch` are the app-wide HTTP
 * client (not auth-specific) and intentionally stay in `lib/`.
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

/* --- types --- */
export type { AccessTokenPayload, AuthUser, UseAuthResult } from "./types";

/* --- jwt lib --- */
export { verifyAccessToken, decodeJwtPayloadUnsafe } from "./lib/jwt-auth";

/* --- cookie lib --- */
export {
  setAccessTokenCookie,
  clearAccessTokenCookie,
  sanitizeLoginRedirect,
  isSecureRequest,
} from "./lib/auth-cookie";

/* --- route-level guards (AE-0164) --- */
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
} from "./guards";

/* --- hooks --- */
export { useAuth } from "./hooks/use-auth";
