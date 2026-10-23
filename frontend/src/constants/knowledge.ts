/** The scopes an owner can give a knowledge document. */
export const DOCUMENT_SCOPE = {
  PERSONAL: "personal",
  PUBLIC: "public",
} as const;

/** A scope an owner can choose (`personal` or `public`). */
export type DocumentScopeChoice =
  (typeof DOCUMENT_SCOPE)[keyof typeof DOCUMENT_SCOPE];

/** The scope filter value that lists every document. */
export const SCOPE_FILTER_ALL = "all";

/** A value of the Knowledge Base scope filter. */
export type ScopeFilterValue = DocumentScopeChoice | typeof SCOPE_FILTER_ALL;

/** The scope filter options, in display order. */
export const SCOPE_FILTER_OPTIONS: readonly ScopeFilterValue[] = [
  SCOPE_FILTER_ALL,
  DOCUMENT_SCOPE.PERSONAL,
  DOCUMENT_SCOPE.PUBLIC,
];
