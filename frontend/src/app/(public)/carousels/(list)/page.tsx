import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { MarketingSectionEyebrow } from "@/app/(public)/(marketing)/marketing-section-eyebrow";
import { BG_DEEP, TEXT, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { SERVER_FETCH } from "@/constants/server-fetch";
import { getRequestLocale } from "@/i18n/request-locale";
import { fetchPublicCarousels } from "@/lib/server-fetch";
import { buildPublicCarouselCards } from "@/lib/public-carousels";
import { CarouselBackLink } from "@/app/(public)/carousels/carousel-back-link";
import { CarouselCard } from "@/app/(public)/carousels/carousel-card";
import { CarouselEmptyState } from "@/app/(public)/carousels/carousel-empty-state";
import { CarouselPageBackground } from "@/app/(public)/carousels/carousel-page-background";
import { CarouselPagination } from "@/app/(public)/carousels/carousel-pagination";

export const dynamic = "force-dynamic";

const CAROUSEL_PAGE_MAX_WIDTH_PX = 1200;
const PAGE_NUMBER_PATTERN = /^\d+$/;

interface CarouselsPageProps {
  searchParams: Promise<{ page?: string }>;
}

function parsePage(value: string | undefined): number {
  if (!value || !PAGE_NUMBER_PATTERN.test(value)) return 1;
  const page = Number.parseInt(value, 10);
  return page > 0 ? page : 1;
}

function pageHref(page: number): string {
  return page <= 1
    ? PUBLIC_ROUTE_PATHS.CAROUSELS
    : `${PUBLIC_ROUTE_PATHS.CAROUSELS}?page=${page}`;
}

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("carousels");
  return {
    title: t("metaTitle"),
    description: t("metaDescription"),
    openGraph: {
      title: t("metaTitle"),
      description: t("metaDescription"),
      type: "website",
    },
  };
}

export default async function PublicCarouselsPage({
  searchParams,
}: CarouselsPageProps): Promise<React.ReactElement> {
  const t = await getTranslations("carousels");
  const locale = await getRequestLocale();
  const { page: pageParam } = await searchParams;
  const page = parsePage(pageParam);
  const offset = (page - 1) * SERVER_FETCH.PUBLIC_CAROUSEL_PAGE_SIZE;
  const feed = await fetchPublicCarousels(
    SERVER_FETCH.PUBLIC_CAROUSEL_PAGE_SIZE,
    offset,
  );
  const cards = buildPublicCarouselCards(
    feed.items,
    locale,
    t("untitledCarousel"),
  );
  const totalPages = Math.max(
    1,
    Math.ceil(feed.total / SERVER_FETCH.PUBLIC_CAROUSEL_PAGE_SIZE),
  );

  return (
    <div
      className="relative min-h-screen overflow-hidden"
      style={{ background: BG_DEEP }}
    >
      <CarouselPageBackground />

      <div
        className="relative z-10 mx-auto px-4 py-12 sm:px-6"
        style={{ maxWidth: `${CAROUSEL_PAGE_MAX_WIDTH_PX}px` }}
      >
        <CarouselBackLink
          href={PUBLIC_ROUTE_PATHS.HOME}
          label={t("backHome")}
        />

        <header className="mb-10 max-w-3xl">
          <MarketingSectionEyebrow label={t("eyebrow")} />
          <h1
            className="text-4xl font-extrabold tracking-tight sm:text-5xl"
            style={{ color: TEXT, letterSpacing: "-0.03em" }}
          >
            {t("title")}
          </h1>
          <p className="mt-4 max-w-2xl text-lg" style={{ color: TEXT_MUTED }}>
            {t("subtitle")}
          </p>
          {feed.total > 0 ? (
            <p
              className="mt-4 font-mono text-xs uppercase tracking-[0.2em]"
              style={{ color: TEXT_DIM }}
            >
              {t("count", { count: feed.total })}
            </p>
          ) : null}
        </header>

        {cards.length === 0 ? (
          <CarouselEmptyState
            title={t("noCarousels")}
            hint={t("noCarouselsHint")}
          />
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((card) => (
              <CarouselCard
                key={card.id}
                card={card}
                locale={locale}
                labels={{
                  slides: t("slideCount", { count: card.slideCount ?? 0 }),
                  open: t("openCarousel", { title: card.title }),
                  view: t("viewCarousel"),
                  coverAlt: t("coverAlt", { title: card.title }),
                }}
              />
            ))}
          </div>
        )}

        <CarouselPagination
          page={page}
          totalPages={totalPages}
          previousHref={pageHref(page - 1)}
          nextHref={pageHref(page + 1)}
          labels={{
            navigation: t("pagination"),
            previous: t("previousPage"),
            next: t("nextPage"),
            counter: t("pageCounter", { page, total: totalPages }),
          }}
        />
      </div>
    </div>
  );
}
