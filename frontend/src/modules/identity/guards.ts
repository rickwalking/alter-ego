/**
 * `identity` — route-level auth guard surface (AE-0164).
 *
 * The role constants, route-classification predicates, the access-token cookie
 * name, and the static-asset matcher that the Next.js `middleware` and the admin
 * route group use to gate access. Relocated from `constants/middleware.ts` in a
 * behavior-preserving pass so the identity context owns the full auth contract
 * (the client lib from AE-0156 + these route-level guards). A thin re-export
 * shim remains at `@/constants/middleware` so existing imports keep resolving.
 *
 * App Router URLs, redirects, and cookie/JWT semantics are unchanged.
 */

import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";

export const ROLES = {
  ADMIN: "admin",
  EDITOR: "editor",
} as const;

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
