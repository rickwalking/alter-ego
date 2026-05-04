import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_ROUTES = ["/", "/blog", "/blog/", "/chat", "/chat/"];
const AUTH_ROUTES = ["/login"];
const ADMIN_ROUTES = ["/admin", "/admin/"];
const EDITOR_ROUTES = [
  "/create",
  "/create/",
  "/knowledge",
  "/knowledge/",
];
const PROTECTED_ROUTES = [
  ...EDITOR_ROUTES,
  ...ADMIN_ROUTES,
];

function isPublicRoute(pathname: string): boolean {
  if (pathname === "/") return true;
  if (pathname.startsWith("/blog/")) return true;
  if (pathname.startsWith("/blog")) return true;
  return false;
}

function isAuthRoute(pathname: string): boolean {
  return pathname === "/login" || pathname.startsWith("/login/");
}

function isAdminRoute(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

function isEditorRoute(pathname: string): boolean {
  return (
    pathname.startsWith("/create/") ||
    pathname === "/create" ||
    pathname.startsWith("/knowledge/") ||
    pathname === "/knowledge"
  );
}

function decodeJwtPayload(token: string): { role: string } | null {
  try {
    const base64 = token.split(".")[1];
    if (!base64) return null;
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as { role: string };
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("access_token")?.value;

  // Allow public routes unconditionally
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  // Allow static assets and API routes
  if (
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/api/") ||
    pathname.startsWith("/ws/") ||
    pathname === "/favicon.ico" ||
    pathname === "/robots.txt" ||
    pathname === "/sitemap.xml"
  ) {
    return NextResponse.next();
  }

  // Skip static files from the public folder
  if (/\.(svg|png|jpg|jpeg|gif|webp|ico|css|js|woff|woff2|ttf|eot)$/i.test(pathname)) {
    return NextResponse.next();
  }

  // If no token on any protected route, redirect to login
  if (!token) {
    if (isAuthRoute(pathname)) {
      return NextResponse.next();
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Token present: decode payload for role checks
  const payload = decodeJwtPayload(token);
  if (!payload) {
    // Invalid token, clear it and redirect to login
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("access_token");
    return response;
  }

  const { role } = payload;

  // Already logged in and visiting login page -> redirect to chat
  if (isAuthRoute(pathname)) {
    return NextResponse.redirect(new URL("/chat", request.url));
  }

  // Admin route checks
  if (isAdminRoute(pathname) && role !== "admin") {
    return NextResponse.redirect(new URL("/403", request.url));
  }

  // Editor route checks (admin can also access)
  if (isEditorRoute(pathname) && role !== "admin" && role !== "editor") {
    return NextResponse.redirect(new URL("/403", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/|ws/).*)"],
};
