/**
 * Card view-models for the public /blog listing (AE-0297, AE-0412).
 *
 * The listing prefers the public blog-posts feed (published-only, includes
 * standalone posts); carousel-origin entries are enriched with their project's
 * localized copy + hero. On public-feed failure it falls open to the carousel
 * feed. AE-0412: hero URLs go through the public image route (never the
 * owner-only preview route), titles are clean and never a placeholder, and
 * only a short niche becomes the category chip.
 */

import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { toPublicCarouselImageUrl } from "@/lib/carousel-media-url";
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

function projectTitle(
  project: CarouselProjectItem,
  locale: SupportedLocale,
): string {
  const localized =
    locale === "en"
      ? [project.title_en, project.title]
      : [project.title, project.title_en];
  return resolveDisplayTitle([...localized, project.topic]);
}

function projectHero(project: CarouselProjectItem): string | undefined {
  const tokens = project.design_tokens as
    | { images?: { hero?: string } }
    | null
    | undefined;
  const hero = tokens?.images?.hero;
  return hero ? toPublicCarouselImageUrl(hero) : undefined;
}

function projectToCard(
  project: CarouselProjectItem,
  locale: SupportedLocale,
  fallbackTitle?: string,
): NeonBlogPostCardProps {
  const title = projectTitle(project, locale) || fallbackTitle || "";
  const rawSubtitle =
    locale === "en"
      ? project.subtitle_en || project.subtitle
      : project.subtitle;
  return {
    id: project.id,
    title,
    subtitle: cardSubtitle(rawSubtitle, title),
    niche: toCategoryLabel(project.niche),
    imageUrl: projectHero(project),
    createdAt: project.created_at,
    href: postHref(project.id),
  };
}

function publicPostToCard(post: PublicBlogPostSummary): NeonBlogPostCardProps {
  const title = resolveDisplayTitle([post.title]);
  return {
    id: post.id,
    title,
    subtitle: cardSubtitle(post.excerpt ?? post.meta_description, title),
    imageUrl: post.featured_image_url
      ? toPublicCarouselImageUrl(post.featured_image_url)
      : undefined,
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
  if (!publicFeed) {
    return carouselFeed.items.map((project) => projectToCard(project, locale));
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
      href: postHref(post.id),
    };
  });
}
