import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { AUTH_LOGIN_REDIRECT_PARAM } from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import {
  isPublicRoute,
  isAuthRoute,
  isAdminRoute,
  isDashboardRoute,
  isEditorDashboardRoute,
  isLegacyEditorRoute,
  isPublicChatRoute,
  isStaticAsset,
  COOKIE_ACCESS_TOKEN,
  ROLES,
} from "@/constants/middleware";
import { clearAccessTokenCookie, verifyAccessToken } from "@/modules/identity";

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

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(COOKIE_ACCESS_TOKEN)?.value;

  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  if (isStaticAsset(pathname)) {
    return NextResponse.next();
  }

  if (!token) {
    if (isAuthRoute(pathname)) {
      return NextResponse.next();
    }
    if (isDashboardRoute(pathname) || isLegacyEditorRoute(pathname)) {
      return NextResponse.redirect(loginRedirectUrl(request, pathname));
    }
    return NextResponse.redirect(loginRedirectUrl(request, pathname));
  }

  const payload = await verifyAccessToken(token);
  if (!payload) {
    if (isAuthRoute(pathname)) {
      const response = NextResponse.next();
      clearAccessTokenCookie(response);
      return response;
    }
    return redirectWithClearedSession(request, pathname);
  }

  const { role } = payload;

  if (isAuthRoute(pathname)) {
    return NextResponse.redirect(new URL(DASHBOARD_ROUTES.CHAT, request.url));
  }

  if (isPublicChatRoute(pathname)) {
    return NextResponse.redirect(new URL(DASHBOARD_ROUTES.CHAT, request.url));
  }

  if (isAdminRoute(pathname) && role !== ROLES.ADMIN) {
    return NextResponse.redirect(new URL("/403", request.url));
  }

  if (
    (isEditorDashboardRoute(pathname) || isLegacyEditorRoute(pathname)) &&
    role !== ROLES.ADMIN &&
    role !== ROLES.EDITOR
  ) {
    return NextResponse.redirect(new URL("/403", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/|ws/).*)"],
};
