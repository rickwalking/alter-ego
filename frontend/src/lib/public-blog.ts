import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";
import { fetchBlogWithDesign, fetchPublicBlogPost } from "@/lib/server-fetch";
import type { CarouselDesignResponse } from "@/schemas/carousel";
import type { PublicBlogPostResponse } from "@/schemas/public-blog-post";

/**
 * Public blog detail resolution (AE-0297, ADR-0013).
 *
 * Single canonical URL `/blog/{id}` branched by provenance:
 * 1. `id` resolves on the public blog-post API → carousel-origin posts enrich
 *    through their project's design tokens; standalone posts render with the
 *    default public theme (never 404 for missing tokens).
 * 2. Otherwise `id` is treated as a legacy carousel project id (today's URLs)
 *    and rendered through the existing carousel projection path.
 */

const ORIGIN_CAROUSEL = "carousel";

export interface PublicBlogView {
  title: string;
  subtitle: string | null;
  markdown: string;
  design: CarouselDesignResponse;
}

function extractMarkdown(
  content: Record<string, unknown>,
  lang: string,
): string {
  const translations = content.translations;
  if (translations && typeof translations === "object") {
    const localized = (translations as Record<string, unknown>)[lang];
    if (typeof localized === "string" && localized.length > 0) {
      return localized;
    }
  }
  if (typeof content.markdown === "string") {
    return content.markdown;
  }
  if (typeof content.body === "string") {
    return content.body;
  }
  return "";
}

function fromCarousel(data: {
  blog: { title: string; subtitle?: string | null; markdown: string };
  design: CarouselDesignResponse;
}): PublicBlogView {
  return {
    title: data.blog.title,
    subtitle: data.blog.subtitle ?? null,
    markdown: data.blog.markdown,
    design: data.design,
  };
}

function fromStandalone(
  post: PublicBlogPostResponse,
  lang: string,
): PublicBlogView {
  return {
    title: post.title,
    subtitle: post.excerpt ?? null,
    markdown: extractMarkdown(post.content, lang),
    design: {
      ...FALLBACK_DESIGN_TOKENS,
      images: {
        ...FALLBACK_DESIGN_TOKENS.images,
        hero: post.featured_image_url ?? "",
      },
    },
  };
}

export async function resolvePublicBlogView(
  id: string,
  lang: string,
): Promise<PublicBlogView | null> {
  const post = await fetchPublicBlogPost(id);
  if (post) {
    if (post.origin === ORIGIN_CAROUSEL && post.project_id) {
      const enriched = await fetchBlogWithDesign(post.project_id, lang);
      if (enriched) {
        return fromCarousel(enriched);
      }
    }
    // Default public theme — a published post must never 404 for missing
    // design tokens (fail toward a plain render, not toward not-found).
    return fromStandalone(post, lang);
  }
  // Legacy carousel-projection URL (`/blog/{project_id}`).
  const legacy = await fetchBlogWithDesign(id, lang);
  return legacy ? fromCarousel(legacy) : null;
}
