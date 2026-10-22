/**
 * View-models for the public /carousels gallery and viewer.
 *
 * Keeps the pages dumb: the API's list item and public projection are reduced
 * to clean, localized cards/neighbors, with cover URLs mapped to the public
 * image route and no internal paths.
 */

import { BLOG_LANGUAGES, DEFAULT_BLOG_LANGUAGE } from "@/constants/api";
import { CAROUSEL_LANGUAGE_TAG_LENGTH } from "@/constants/carousels";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { toPublicCarouselImageUrl } from "@/lib/carousel-media-url";
import {
  resolveDisplayTitle,
  stripEmphasisMarkup,
} from "@/lib/public-blog-text";
import type { SupportedLocale } from "@/i18n/config";
import type {
  CarouselProjectListResponse,
  CarouselPublicResponse,
} from "@/schemas/carousel";

export interface PublicCarouselCard {
  id: string;
  title: string;
  coverUrl: string | null;
  createdAt: string;
  language: string;
  slideCount: number | null;
  href: string;
}

export interface PublicCarouselNeighbor {
  id: string;
  title: string;
  href: string;
}

type CarouselProjectItem = CarouselProjectListResponse["items"][number];

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function designImages(
  project: CarouselProjectItem,
): Record<string, unknown> | null {
  const tokens = project.design_tokens;
  if (!tokens || typeof tokens !== "object") return null;
  const images = (tokens as Record<string, unknown>).images;
  return images && typeof images === "object"
    ? (images as Record<string, unknown>)
    : null;
}

function listLength(value: unknown): number {
  if (!Array.isArray(value)) return 0;
  return value.filter(isNonEmptyString).length;
}

function projectCoverUrl(project: CarouselProjectItem): string | null {
  const images = designImages(project);
  if (!images) return null;
  const hero = isNonEmptyString(images.hero) ? images.hero : null;
  const firstSlide = Array.isArray(images.slides)
    ? images.slides.find(isNonEmptyString)
    : null;
  const url = hero ?? firstSlide;
  return url ? toPublicCarouselImageUrl(url) : null;
}

function projectSlideCount(project: CarouselProjectItem): number | null {
  const images = designImages(project);
  const count = images
    ? Math.max(
        listLength(images.slides),
        listLength(images.rendered_slides_pt),
        listLength(images.rendered_slides_en),
      )
    : 0;
  if (count > 0) return count;
  return project.slide_count ?? null;
}

export function carouselLanguageTag(language: string): string {
  const tag = language
    .trim()
    .slice(0, CAROUSEL_LANGUAGE_TAG_LENGTH)
    .toUpperCase();
  return tag || BLOG_LANGUAGES.PORTUGUESE.toUpperCase();
}

export function carouselTitle(
  candidates: readonly (string | null | undefined)[],
  fallbackTitle: string,
): string {
  return resolveDisplayTitle(candidates) || fallbackTitle;
}

export function carouselSubtitle(
  candidates: readonly (string | null | undefined)[],
): string | null {
  for (const candidate of candidates) {
    if (isNonEmptyString(candidate)) {
      const clean = stripEmphasisMarkup(candidate);
      if (clean) return clean;
    }
  }
  return null;
}

/** The localizable copy fields of a carousel project (list item or projection). */
export interface CarouselCopyFields {
  title: string | null;
  title_en?: string | null;
  subtitle: string | null;
  subtitle_en?: string | null;
  topic: string;
}

export interface LocalizedCarouselCopy {
  language: typeof BLOG_LANGUAGES.ENGLISH | typeof BLOG_LANGUAGES.PORTUGUESE;
  /** "" when neither language nor the topic has a real title. */
  title: string;
  subtitle: string | null;
}

/**
 * A card shows its title and subtitle in ONE language. The locale's
 * language wins when it has a real title; otherwise the card falls back to the
 * other language as a whole, never an English title over a Portuguese subtitle.
 */
