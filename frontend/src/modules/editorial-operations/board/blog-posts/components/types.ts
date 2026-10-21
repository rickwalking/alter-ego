/**
 * Blog-post board component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { BlogPostStatus } from "@/modules/publishing";

export interface BlogPostBadgeProps {
  children: React.ReactNode;
  color: string;
}

export interface BlogPostStatusBadgeProps {
  /** `null` = unknown/drifted backend status → neutral fallback badge. */
  status: BlogPostStatus | null;
  /**
   * `false` on a `published` post means anonymous readers cannot see
   * it yet (carousel not released) — the badge says so instead of "Published".
   * Omitted = no live-state info (badge shows the stored status).
   */
  isPublic?: boolean;
}
