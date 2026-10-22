import { getTranslations } from "next-intl/server";
import { getRequestLocale } from "@/i18n/request-locale";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";
import { MarketingDecorations } from "@/app/(public)/(marketing)/marketing-decorations";
import { MarketingHero } from "@/app/(public)/(marketing)/marketing-hero";
import { MarketingStats } from "@/app/(public)/(marketing)/marketing-stats";
import { MarketingFeatures } from "@/app/(public)/(marketing)/marketing-features";
import { MarketingLatestPosts } from "@/app/(public)/(marketing)/marketing-latest-posts";
import { MarketingAbout } from "@/app/(public)/(marketing)/marketing-about";
import { MarketingFooter } from "@/app/(public)/(marketing)/marketing-footer";
import { loadLandingFeeds } from "@/app/(public)/(marketing)/marketing-latest-posts-data";
import type { Translator } from "@/app/(public)/(marketing)/types";

function HomePageContent({
  t,
  tc,
  tb,
  cards,
  carouselTotal,
  locale,
}: Readonly<{
  t: Translator;
  tc: Translator;
  tb: Translator;
  cards: NeonBlogPostCardProps[];
  carouselTotal: number;
  locale: string;
}>): React.ReactElement {
  return (
    <>
      <MarketingDecorations />
      <MarketingHero t={t} tc={tc} />
      <MarketingStats t={t} carouselTotal={carouselTotal} />
      <MarketingFeatures t={t} />
      <MarketingLatestPosts t={t} tb={tb} cards={cards} locale={locale} />
      <MarketingAbout t={t} />
      <MarketingFooter />
    </>
  );
}

export default async function HomePage() {
  const t = await getTranslations("home");
  const tc = await getTranslations("common");
  const tb = await getTranslations("blog");

  const locale = await getRequestLocale();

  const { cards, carouselTotal } = await loadLandingFeeds(locale);

  return (
    <HomePageContent
      t={t}
      tc={tc}
      tb={tb}
      cards={cards}
      carouselTotal={carouselTotal}
      locale={locale}
    />
  );
}