export function localizedCarouselCopy(
  fields: CarouselCopyFields,
  locale: SupportedLocale,
): LocalizedCarouselCopy {
  const englishTitle = resolveDisplayTitle([fields.title_en]);
  const portugueseTitle = resolveDisplayTitle([fields.title]);
  const useEnglish =
    englishTitle !== "" &&
    (locale === BLOG_LANGUAGES.ENGLISH || portugueseTitle === "");
  if (useEnglish) {
    return {
      language: BLOG_LANGUAGES.ENGLISH,
      title: englishTitle,
      subtitle: carouselSubtitle([fields.subtitle_en]),
    };
  }
  return {
    language: BLOG_LANGUAGES.PORTUGUESE,
    title: resolveDisplayTitle([fields.title, fields.topic]),
    subtitle: carouselSubtitle([fields.subtitle]),
  };
}

export function toPublicCarouselCard(
  project: CarouselProjectItem,
  locale: SupportedLocale,
  fallbackTitle: string,
): PublicCarouselCard {
  const localizedTitles =
    locale === BLOG_LANGUAGES.ENGLISH
      ? [project.title_en, project.title, project.topic]
      : [project.title, project.title_en, project.topic];
  return {
    id: project.id,
    title: carouselTitle(localizedTitles, fallbackTitle),
    coverUrl: projectCoverUrl(project),
    createdAt: project.created_at,
    language: project.language,
    slideCount: projectSlideCount(project),
    href: PUBLIC_ROUTE_PATHS.CAROUSEL_VIEWER(project.id),
  };
}

export function buildPublicCarouselCards(
  items: CarouselProjectListResponse["items"],
  locale: SupportedLocale,
  fallbackTitle: string,
): PublicCarouselCard[] {
  return items.map((project) =>
    toPublicCarouselCard(project, locale, fallbackTitle),
  );
}

/** Viewer title: localized title, the other language's, the topic, the fallback. */
export function publicCarouselTitle(
  carousel: CarouselPublicResponse,
  locale: SupportedLocale,
  fallbackTitle: string,
): string {
  const localized =
    locale === BLOG_LANGUAGES.ENGLISH
      ? [carousel.title_en, carousel.title, carousel.topic]
      : [carousel.title, carousel.title_en, carousel.topic];
  return carouselTitle(localized, fallbackTitle);
}

export function publicCarouselSubtitle(
  carousel: CarouselPublicResponse,
  locale: SupportedLocale,
): string | null {
  return locale === BLOG_LANGUAGES.ENGLISH
    ? carouselSubtitle([carousel.subtitle_en, carousel.subtitle])
    : carouselSubtitle([carousel.subtitle, carousel.subtitle_en]);
}

export function resolveCarouselLanguage(
  carousel: CarouselPublicResponse,
  requested: string | undefined,
  locale: SupportedLocale,
): string {
  const available = carousel.available_languages;
  if (requested && available.includes(requested)) return requested;
  if (available.includes(locale)) return locale;
  return available[0] ?? DEFAULT_BLOG_LANGUAGE;
}

export interface CarouselNeighborsInput {
  items: CarouselProjectListResponse["items"];
  currentId: string;
  locale: SupportedLocale;
  fallbackTitle: string;
}

export function carouselNeighbors(input: CarouselNeighborsInput): {
  previous: PublicCarouselNeighbor | null;
  next: PublicCarouselNeighbor | null;
} {
  const { items, currentId, locale, fallbackTitle } = input;
  const index = items.findIndex((item) => item.id === currentId);
  if (index === -1) return { previous: null, next: null };
  const toNeighbor = (
    item: CarouselProjectItem | undefined,
  ): PublicCarouselNeighbor | null =>
    item
      ? {
          id: item.id,
          title: toPublicCarouselCard(item, locale, fallbackTitle).title,
          href: PUBLIC_ROUTE_PATHS.CAROUSEL_VIEWER(item.id),
        }
      : null;
  return {
    previous: toNeighbor(items[index - 1]),
    next: toNeighbor(items[index + 1]),
  };
}
