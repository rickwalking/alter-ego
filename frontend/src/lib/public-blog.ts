import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";
import { toPublicCarouselImageUrl } from "@/lib/carousel-media-url";
import {
  emphasisHtmlToMarkdown,
  resolveDisplayTitle,
  stripEmphasisMarkup,
} from "@/lib/public-blog-text";
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
 *
 * AE-0412: every view is sanitized for anonymous visitors — image URLs use the
 * public routes (never the owner-only preview route), the title carries no
 * markup and is never a placeholder ("" when no real title exists), and inline
 * emphasis HTML in the body becomes markdown emphasis.
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

function publicDesign(design: CarouselDesignResponse): CarouselDesignResponse {
  const { hero, slides } = design.images;
  return {
    ...design,
    images: {
      ...design.images,
      hero: hero ? toPublicCarouselImageUrl(hero) : hero,
      slides: slides.map(toPublicCarouselImageUrl),
    },
  };
}

function sanitizeView(
  view: PublicBlogView,
  fallbackTitles: ReadonlyArray<string | null | undefined>,
): PublicBlogView {
  const title = resolveDisplayTitle([view.title, ...fallbackTitles]);
  const subtitle = view.subtitle ? stripEmphasisMarkup(view.subtitle) : "";
  return {
    title,
    subtitle: subtitle && subtitle !== title ? subtitle : null,
    markdown: emphasisHtmlToMarkdown(view.markdown),
    design: publicDesign(view.design),
  };
}

/**
 * Drop a carousel design's images, keeping only its theme tokens (ADR-0025).
 *
 * A carousel design's `images` are rendered Instagram slides (`/slide-images/…`,
 * baked-in text, empty alt); they are never blog artwork, so the public blog
 * page must not read them (AE-0422). The post's own cover/section images arrive
 * with `blog.v2` in AE-0423.
 */
function themeOnlyDesign(
  design: CarouselDesignResponse,
): CarouselDesignResponse {
  return {
    ...design,
    images: {
      hero: "",
      slides: [],
      rendered_slides_pt: null,
      rendered_slides_en: null,
      blog_image_map: null,
    },
  };
}

function fromCarousel(data: {
  blog: { title: string; subtitle?: string | null; markdown: string };
  design: CarouselDesignResponse;
}): PublicBlogView {
  return {
    title: data.blog.title,
    subtitle: data.blog.subtitle ?? null,
    markdown: data.blog.markdown,
    design: themeOnlyDesign(data.design),
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

async function resolveRawView(
  id: string,
  lang: string,
): Promise<{ view: PublicBlogView; fallbackTitle?: string } | null> {
  const post = await fetchPublicBlogPost(id);
  if (post) {
    if (post.origin === ORIGIN_CAROUSEL && post.project_id) {
      const enriched = await fetchBlogWithDesign(post.project_id, lang);
      if (enriched) {
        return { view: fromCarousel(enriched), fallbackTitle: post.title };
      }
    }
    // Default public theme — a published post must never 404 for missing
    // design tokens (fail toward a plain render, not toward not-found).
    return { view: fromStandalone(post, lang) };
  }
  // Legacy carousel-projection URL (`/blog/{project_id}`).
  const legacy = await fetchBlogWithDesign(id, lang);
  return legacy ? { view: fromCarousel(legacy) } : null;
}

export async function resolvePublicBlogView(
  id: string,
  lang: string,
): Promise<PublicBlogView | null> {
  const resolved = await resolveRawView(id, lang);
  if (!resolved) {
    return null;
  }
  return sanitizeView(resolved.view, [resolved.fallbackTitle]);
}
