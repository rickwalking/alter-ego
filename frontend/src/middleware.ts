import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  isPublicRoute,
  isAuthRoute,
  isAdminRoute,
  isEditorRoute,
  isStaticAsset,
  decodeJwtPayload,
  COOKIE_ACCESS_TOKEN,
  ROLES,
} from "@/constants/middleware";

export function middleware(request: NextRequest) {
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
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const payload = decodeJwtPayload(token);
  if (!payload) {
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete(COOKIE_ACCESS_TOKEN);
    return response;
  }

  const { role } = payload;

  if (isAuthRoute(pathname)) {
    return NextResponse.redirect(new URL("/chat", request.url));
  }

  if (isAdminRoute(pathname) && role !== ROLES.ADMIN) {
    return NextResponse.redirect(new URL("/403", request.url));
  }

  if (
    isEditorRoute(pathname) &&
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
