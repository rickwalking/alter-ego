/** API endpoint paths. */
export const API_ENDPOINTS = {
  AUTH_LOGIN: "/api/auth/token",
  AUTH_ME: "/api/auth/me",
  AUTH_CHANGE_PASSWORD: "/api/auth/change-password",
  ADMIN_USERS: "/api/admin/users",
  ADMIN_USER_BY_ID: (id: string) => `/api/admin/users/${id}`,
  ADMIN_USER_RESET_PASSWORD: (id: string) => `/api/admin/users/${id}/reset-password`,
  DOCUMENTS: "/api/documents",
  DOCUMENT_BY_ID: (id: string) => `/api/documents/${id}`,
  DOCUMENT_REPROCESS: (id: string) => `/api/documents/${id}/reprocess`,
  DOCUMENT_UPLOAD: "/api/documents/upload",
  CONVERSATIONS: "/api/conversations",
  CONVERSATION_BY_ID: (id: string) => `/api/conversations/${id}`,
  CONVERSATION_MESSAGES: (id: string) => `/api/conversations/${id}/messages`,
  CONVERSATION_CHAT: (id: string) => `/api/conversations/${id}/chat`,
  SEARCH: "/api/search",
  CAROUSELS: "/api/carousels",
  CAROUSEL_BY_ID: (id: string) => `/api/carousels/${id}`,
  CAROUSEL_GENERATE: (id: string) => `/api/carousels/${id}/generate`,
  CAROUSEL_RESUME: (id: string) => `/api/carousels/${id}/resume`,
  CAROUSEL_STREAM: (id: string) => `/api/carousels/${id}/stream`,
  CAROUSEL_STATUS: (id: string) => `/api/carousels/${id}/status`,
  CAROUSEL_BLOG: (id: string) => `/api/carousels/${id}/blog`,
  CAROUSEL_BLOG_LANG: (id: string, lang: string) => `/api/carousels/${id}/blog/${lang}`,
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
} as const;

/** Route paths for navigation. */
export const ROUTE_PATHS = {
  HOME: "/",
  LOGIN: "/login",
  CHAT: "/chat",
  KNOWLEDGE: "/knowledge",
  BLOG: "/blog",
  BLOG_POST: (slug: string) => `/blog/${slug}`,
  CREATE: "/create",
  CREATE_WORKSPACE: (id: string) => `/create/${id}`,
  CREATE_PUBLISH: (id: string) => `/create/${id}/publish`,
  ADMIN: "/admin",
  ADMIN_USERS: "/admin/users",
} as const;

/** HTTP methods. */
export const HTTP_METHODS = {
  GET: "GET",
  POST: "POST",
  PUT: "PUT",
  DELETE: "DELETE",
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
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://alterego.app";
