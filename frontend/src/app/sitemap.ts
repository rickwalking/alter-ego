import type { MetadataRoute } from "next";
import { SITE_URL } from "@/constants/api";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { SITEMAP } from "@/constants/sitemap";
import { fetchPublicBlogPosts, fetchPublicCarousels } from "@/lib/server-fetch";

export const dynamic = "force-dynamic";

type SitemapEntry = MetadataRoute.Sitemap[number];

function siteUrl(path: string): string {
  return path === PUBLIC_ROUTE_PATHS.HOME ? SITE_URL : `${SITE_URL}${path}`;
}

function pageEntries(): SitemapEntry[] {
  return [
    {
      url: siteUrl(PUBLIC_ROUTE_PATHS.HOME),
      changeFrequency: SITEMAP.PAGE_CHANGE_FREQUENCY,
      priority: SITEMAP.HOME_PRIORITY,
    },
    {
      url: siteUrl(PUBLIC_ROUTE_PATHS.BLOG),
      changeFrequency: SITEMAP.PAGE_CHANGE_FREQUENCY,
      priority: SITEMAP.SECTION_PRIORITY,
    },
    {
      url: siteUrl(PUBLIC_ROUTE_PATHS.CAROUSELS),
      changeFrequency: SITEMAP.PAGE_CHANGE_FREQUENCY,
      priority: SITEMAP.SECTION_PRIORITY,
    },
  ];
}

function contentEntry(
  path: string,
  modified: string | null | undefined,
): SitemapEntry {
  return {
    url: siteUrl(path),
    ...(modified ? { lastModified: new Date(modified) } : {}),
    changeFrequency: SITEMAP.CONTENT_CHANGE_FREQUENCY,
    priority: SITEMAP.CONTENT_PRIORITY,
  };
}

/**
 * Production URLs of the public pages, every published blog post and every
 * public completed carousel. Drafts never reach these feeds, and an
 * unavailable feed only drops its own entries.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [posts, carousels] = await Promise.all([
    fetchPublicBlogPosts(SITEMAP.BLOG_POST_LIMIT),
    fetchPublicCarousels(SITEMAP.CAROUSEL_LIMIT, 0),
  ]);
  return [
    ...pageEntries(),
    ...(posts?.items ?? []).map((post) =>
      contentEntry(PUBLIC_ROUTE_PATHS.BLOG_POST(post.id), post.published_at),
    ),
    ...carousels.items.map((carousel) =>
      contentEntry(
        PUBLIC_ROUTE_PATHS.CAROUSEL_VIEWER(carousel.id),
        carousel.updated_at,
      ),
    ),
  ];
}
