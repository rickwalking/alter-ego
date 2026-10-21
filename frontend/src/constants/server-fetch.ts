/** Constants for server-side data fetching (server-fetch helpers). */

export const SERVER_FETCH = {
  /** Default page size for public project listings. */
  DEFAULT_PROJECT_LIMIT: 20,
  /** Only finished projects are shown publicly (AE-0443). */
  COMPLETED_STATUS: "completed",
  /** Public carousel gallery page size (AE-0444). */
  PUBLIC_CAROUSEL_PAGE_SIZE: 12,
} as const;
