import type { NextRequest, NextResponse } from "next/server";

import { HTTP_HEADER_X_FORWARDED_PROTO } from "@/constants/auth";
import { SECONDS_PER_MINUTE } from "@/constants/time";

import { COOKIE_ACCESS_TOKEN } from "../guards";

export { COOKIE_ACCESS_TOKEN };

/** Same env var and default as the backend's ``access_token_expire_minutes``. */
const ACCESS_TOKEN_EXPIRE_MINUTES_ENV = "ACCESS_TOKEN_EXPIRE_MINUTES";
const DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60;

/** The session cookie lifetime: the backend's token lifetime, in seconds. */
function accessTokenMaxAgeSeconds(): number {
  const minutes = Number(process.env[ACCESS_TOKEN_EXPIRE_MINUTES_ENV]);
  const valid =
    Number.isInteger(minutes) && minutes > 0
      ? minutes
      : DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES;
  return valid * SECONDS_PER_MINUTE;
}

/** Whether the incoming request used HTTPS (directly or via proxy). */
export function isSecureRequest(request: NextRequest): boolean {
  if (request.nextUrl.protocol === "https:") {
    return true;
  }
  const forwarded = request.headers.get(HTTP_HEADER_X_FORWARDED_PROTO);
  if (!forwarded) {
    return false;
  }
  return forwarded.split(",")[0]?.trim() === "https";
}

/**
 * Attach HttpOnly JWT cookie for Next.js middleware (same host as the UI), with
 * the same attributes as the backend's login cookie: SameSite=Strict and the
 * token's lifetime.
 */
export function setAccessTokenCookie(
  response: NextResponse,
  token: string,
  request: NextRequest,
): void {
  response.cookies.set(COOKIE_ACCESS_TOKEN, token, {
    httpOnly: true,
    secure: isSecureRequest(request),
    sameSite: "strict",
    path: "/",
    maxAge: accessTokenMaxAgeSeconds(),
  });
}

/** Remove stale session cookie (e.g. after 401 or invalid JWT). */
export function clearAccessTokenCookie(response: {
  cookies: { delete: (name: string) => void };
}): void {
  response.cookies.delete(COOKIE_ACCESS_TOKEN);
}
