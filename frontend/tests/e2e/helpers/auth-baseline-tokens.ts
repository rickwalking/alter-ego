/**
 * AE-0165 — Auth baseline safety net helpers.
 *
 * Builds CRAFTED, UNSIGNED JWTs to drive the frontend middleware as it behaves
 * TODAY: the frontend runtime has no `AUTH_JWT_SECRET`/`SECRET_KEY`, so
 * `verifyAccessToken` (src/lib/jwt-auth.ts) falls back to
 * `decodeJwtPayloadUnsafe`, which ONLY base64url-decodes the payload segment and
 * checks `exp`, `type === "auth"` and `role` is a string — the signature is
 * never verified. These helpers therefore emit a real `header.payload.sig`
 * shape with an arbitrary signature string.
 *
 * This is a BEHAVIOR-CAPTURE baseline (no app code changes). If a later
 * identity-module relocation (AE-0156/0164) introduces a real secret, these
 * tokens would stop validating and the specs would need a signing step — that
 * divergence is the point: the baseline pins current behavior.
 */

/** Roles understood by the middleware (mirror of src/constants/middleware ROLES). */
export const BASELINE_ROLES = {
  ADMIN: "admin",
  EDITOR: "editor",
  /** A role the middleware treats as a plain authenticated user. */
  VIEWER: "viewer",
} as const;

export type BaselineRole = (typeof BASELINE_ROLES)[keyof typeof BASELINE_ROLES];

/** Matches JWT_TYPE_AUTH in src/constants/jwt.ts. */
const TOKEN_TYPE_AUTH = "auth";

/** Arbitrary, ignored-by-fallback signature segment. */
const UNSIGNED_SIGNATURE = "baseline-unsigned-signature";

const SECONDS_PER_HOUR = 3600;

interface AccessTokenClaims {
  sub: string;
  email: string;
  role: string;
  type: string;
  exp: number;
  iat: number;
}

function base64UrlEncode(value: string): string {
  return Buffer.from(value, "utf-8")
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function encodeSegment(payload: Record<string, unknown>): string {
  return base64UrlEncode(JSON.stringify(payload));
}

function buildToken(claims: AccessTokenClaims): string {
  const header = encodeSegment({ alg: "HS256", typ: "JWT" });
  const body = encodeSegment(claims as unknown as Record<string, unknown>);
  return `${header}.${body}.${UNSIGNED_SIGNATURE}`;
}

interface CraftTokenOptions {
  role: BaselineRole;
  /** Seconds until expiry (negative = already expired). Default: 1 hour. */
  expiresInSeconds?: number;
  email?: string;
  sub?: string;
}

/** Craft an unsigned access token whose payload the fallback decoder accepts. */
export function craftAccessToken(options: CraftTokenOptions): string {
  const {
    role,
    expiresInSeconds = SECONDS_PER_HOUR,
    email = `${role}@baseline.test`,
    sub = `baseline-${role}`,
  } = options;
  const nowSeconds = Math.floor(Date.now() / 1000);
  return buildToken({
    sub,
    email,
    role,
    type: TOKEN_TYPE_AUTH,
    iat: nowSeconds,
    exp: nowSeconds + expiresInSeconds,
  });
}

/** A valid (~1h) admin token. */
export function craftAdminToken(): string {
  return craftAccessToken({ role: BASELINE_ROLES.ADMIN });
}

/** A valid (~1h) editor token. */
export function craftEditorToken(): string {
  return craftAccessToken({ role: BASELINE_ROLES.EDITOR });
}

/** A valid (~1h) plain-viewer token. */
export function craftViewerToken(): string {
  return craftAccessToken({ role: BASELINE_ROLES.VIEWER });
}

/** An admin token whose `exp` is already in the past. */
export function craftExpiredAdminToken(): string {
  return craftAccessToken({
    role: BASELINE_ROLES.ADMIN,
    expiresInSeconds: -SECONDS_PER_HOUR,
  });
}

/** The httpOnly cookie name the middleware reads (COOKIE_ACCESS_TOKEN). */
export const ACCESS_TOKEN_COOKIE = "access_token";

/** Shape accepted by Playwright `context.addCookies`. */
export interface AccessTokenCookie {
  name: string;
  value: string;
  domain: string;
  path: string;
  httpOnly: boolean;
  sameSite: "Lax";
}

/** Build the access_token cookie entry for a crafted token on localhost. */
export function accessTokenCookie(token: string): AccessTokenCookie {
  return {
    name: ACCESS_TOKEN_COOKIE,
    value: token,
    domain: "localhost",
    path: "/",
    httpOnly: true,
    sameSite: "Lax",
  };
}
