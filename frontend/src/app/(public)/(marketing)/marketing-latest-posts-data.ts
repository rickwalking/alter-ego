import { cardLocale } from "@/app/(public)/(marketing)/marketing-helpers";
import { buildPublicBlogCards } from "@/lib/public-blog-cards";
import {
  fetchCompletedProjects,
  fetchPublicBlogPosts,
} from "@/lib/server-fetch";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";

const LATEST_POSTS_LIMIT = 5;
const CAROUSEL_COPY_LIMIT = 20;

export interface LandingFeeds {
  cards: NeonBlogPostCardProps[];
  carouselTotal: number;
}

/**
 * Landing data: "Latest Posts" cards come from the published-only public
 * blog feed (the /blog list source); public carousels only enrich those
 * cards with localized copy and give the stats their total.
 */
export async function loadLandingFeeds(locale: string): Promise<LandingFeeds> {
  const [publicFeed, carouselFeed] = await Promise.all([
    fetchPublicBlogPosts(LATEST_POSTS_LIMIT),
    fetchCompletedProjects(CAROUSEL_COPY_LIMIT),
  ]);
  return {
    cards: buildPublicBlogCards({
      publicFeed,
      carouselFeed,
      locale: cardLocale(locale),
    }),
    carouselTotal: carouselFeed.total,
  };
}
