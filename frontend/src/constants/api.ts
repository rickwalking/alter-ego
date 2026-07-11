/** Client-side API base path (the Next.js BFF route prefix). */
export const API_BASE = "/api";

/** API endpoint paths. */
export const API_ENDPOINTS = {
  AUTH_LOGIN: "/api/auth/token",
  AUTH_ME: "/api/auth/me",
  AUTH_LOGOUT: "/api/auth/logout",
  AUTH_CHANGE_PASSWORD: "/api/auth/change-password",
  ADMIN_USERS: "/api/admin/users",
  ADMIN_USER_BY_ID: (id: string) => `/api/admin/users/${id}`,
  ADMIN_USER_RESET_PASSWORD: (id: string) =>
    `/api/admin/users/${id}/reset-password`,
  DOCUMENTS: "/api/documents",
  DOCUMENT_BY_ID: (id: string) => `/api/documents/${id}`,
  DOCUMENT_REPROCESS: (id: string) => `/api/documents/${id}/reprocess`,
  DOCUMENT_UPLOAD: "/api/documents/upload",
  CONVERSATIONS: "/api/conversations/",
  CONVERSATIONS_ALTER_EGO: "/api/conversations/?origin=alter_ego",
  CONVERSATION_BY_ID: (id: string) => `/api/conversations/${id}`,
  CONVERSATION_MESSAGES: (id: string) => `/api/conversations/${id}/messages`,
  CONVERSATION_CHAT: (id: string) => `/api/conversations/${id}/chat`,
  CONVERSATION_CHAT_STREAM: (id: string) =>
    `/api/conversations/${id}/chat/stream`,
  CONVERSATION_PUBLISH_CHAT_STREAM: (id: string) =>
    `/api/conversations/${id}/publish-chat/stream`,
  SEARCH: "/api/search",
  PALETTES: "/api/palettes",
  PALETTE_BY_ID: (id: string) => `/api/palettes/${id}`,
  CAROUSELS: "/api/carousels",
  CAROUSEL_BY_ID: (id: string) => `/api/carousels/${id}`,
  CAROUSEL_BLOG: (id: string) => `/api/carousels/${id}/blog`,
  CAROUSEL_PREVIEW_BLOG: (id: string, lang: string) =>
    `/api/carousels/${id}/preview/blog/${lang}`,
  CAROUSEL_PREVIEW_DESIGN: (id: string, lang: string) =>
    `/api/carousels/${id}/preview/design/${lang}`,
  CAROUSEL_PREVIEW_IMAGE: (id: string, filename: string) =>
    `/api/carousels/${id}/preview/images/${filename}`,
  CAROUSEL_BLOG_LANG: (id: string, lang: string) =>
    `/api/carousels/${id}/blog/${lang}`,
  CAROUSEL_DESIGN: (id: string, lang?: string) =>
    `/api/carousels/${id}/design${lang ? `?lang=${lang}` : ""}`,
  CAROUSEL_SLIDES: (id: string) => `/api/carousels/${id}/slides`,
  CAROUSEL_IMAGE: (id: string, filename: string) =>
    `/api/carousels/${id}/images/${filename}`,
  CAROUSEL_PDF: (id: string) => `/api/carousels/${id}/pdf`,
  CAROUSEL_PUBLISH_INSTAGRAM: (id: string) =>
    `/api/carousels/${id}/publish/instagram`,
  CAROUSEL_PUBLISH_INSTAGRAM_STATUS: (id: string) =>
    `/api/carousels/${id}/publish/instagram/status`,
  CAROUSEL_PUBLISH: (id: string) => `/api/carousels/${id}/publish`,
  CAROUSEL_REPAIR: (id: string) => `/api/carousels/${id}/repair`,
  CAROUSEL_REPUBLISH: (id: string) => `/api/carousels/${id}/republish`,
  CAROUSEL_STRATEGIES: "/api/carousels/strategies",
  CAROUSEL_STRATEGY_APPLY: (id: string) => `/api/carousels/${id}/strategy`,
  CAROUSEL_WORKFLOW_START: (id: string) =>
    `/api/carousels/${id}/workflow/start`,
  CAROUSEL_WORKFLOW_STATE: (id: string) =>
    `/api/carousels/${id}/workflow/state`,
  CAROUSEL_WORKFLOW_RESUME: (id: string) =>
    `/api/carousels/${id}/workflow/resume`,
  CAROUSEL_WORKFLOW_STREAM: (id: string) =>
    `/api/carousels/${id}/workflow/stream`,
  BLOG_POSTS: "/api/blog-posts",
  BLOG_POST_BY_ID: (id: string) => `/api/blog-posts/${id}`,
  PUBLIC_BLOG_POSTS: "/api/public/blog-posts",
  PUBLIC_BLOG_POST_BY_ID: (id: string) => `/api/public/blog-posts/${id}`,
  BLOG_POST_VERSIONS: (id: string) => `/api/blog-posts/${id}/versions`,
  BLOG_POST_AI_SUGGEST: (id: string) => `/api/blog-posts/${id}/ai-suggest`,
  BLOG_POST_AI_IMPROVE: (id: string) => `/api/blog-posts/${id}/ai-improve`,
  BLOG_POST_GENERATE_IMAGE: (id: string) =>
    `/api/blog-posts/${id}/generate-image`,
  PERSONAS: "/api/personas",
  PERSONA_VOICE_SCORE: (id: string) => `/api/personas/${id}/voice-score`,
  RUBRICS: "/api/rubrics",
  RUBRIC_EVALUATE: (id: string) => `/api/rubrics/${id}/evaluate`,
  PROJECT_SOURCES: (projectId: string) => `/api/projects/${projectId}/sources`,
  PROJECT_SOURCE_EXTRACT: (projectId: string, sourceId: string) =>
    `/api/projects/${projectId}/sources/${sourceId}/extract`,
  WORKFLOW_BOARD: "/api/workflow-board",
  NOTIFICATIONS: "/api/notifications",
  CONTENT_CALENDAR: "/api/content-calendar",
  BLOG_SCHEDULE: (id: string) => `/api/blog-posts/${id}/schedule`,
  BLOG_POST_SEO_ANALYZE: (id: string) => `/api/blog-posts/${id}/seo-analyze`,
  BLOG_POST_ACCESSIBILITY_CHECK: (id: string) =>
    `/api/blog-posts/${id}/accessibility-check`,
  BLOG_POST_PLAGIARISM_CHECK: (id: string) =>
    `/api/blog-posts/${id}/plagiarism-check`,
  BLOG_POST_AI_DISCLOSURE: (id: string) =>
    `/api/blog-posts/${id}/ai-disclosure`,
  EDITORIAL_ANALYTICS: "/api/editorial-analytics",
} as const;

