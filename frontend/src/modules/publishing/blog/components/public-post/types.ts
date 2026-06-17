/**
 * Public blog-post component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { CarouselDesignResponse } from "@/schemas/carousel";

export interface BlogPostAdminPanelProps {
  projectId: string;
  design: CarouselDesignResponse;
}

export interface BlogPostContentProps {
  markdown: string;
  design: CarouselDesignResponse;
  slideImages: string[];
}

export interface SectionProps {
  markdown: string;
  design: CarouselDesignResponse;
  slideImage: string | null;
}

export interface BlogPostHeaderProps {
  title: string;
  subtitle?: string;
  badge: string;
  design: CarouselDesignResponse;
}

export interface BlogPostHeroProps {
  imageUrl: string;
  title: string;
  design: CarouselDesignResponse;
}
