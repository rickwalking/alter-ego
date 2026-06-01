import { NextRequest, NextResponse } from "next/server";

import { AUTH_LOGIN_REDIRECT_PARAM } from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { clearAccessTokenCookie, sanitizeLoginRedirect } from "@/lib/auth-cookie";

const DEFAULT_BACKEND_URL = "http://localhost:8000";

function resolveBackendUrl(): string {
  return (
    process.env.API_BASE_URL ??
    (process.env.NODE_ENV === "production"
      ? "http://backend:8000"
      : DEFAULT_BACKEND_URL)
  );
}

/**
 * Clear session cookie and send the user to login.
 * Used when API returns 401 so stale HttpOnly cookies are removed.
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  const redirectParam = request.nextUrl.searchParams.get(
    AUTH_LOGIN_REDIRECT_PARAM,
  );
  const loginUrl = new URL(PUBLIC_ROUTE_PATHS.LOGIN, request.url);
  if (redirectParam) {
    loginUrl.searchParams.set(
      AUTH_LOGIN_REDIRECT_PARAM,
      sanitizeLoginRedirect(redirectParam),
    );
  }
  loginUrl.searchParams.set("error", "session_expired");

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
