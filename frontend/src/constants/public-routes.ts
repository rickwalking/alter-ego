/** Public App Router paths (no authentication required). */
export const PUBLIC_ROUTE_PATHS = {
  HOME: "/",
  BLOG: "/blog",
  CAROUSELS: "/carousels",
  CAROUSEL_VIEWER: (id: string) => `/carousels/${id}`,
  CHAT: "/chat",
  LOGIN: "/login",
  /**
   * Session-expired logout handler. Must NOT live under `/api`: nginx proxies
   * every `/api/*` request to FastAPI, so a Next route there never runs in prod
   *.
   */
  LOGOUT: "/auth/logout",
} as const;
