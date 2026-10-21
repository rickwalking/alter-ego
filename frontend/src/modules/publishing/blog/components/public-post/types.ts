/**
 * Public blog-post component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { CSSProperties, ReactNode } from "react";
import type { BlogImage, BlogSection } from "@/schemas/blog-document";
import type { CarouselDesignResponse } from "@/schemas/carousel";

export interface BlogPostContentProps {
  sections: BlogSection[];
  design: CarouselDesignResponse;
}

export interface SectionProps {
  heading: string | null;
  bodyMd: string;
  image?: BlogImage | null;
  design: CarouselDesignResponse;
}

export interface SectionHeadingProps {
  heading: string | null;
  design: CarouselDesignResponse;
}

export interface SectionBodyProps {
  markdown: string;
  design: CarouselDesignResponse;
}

export interface BlogPostHeaderProps {
  title: string;
  subtitle?: string;
  badge?: string;
  swipeHint: string;
  design: CarouselDesignResponse;
}

export interface BlogPostHeroProps {
  cover: BlogImage | null;
  design: CarouselDesignResponse;
}

export interface BlogLanguageSwitchProps {
  activeLanguage: string;
  label: string;
  options: readonly { language: string; label: string; href: string }[];
}

export interface PublicCoverImageProps {
  src: string;
  alt: string;
  sizes: string;
  frameClassName?: string;
  frameStyle?: CSSProperties;
  overlay?: ReactNode;
}
