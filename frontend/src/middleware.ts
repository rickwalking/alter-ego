import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { AUTH_LOGIN_REDIRECT_PARAM } from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import {
  isPublicRoute,
  isAuthRoute,
  isAdminRoute,
  isEditorDashboardRoute,
  isLegacyEditorRoute,
  isStaticAsset,
  COOKIE_ACCESS_TOKEN,
  ROLES,
  clearAccessTokenCookie,
  verifyAccessToken,
} from "@/modules/identity";

function loginRedirectUrl(request: NextRequest, returnPath?: string): URL {
  const loginUrl = new URL(PUBLIC_ROUTE_PATHS.LOGIN, request.url);
  if (returnPath && returnPath !== PUBLIC_ROUTE_PATHS.LOGIN) {
    loginUrl.searchParams.set(AUTH_LOGIN_REDIRECT_PARAM, returnPath);
  }
  return loginUrl;
}

function redirectWithClearedSession(
  request: NextRequest,
  returnPath?: string,
): NextResponse {
  const response = NextResponse.redirect(loginRedirectUrl(request, returnPath));
  clearAccessTokenCookie(response);
  return response;
}

/** No session cookie: auth pages render, everything else goes to login. */
function anonymousResponse(
  request: NextRequest,
  pathname: string,
): NextResponse {
  if (isAuthRoute(pathname)) {
    return NextResponse.next();
  }
  return NextResponse.redirect(loginRedirectUrl(request, pathname));
}

/** A cookie that no longer verifies: clear it (and re-login off auth pages). */
function invalidSessionResponse(
  request: NextRequest,
  pathname: string,
): NextResponse {
  if (!isAuthRoute(pathname)) {
    return redirectWithClearedSession(request, pathname);
  }
  const response = NextResponse.next();
  clearAccessTokenCookie(response);
  return response;
}

/** Admin pages need an admin; editor pages need an admin or an editor. */
function roleCanOpen(pathname: string, role: string): boolean {
  if (isAdminRoute(pathname) && role !== ROLES.ADMIN) {
    return false;
  }
  const editorOnly =
    isEditorDashboardRoute(pathname) || isLegacyEditorRoute(pathname);
  return !editorOnly || role === ROLES.ADMIN || role === ROLES.EDITOR;
}

/**
 * A signed-in user: skip login, enforce the role. The public chat never gets
 * here: public routes return before the session is read.
 */
function authenticatedResponse(
  request: NextRequest,
  pathname: string,
  role: string,
): NextResponse {
  if (isAuthRoute(pathname)) {
    return NextResponse.redirect(new URL(DASHBOARD_ROUTES.CHAT, request.url));
  }
  if (!roleCanOpen(pathname, role)) {
    return NextResponse.redirect(new URL("/403", request.url));
  }
  return NextResponse.next();
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (isPublicRoute(pathname) || isStaticAsset(pathname)) {
    return NextResponse.next();
  }
  const token = request.cookies.get(COOKIE_ACCESS_TOKEN)?.value;
  if (!token) {
    return anonymousResponse(request, pathname);
  }
  const payload = await verifyAccessToken(token);
  if (!payload) {
    return invalidSessionResponse(request, pathname);
  }
  return authenticatedResponse(request, pathname, payload.role);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/|ws/).*)"],
};
