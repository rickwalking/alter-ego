import type { getTranslations } from "next-intl/server";
import type { CarouselProjectListResponse } from "@/schemas/carousel";

export type Translator = Awaited<ReturnType<typeof getTranslations>>;

export type CarouselListItem = CarouselProjectListResponse["items"][number];

export interface MarketingHeroProps {
  t: Translator;
  tc: Translator;
}

export interface MarketingStatsProps {
  t: Translator;
}

export interface MarketingFeaturesProps {
  t: Translator;
}

export interface MarketingLatestPostsProps {
  t: Translator;
  tb: Translator;
  data: CarouselProjectListResponse;
  locale: string;
}

export interface MarketingAboutProps {
  t: Translator;
}

export interface MarketingPostProps {
  post: CarouselListItem;
  locale: string;
}

export interface LatestPostsHeaderProps {
  t: Translator;
}
