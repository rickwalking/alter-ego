/** API endpoint paths. */
export const API_ENDPOINTS = {
  DOCUMENTS: "/api/documents",
  DOCUMENT_UPLOAD: "/api/documents/upload",
  CONVERSATIONS: "/api/conversations",
  SEARCH: "/api/search",
  CAROUSELS: "/api/carousels",
  CAROUSEL_GENERATE: (id: string) => `/api/carousels/${id}/generate`,
  CAROUSEL_STATUS: (id: string) => `/api/carousels/${id}/status`,
  CAROUSEL_BLOG: (id: string) => `/api/carousels/${id}/blog`,
  CAROUSEL_BLOG_LANG: (id: string, lang: string) => `/api/carousels/${id}/blog/${lang}`,
  CAROUSEL_DESIGN: (id: string) => `/api/carousels/${id}/design`,
  CAROUSEL_SLIDES: (id: string) => `/api/carousels/${id}/slides`,
  CAROUSEL_IMAGE: (id: string, filename: string) =>
    `/api/carousels/${id}/images/${filename}`,
} as const;

/** Route paths for navigation. */
export const ROUTE_PATHS = {
  HOME: "/",
  CHAT: "/chat",
  KNOWLEDGE: "/knowledge",
  BLOG: "/blog",
  BLOG_POST: (slug: string) => `/blog/${slug}`,
  CREATE: "/create",
  CREATE_WORKSPACE: (id: string) => `/create/${id}`,
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
