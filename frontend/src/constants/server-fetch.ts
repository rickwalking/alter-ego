/** Constants for server-side data fetching (server-fetch helpers). */

const SECONDS_PER_HOUR = 3600;

export const SERVER_FETCH = {
  /** Default page size for public project listings. */
  DEFAULT_PROJECT_LIMIT: 20,
  /** ISR revalidation window (seconds) for combined blog+design fetches. */
  BLOG_REVALIDATE_SECONDS: SECONDS_PER_HOUR,
} as const;
