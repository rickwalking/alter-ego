/**
 * `identity` — bounded-context public contract (AE-0156).
 *
 * Owns the frontend auth/session surface — JWT verification/decoding, the
 * HttpOnly access-token cookie helpers, login-redirect sanitization, and the
 * client-side `useAuth` session hook — relocated from `lib/` and `hooks/` in a
 * behavior-preserving pass. This barrel is the ONLY import surface for
 * cross-context and `app/` consumers; everything else under
 * `modules/identity/**` is internal. Thin re-export shims remain at the old
 * paths (`@/lib/jwt-auth`, `@/lib/auth-cookie`, `@/hooks/use-auth`) as a safety
 * net only.
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
  COOKIE_ACCESS_TOKEN,
} from "./lib/auth-cookie";

/* --- hooks --- */
export { useAuth } from "./hooks/use-auth";
