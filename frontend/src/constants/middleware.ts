export const ROLES = {
  ADMIN: "admin",
  EDITOR: "editor",
} as const;

import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";

export const PUBLIC_ROUTES = [
  PUBLIC_ROUTE_PATHS.HOME,
  PUBLIC_ROUTE_PATHS.BLOG,
  `${PUBLIC_ROUTE_PATHS.BLOG}/`,
  PUBLIC_ROUTE_PATHS.CHAT,
];

export function isPublicRoute(pathname: string): boolean {
  if (pathname === PUBLIC_ROUTE_PATHS.HOME) {
    return true;
  }
  if (pathname === PUBLIC_ROUTE_PATHS.CHAT) {
    return true;
  }
  if (
    pathname === PUBLIC_ROUTE_PATHS.BLOG ||
    pathname.startsWith(`${PUBLIC_ROUTE_PATHS.BLOG}/`)
  ) {
    return true;
  }
  return false;
}

export function isPublicChatRoute(pathname: string): boolean {
  return pathname === PUBLIC_ROUTE_PATHS.CHAT;
}

export function isAuthRoute(pathname: string): boolean {
  return pathname === "/login" || pathname.startsWith("/login/");
}

export function isAdminRoute(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

export function isDashboardRoute(pathname: string): boolean {
  return pathname === "/dashboard" || pathname.startsWith("/dashboard/");
}

/** Legacy editor paths that redirect into the dashboard shell. */
export function isLegacyEditorRoute(pathname: string): boolean {
  return (
    pathname.startsWith("/create/") ||
    pathname === "/create" ||
    pathname.startsWith("/knowledge/") ||
    pathname === "/knowledge" ||
    pathname.startsWith("/personas") ||
    pathname.startsWith("/rubrics") ||
    pathname.startsWith("/blog-posts") ||
    pathname.startsWith("/workflow") ||
    pathname.startsWith("/calendar") ||
    pathname.startsWith("/analytics")
  );
}

/** Dashboard paths that require editor or admin (not plain authenticated users). */
export function isEditorDashboardRoute(pathname: string): boolean {
  if (!isDashboardRoute(pathname)) {
    return false;
  }
  if (
    pathname === DASHBOARD_ROUTES.CHAT ||
    pathname === DASHBOARD_ROUTES.HOME
  ) {
    return false;
  }
  return true;
}

/** @deprecated Use isEditorDashboardRoute or isLegacyEditorRoute */
export function isEditorRoute(pathname: string): boolean {
  return isLegacyEditorRoute(pathname) || isEditorDashboardRoute(pathname);
}

export const COOKIE_ACCESS_TOKEN = "access_token";

export const STATIC_FILE_PATTERN =
  /\.(svg|png|jpg|jpeg|gif|webp|ico|css|js|woff|woff2|ttf|eot)$/i;

export function isStaticAsset(pathname: string): boolean {
  return (
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/api/") ||
    pathname === "/favicon.ico" ||
    pathname === "/robots.txt" ||
    pathname === "/sitemap.xml" ||
    STATIC_FILE_PATTERN.test(pathname)
  );
}

/** @deprecated Use verifyAccessToken from @/lib/jwt-auth in middleware. */
export function decodeJwtPayload(token: string): { role: string } | null {
  try {
    const segment = token.split(".")[1];
    if (!segment) return null;
    const padded = segment.replace(/-/g, "+").replace(/_/g, "/");
    const remainder = padded.length % 4;
    const base64 =
      remainder === 0 ? padded : padded + "=".repeat(4 - remainder);
    const json = atob(base64);
    const payload = JSON.parse(json) as { role: string; exp?: number };
    if (typeof payload.exp === "number" && payload.exp * 1000 <= Date.now()) {
      return null;
    }
    return payload;
  } catch {
    return null;
  }
}
