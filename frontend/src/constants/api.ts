/** API endpoint paths. */
export const API_ENDPOINTS = {
  DOCUMENTS: "/api/documents",
  DOCUMENT_UPLOAD: "/api/documents/upload",
  CONVERSATIONS: "/api/conversations",
  SEARCH: "/api/search",
} as const;

/** Route paths for navigation. */
export const ROUTE_PATHS = {
  HOME: "/",
  CHAT: "/chat",
  KNOWLEDGE: "/knowledge",
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
