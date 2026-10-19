import { NextRequest, NextResponse } from "next/server";

import { resolveBackendUrl } from "@/constants/api";
import {
  AUTH_LOGIN_REDIRECT_PARAM,
  FORWARDED_PROTOCOLS,
  HTTP_HEADER_HOST,
  HTTP_HEADER_X_FORWARDED_PROTO,
} from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import {
  clearAccessTokenCookie,
  sanitizeLoginRedirect,
} from "@/modules/identity";

const SESSION_EXPIRED_ERROR = "session_expired";

/**
 * Apply the forwarded public host to the login URL. Parsed defensively: the
 * `Host` header is client-controllable, and a malformed value must never turn
 * the logout redirect into a 500.
 */
function applyForwardedHost(loginUrl: URL, forwardedHost: string): void {
  try {
    const parsedHost = new URL(`http://${forwardedHost}`);
    loginUrl.hostname = parsedHost.hostname;
    loginUrl.port = parsedHost.port;
  } catch {
    // Malformed Host header: keep the origin derived from the request URL.
  }
}

/**
 * Build the login URL from the proxy headers, not from `request.url`'s host.
 * Under the Next standalone server `request.url` carries the bind address
 * (`0.0.0.0:3000`), so the redirect would point at an unreachable host
 * (AE-0431). nginx forwards `Host $host` and `X-Forwarded-Proto $real_scheme`
 * for the frontend location (`nginx/nginx.conf.ssl`).
 */
function buildLoginUrl(request: NextRequest): URL {
  const loginUrl = new URL(PUBLIC_ROUTE_PATHS.LOGIN, request.url);

  const forwardedHost = request.headers.get(HTTP_HEADER_HOST);
  if (forwardedHost) {
    applyForwardedHost(loginUrl, forwardedHost);
  }

  const forwardedProto = request.headers
    .get(HTTP_HEADER_X_FORWARDED_PROTO)
    ?.split(",")[0]
    ?.trim();
  if (
    forwardedProto &&
    FORWARDED_PROTOCOLS.some((proto) => proto === forwardedProto)
  ) {
    loginUrl.protocol = forwardedProto;
  }

  return loginUrl;
}

/**
 * Clear session cookie and send the user to login.
 * Used when API returns 401 so stale HttpOnly cookies are removed.
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  const redirectParam = request.nextUrl.searchParams.get(
    AUTH_LOGIN_REDIRECT_PARAM,
  );
  const loginUrl = buildLoginUrl(request);
  if (redirectParam) {
    loginUrl.searchParams.set(
      AUTH_LOGIN_REDIRECT_PARAM,
      sanitizeLoginRedirect(redirectParam),
    );
  }
  loginUrl.searchParams.set("error", SESSION_EXPIRED_ERROR);

  try {
    await fetch(`${resolveBackendUrl()}/api/auth/logout`, {
      method: "POST",
      headers: { Cookie: request.headers.get("cookie") ?? "" },
    });
  } catch {
    // Backend logout is best-effort; cookie is cleared on the Next response.
  }

  const response = NextResponse.redirect(loginUrl);
  clearAccessTokenCookie(response);
  return response;
}