/** Route paths for navigation. */
export const ROUTE_PATHS = {
  HOME: "/",
  LOGIN: "/login",
  CHAT: "/dashboard/chat",
  PUBLIC_CHAT: "/chat",
  KNOWLEDGE: "/dashboard/knowledge",
  BLOG: "/blog",
  BLOG_POST: (slug: string) => `/blog/${slug}`,
  CREATE: "/dashboard/create",
  CREATE_WORKSPACE: (id: string) => `/dashboard/create/${id}`,
  CREATE_PUBLISH: (id: string) => `/dashboard/create/${id}/publish`,
  ADMIN: "/admin",
  ADMIN_USERS: "/admin/users",
  BLOG_POSTS: "/dashboard/blog-posts",
  BLOG_POST_EDIT: (id: string) => `/dashboard/blog-posts/${id}/edit`,
} as const;

/** HTTP methods. */
export const HTTP_METHODS = {
  GET: "GET",
  POST: "POST",
  PUT: "PUT",
  PATCH: "PATCH",
  DELETE: "DELETE",
} as const;

/** Common HTTP status codes used by API clients. */
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,
  /** First redirect status; marks the exclusive upper bound of the 2xx range. */
  MULTIPLE_CHOICES: 300,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504,
} as const;

/** Content types. */
export const CONTENT_TYPES = {
  JSON: "application/json",
  FORM_DATA: "multipart/form-data",
} as const;

/** Available blog languages. */
export const BLOG_LANGUAGES = {
  PORTUGUESE: "pt",
  ENGLISH: "en",
} as const;

/** Default blog language. */
export const DEFAULT_BLOG_LANGUAGE = BLOG_LANGUAGES.PORTUGUESE;

/** Site URL used for SEO metadata and sitemap generation. */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://alterego.app";

/** Default backend URL for server-side API route proxies. */
export const DEFAULT_BACKEND_URL =
  process.env.API_BASE_URL ?? "http://localhost:8000";

/**
 * In-cluster backend URL used when running inside Docker / production and no
 * explicit `API_BASE_URL` override is provided.
 */
export const PRODUCTION_BACKEND_URL = "http://backend:8000";

/** Production Node environment name. */
const PRODUCTION_NODE_ENV = "production";

/**
 * Resolve the backend base URL for server-side API route proxies (BFF).
 *
 * Prefers an explicit `API_BASE_URL` override, then falls back to the
 * in-cluster URL in production and the default (localhost) URL in dev.
 * Centralizes the previously duplicated `resolveBackendUrl()` helpers.
 */
export function resolveBackendUrl(): string {
  return (
    process.env.API_BASE_URL ??
    (process.env.NODE_ENV === PRODUCTION_NODE_ENV
      ? PRODUCTION_BACKEND_URL
      : DEFAULT_BACKEND_URL)
  );
}
