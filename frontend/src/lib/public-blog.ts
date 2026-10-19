import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";
import { toPublicCarouselImageUrl } from "@/lib/carousel-media-url";
import {
  emphasisHtmlToMarkdown,
  resolveDisplayTitle,
  stripEmphasisMarkup,
} from "@/lib/public-blog-text";
import { fetchCarouselDesign, fetchPublicBlogPost } from "@/lib/server-fetch";
import {
  resolveBlogLanguage,
  tryParseBlogContent,
} from "@/modules/publishing/blog/lib/parse-blog-content";
import type { BlogImage, BlogSection } from "@/schemas/blog-document";
import type { CarouselDesignResponse } from "@/schemas/carousel";
import type { PublicBlogPostResponse } from "@/schemas/public-blog-post";

/**
 * Public blog detail resolution (AE-0297, ADR-0013, AE-0423/ADR-0025).
 *
 * `/blog/{id}` renders ONLY the post's own `blog.v2` document from the public
 * blog-post API: its cover and per-section images with their stored alt. The
 * carousel is consulted for theme tokens only (colors/typography), never for
 * article text or images: there is no `fetchBlogWithDesign` / carousel `/blog`
 * read and no legacy `/blog/{project_id}` fallback, so a carousel-origin post
 * without a published v2 row is a 404. The content language (`?lang=`) picks
 * `content.translations[lang]` and falls back to the PT document.
 *
 * AE-0412: the view is sanitized for anonymous visitors — image URLs use the
 * public routes, the title carries no markup and is never a placeholder, and
 * inline emphasis HTML in a section body becomes markdown emphasis.
 */

const ORIGIN_CAROUSEL = "carousel";

export interface PublicBlogView {
  title: string;
  subtitle: string | null;
  cover: BlogImage | null;
  sections: BlogSection[];
  design: CarouselDesignResponse;
}

/** Keep a carousel design's theme tokens, never its images (ADR-0025). */
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

async function resolveTheme(
  post: PublicBlogPostResponse,
  lang: string,
): Promise<CarouselDesignResponse> {
  if (post.origin !== ORIGIN_CAROUSEL || !post.project_id) {
    return FALLBACK_DESIGN_TOKENS;
  }
  const design = await fetchCarouselDesign(post.project_id, lang);
  // A published post never 404s for missing tokens: default public theme.
  return design ? themeOnlyDesign(design) : FALLBACK_DESIGN_TOKENS;
}

function publicImage(image: BlogImage | null): BlogImage | null {
  return image ? { ...image, url: toPublicCarouselImageUrl(image.url) } : null;
}

function publicSection(section: BlogSection): BlogSection {
  return {
    ...section,
    body_md: emphasisHtmlToMarkdown(section.body_md),
    image: publicImage(section.image),
  };
}

function publicSubtitle(
  post: PublicBlogPostResponse,
  title: string,
): string | null {
  const subtitle = post.excerpt ? stripEmphasisMarkup(post.excerpt) : "";
  return subtitle && subtitle !== title ? subtitle : null;
}

export async function resolvePublicBlogView(
  id: string,
  lang: string,
): Promise<PublicBlogView | null> {
  const post = await fetchPublicBlogPost(id);
  const document = post ? tryParseBlogContent(post.content) : null;
  if (!post || !document) {
    return null;
  }
  const language = resolveBlogLanguage(document, lang);
  const title = resolveDisplayTitle([post.title]);
  return {
    title,
    subtitle: publicSubtitle(post, title),
    cover: publicImage(language.cover ?? document.cover),
    sections: language.sections.map(publicSection),
    design: await resolveTheme(post, lang),
  };
}
