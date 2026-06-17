/**
 * Blog listing component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";

export interface NeonBlogPostCardComponentProps extends NeonBlogPostCardProps {
  featured?: boolean;
}
