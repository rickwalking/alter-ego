import type { NextRequest, NextResponse } from "next/server";

import { SECONDS_PER_HOUR } from "@/constants/time";

import { COOKIE_ACCESS_TOKEN } from "../guards";

export { COOKIE_ACCESS_TOKEN };

const DEFAULT_TOKEN_MAX_AGE_SEC = SECONDS_PER_HOUR;

/** Whether the incoming request used HTTPS (directly or via proxy). */
export function isSecureRequest(request: NextRequest): boolean {
  if (request.nextUrl.protocol === "https:") {
    return true;
  }
  const forwarded = request.headers.get("x-forwarded-proto");
  if (!forwarded) {
    return false;
  }
  return forwarded.split(",")[0]?.trim() === "https";
}

/** Attach HttpOnly JWT cookie for Next.js middleware (same host as the UI). */
export function setAccessTokenCookie(
  response: NextResponse,
  token: string,
  request: NextRequest,
): void {
  response.cookies.set(COOKIE_ACCESS_TOKEN, token, {
    httpOnly: true,
    secure: isSecureRequest(request),
    sameSite: "lax",
    path: "/",
    maxAge: DEFAULT_TOKEN_MAX_AGE_SEC,
  });
}

/** Only allow same-origin relative redirects after login. */
export function sanitizeLoginRedirect(redirect: string | null): string {
  if (!redirect || !redirect.startsWith("/") || redirect.startsWith("//")) {
    return "/dashboard/chat";
  }
  if (redirect.startsWith("/login")) {
    return "/dashboard/chat";
  }
  return redirect;
}

/** Remove stale session cookie (e.g. after 401 or invalid JWT). */
export function clearAccessTokenCookie(response: {
  cookies: { delete: (name: string) => void };
}): void {
  response.cookies.delete(COOKIE_ACCESS_TOKEN);
}
