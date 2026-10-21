/**
 * Card view-models for the public /blog listing (AE-0297, AE-0412).
 *
 * The listing is the public blog-posts feed (published-only, includes
 * standalone posts); carousel-origin entries are enriched with their project's
 * localized copy, while the image is always the post's own cover (AE-0423).
 * On public-feed failure the listing is empty (no dead project-id links). AE-0412: hero URLs go through the public image route (never the
 * owner-only preview route), titles are clean and never a placeholder, and
 * only a short niche becomes the category chip.
 */

import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { toPublicCarouselImageUrl } from "@/lib/carousel-media-url";
import { localizedCarouselCopy } from "@/lib/public-carousels";
import {
  resolveDisplayTitle,
  stripEmphasisMarkup,
  toCategoryLabel,
} from "@/lib/public-blog-text";
import type { SupportedLocale } from "@/i18n/config";
import type { CarouselProjectListResponse } from "@/schemas/carousel";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";
import type { PublicBlogPostSummary } from "@/schemas/public-blog-post";

const SUBTITLE_MAX_WORDS = 15;
const TRUNCATION_SUFFIX = "...";

function postHref(id: string): string {
  return `${PUBLIC_ROUTE_PATHS.BLOG}/${id}`;
}

type CarouselProjectItem = CarouselProjectListResponse["items"][number];

function truncateWords(text: string, maxWords: number): string {
  const words = stripEmphasisMarkup(text)
    .split(" ")
    .filter((w) => w.length > 0);
  if (words.length <= maxWords) return words.join(" ");
  return words.slice(0, maxWords).join(" ") + TRUNCATION_SUFFIX;
}

/** Truncated subtitle, or undefined when empty or a repeat of the title. */
function cardSubtitle(
  source: string | null | undefined,
  title: string,
): string | undefined {
  const subtitle = truncateWords(source ?? "", SUBTITLE_MAX_WORDS);
  if (!subtitle || subtitle.toLowerCase() === title.toLowerCase()) {
    return undefined;
  }
  return subtitle;
}

function projectToCard(
  project: CarouselProjectItem,
  locale: SupportedLocale,
  fallbackTitle?: string,
): NeonBlogPostCardProps {
  // AE-0446: title and subtitle come from ONE language, never mixed.
  const copy = localizedCarouselCopy(project, locale);
  const title = copy.title || (fallbackTitle ?? "");
  const rawSubtitle = copy.subtitle;
  return {
    id: project.id,
    title,
    subtitle: cardSubtitle(rawSubtitle, title),
    niche: toCategoryLabel(project.niche),
    createdAt: project.created_at,
    href: postHref(project.id),
  };
}

/**
 * The card image is the post's own cover projection (`featured_image_url`,
 * AE-0423). A null cover leaves the card text-only (deterministic neutral
 * fallback) — never the carousel hero or a slide.
 */
function postCoverUrl(post: PublicBlogPostSummary): string | undefined {
  return post.featured_image_url
    ? toPublicCarouselImageUrl(post.featured_image_url)
    : undefined;
}

function publicPostToCard(post: PublicBlogPostSummary): NeonBlogPostCardProps {
  const title = resolveDisplayTitle([post.title]);
  return {
    id: post.id,
    title,
    subtitle: cardSubtitle(post.excerpt ?? post.meta_description, title),
    imageUrl: postCoverUrl(post),
    createdAt: post.published_at ?? "",
    href: postHref(post.id),
  };
}

export interface PublicBlogCardSources {
  publicFeed: { items: PublicBlogPostSummary[] } | null;
  carouselFeed: CarouselProjectListResponse;
  locale: SupportedLocale;
}

export function buildPublicBlogCards({
  publicFeed,
  carouselFeed,
  locale,
}: PublicBlogCardSources): NeonBlogPostCardProps[] {
  // AE-0423: the public blog-post feed is the only listing source. A carousel
  // project id is no longer a readable blog URL (no legacy `/blog/{project_id}`
  // fallback), so an unavailable feed renders no cards instead of dead links.
  if (!publicFeed) {
    return [];
  }
  const byProject = new Map(
    carouselFeed.items.map((project) => [project.id, project]),
  );
  return publicFeed.items.map((post) => {
    const project = post.project_id
      ? byProject.get(post.project_id)
      : undefined;
    if (!project) {
      return publicPostToCard(post);
    }
    const fallbackTitle = resolveDisplayTitle([post.title]);
    return {
      ...projectToCard(project, locale, fallbackTitle),
      id: post.id,
      imageUrl: postCoverUrl(post),
      href: postHref(post.id),
    };
  });
}
