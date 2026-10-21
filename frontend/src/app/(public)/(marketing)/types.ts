import type { getTranslations } from "next-intl/server";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";

export type Translator = Awaited<ReturnType<typeof getTranslations>>;

export interface MarketingHeroProps {
  t: Translator;
  tc: Translator;
}

export interface MarketingStatsProps {
  t: Translator;
  carouselTotal: number;
}

export interface MarketingFeaturesProps {
  t: Translator;
}

export interface MarketingLatestPostsProps {
  t: Translator;
  tb: Translator;
  cards: NeonBlogPostCardProps[];
  locale: string;
}

export interface MarketingAboutProps {
  t: Translator;
}

export interface MarketingPostProps {
  card: NeonBlogPostCardProps;
  locale: string;
}

export interface LatestPostsHeaderProps {
  t: Translator;
}
