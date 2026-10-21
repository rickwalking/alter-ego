import { cache } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { MarketingSectionEyebrow } from "@/app/(public)/(marketing)/marketing-section-eyebrow";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { BLOG_LANGUAGES, SITE_URL } from "@/constants/api";
import { BG_DEEP, TEXT, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { getRequestLocale } from "@/i18n/request-locale";
import type { SupportedLocale } from "@/i18n/config";
import { formatPublicDate } from "@/lib/public-blog-text";
import {
  carouselLanguageTag,
  carouselNeighbors,
  publicCarouselSubtitle,
  publicCarouselTitle,
  resolveCarouselLanguage,
} from "@/lib/public-carousels";
import { fetchPublicCarousel, fetchPublicCarousels } from "@/lib/server-fetch";
import { CarouselBackLink } from "../carousel-back-link";
import { CarouselPageBackground } from "../carousel-page-background";
import { CarouselLanguageSwitch } from "./carousel-language-switch";
import { CarouselNeighbors } from "./carousel-neighbors";
import { CarouselViewer } from "./carousel-viewer";

export const dynamic = "force-dynamic";

const CAROUSEL_VIEW_MAX_WIDTH_PX = 1100;
const META_TITLE_SEPARATOR = " · ";
const META_DESCRIPTION_MAX_CHARS = 160;
const NEIGHBOR_FEED_LIMIT = 100;

interface CarouselViewerPageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ lang?: string }>;
}

const loadCarousel = cache(fetchPublicCarousel);

function contentLocale(language: string): SupportedLocale {
  return language === BLOG_LANGUAGES.ENGLISH ? "en" : "pt";
}

function truncateDescription(text: string): string {
  if (text.length <= META_DESCRIPTION_MAX_CHARS) return text;
  return `${text.slice(0, META_DESCRIPTION_MAX_CHARS - 1).trimEnd()}…`;
}

function absoluteCoverUrl(coverUrl: string | null): string | undefined {
  return coverUrl ? new URL(coverUrl, SITE_URL).toString() : undefined;
}

export async function generateMetadata({
  params,
  searchParams,
}: CarouselViewerPageProps): Promise<Metadata> {
  const { id } = await params;
  const { lang } = await searchParams;
  const carousel = await loadCarousel(id);
  if (!carousel) return {};

  const locale = await getRequestLocale();
  const language = resolveCarouselLanguage(carousel, lang, locale);
  const t = await getTranslations("carousels");
  const title = publicCarouselTitle(
    carousel,
    contentLocale(language),
    t("untitledCarousel"),
  );
  const subtitle = publicCarouselSubtitle(carousel, contentLocale(language));
  const description = subtitle
    ? truncateDescription(subtitle)
    : t("metaDescription");
  const image = absoluteCoverUrl(carousel.cover_url);
  const metaTitle = `${title}${META_TITLE_SEPARATOR}${t("metaTitleSuffix")}`;

  return {
    title: metaTitle,
    description,
    openGraph: {
      title: metaTitle,
      description,
      type: "article",
      images: image ? [image] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: metaTitle,
      description,
      images: image ? [image] : undefined,
    },
  };
}

export default async function PublicCarouselViewerPage({
  params,
  searchParams,
}: CarouselViewerPageProps): Promise<React.ReactElement> {
  const { id } = await params;
  const { lang } = await searchParams;
  const carousel = await loadCarousel(id);
  if (!carousel) notFound();

  const t = await getTranslations("carousels");
  const locale = await getRequestLocale();
  const language = resolveCarouselLanguage(carousel, lang, locale);
  const localized = contentLocale(language);
  const title = publicCarouselTitle(carousel, localized, t("untitledCarousel"));
  const subtitle = publicCarouselSubtitle(carousel, localized);
  const slides = carousel.slides_by_language[language] ?? [];
  if (slides.length === 0) notFound();

  const feed = await fetchPublicCarousels(NEIGHBOR_FEED_LIMIT, 0);
  const neighbors = carouselNeighbors({
    items: feed.items,
    currentId: id,
    locale: localized,
    fallbackTitle: t("untitledCarousel"),
  });
  const date = formatPublicDate(carousel.created_at, locale);
  const languageOptions = carousel.available_languages.map((option) => ({
    language: option,
    label:
      option === BLOG_LANGUAGES.ENGLISH
        ? t("contentLanguageEn")
        : t("contentLanguagePt"),
    href: `?lang=${option}`,
  }));

  return (
    <div
      className="relative min-h-screen overflow-hidden"
      style={{ background: BG_DEEP }}
    >
      <CarouselPageBackground />

      <div
        className="relative z-10 mx-auto px-4 py-12 sm:px-6"
        style={{ maxWidth: `${CAROUSEL_VIEW_MAX_WIDTH_PX}px` }}
      >
        <CarouselBackLink
          href={PUBLIC_ROUTE_PATHS.CAROUSELS}
          label={t("backToCarousels")}
        />

        <header className="mx-auto max-w-3xl text-center">
          <MarketingSectionEyebrow label={t("viewerEyebrow")} />
          <h1
            className="text-3xl font-extrabold tracking-tight sm:text-5xl"
            style={{ color: TEXT, letterSpacing: "-0.03em" }}
          >
            {title}
          </h1>
          {subtitle ? (
            <p className="mt-4 text-lg" style={{ color: TEXT_MUTED }}>
              {subtitle}
            </p>
          ) : null}
          <div
            className="mt-5 flex flex-wrap items-center justify-center gap-3 text-xs"
            style={{ color: TEXT_DIM }}
          >
            <NeonBadge size="sm" variant="cyan">
              {carouselLanguageTag(language)}
            </NeonBadge>
            <span>{t("slideCount", { count: carousel.slide_count })}</span>
            {date ? (
              <>
                <span aria-hidden="true">·</span>
                <time dateTime={carousel.created_at}>{date}</time>
              </>
            ) : null}
          </div>
          {languageOptions.length > 1 ? (
            <CarouselLanguageSwitch
              activeLanguage={language}
              label={t("contentLanguage")}
              options={languageOptions}
            />
          ) : null}
        </header>

        <CarouselViewer key={language} title={title} slides={slides} />

        <CarouselNeighbors
          previous={neighbors.previous}
          next={neighbors.next}
          previousLabel={t("previousCarousel")}
          nextLabel={t("nextCarousel")}
          listLabel={t("carouselList")}
          listHref={PUBLIC_ROUTE_PATHS.CAROUSELS}
        />
      </div>
    </div>
  );
}
