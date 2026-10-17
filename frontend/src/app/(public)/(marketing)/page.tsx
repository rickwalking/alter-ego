import { getTranslations } from "next-intl/server";
import { getRequestLocale } from "@/i18n/request-locale";
import { fetchCompletedProjects } from "@/lib/server-fetch";
import type { CarouselProjectListResponse } from "@/schemas/carousel";
import { MarketingDecorations } from "@/app/(public)/(marketing)/marketing-decorations";
import { MarketingHero } from "@/app/(public)/(marketing)/marketing-hero";
import { MarketingStats } from "@/app/(public)/(marketing)/marketing-stats";
import { MarketingFeatures } from "@/app/(public)/(marketing)/marketing-features";
import { MarketingLatestPosts } from "@/app/(public)/(marketing)/marketing-latest-posts";
import { MarketingAbout } from "@/app/(public)/(marketing)/marketing-about";
import { MarketingFooter } from "@/app/(public)/(marketing)/marketing-footer";
import type { Translator } from "@/app/(public)/(marketing)/types";

function HomePageContent({
  t,
  tc,
  tb,
  data,
  locale,
}: {
  t: Translator;
  tc: Translator;
  tb: Translator;
  data: CarouselProjectListResponse;
  locale: string;
}): React.ReactElement {
  return (
    <>
      <MarketingDecorations />
      <MarketingHero t={t} tc={tc} />
      <MarketingStats t={t} />
      <MarketingFeatures t={t} />
      <MarketingLatestPosts t={t} tb={tb} data={data} locale={locale} />
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

  const data: CarouselProjectListResponse = await fetchCompletedProjects(5);

  return <HomePageContent t={t} tc={tc} tb={tb} data={data} locale={locale} />;
}
