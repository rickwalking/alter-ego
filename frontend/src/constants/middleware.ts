export const ROLES = {
  ADMIN: "admin",
  EDITOR: "editor",
} as const;

export const PUBLIC_ROUTES = ["/", "/blog", "/blog/"];

export function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some((route) =>
    route.endsWith("/") ? pathname.startsWith(route) : pathname === route,
  );
}

export function isAuthRoute(pathname: string): boolean {
  return pathname === "/login" || pathname.startsWith("/login/");
}

export function isAdminRoute(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

export function isEditorRoute(pathname: string): boolean {
  return (
    pathname.startsWith("/create/") ||
    pathname === "/create" ||
    pathname.startsWith("/knowledge/") ||
    pathname === "/knowledge"
  );
}

export const COOKIE_ACCESS_TOKEN = "access_token";

export const STATIC_FILE_PATTERN = /\.(svg|png|jpg|jpeg|gif|webp|ico|css|js|woff|woff2|ttf|eot)$/i;

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

export function decodeJwtPayload(token: string): { role: string } | null {
  try {
    const base64 = token.split(".")[1];
    if (!base64) return null;
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as { role: string };
  } catch {
    return null;
  }
}
