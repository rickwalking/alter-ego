import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-fetch", () => ({
  fetchPublicBlogPosts: vi.fn(),
  fetchPublicCarousels: vi.fn(),
}));

import { fetchPublicBlogPosts, fetchPublicCarousels } from "@/lib/server-fetch";
import robots from "./robots";
import sitemap from "./sitemap";

const SITE = "https://marinssolutions.com";
const mockPosts = vi.mocked(fetchPublicBlogPosts);
const mockCarousels = vi.mocked(fetchPublicCarousels);

const POST = {
  id: "post-1",
  slug: "post-1",
  title: "Published",
  published_at: "2026-10-20T10:00:00Z",
  keywords: [],
  origin: "manual",
};

const CAROUSEL = {
  id: "carousel-1",
  created_at: "2026-10-19T09:00:00Z",
  updated_at: "2026-10-19T12:00:00Z",
};

type CarouselPage = Awaited<ReturnType<typeof fetchPublicCarousels>>;

function carouselPage(
  items: (typeof CAROUSEL)[],
  total = items.length,
): CarouselPage {
  return { items, total, limit: 100, offset: 0 } as unknown as CarouselPage;
}

function feeds(
  posts: (typeof POST)[] | null,
  carousels: (typeof CAROUSEL)[],
): void {
  mockPosts.mockResolvedValue(
    posts === null
      ? null
      : { items: posts, total: posts.length, limit: 50, offset: 0 },
  );
  mockCarousels.mockResolvedValue(carouselPage(carousels));
}

const PAGES = [SITE, `${SITE}/blog`, `${SITE}/carousels`, `${SITE}/chat`];

async function sitemapUrls(): Promise<string[]> {
  return (await sitemap()).map((entry) => entry.url);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("robots", () => {
  it("points at the production sitemap", () => {
    // Scenario: robots.txt points at the production sitemap
    expect(robots().sitemap).toBe(`${SITE}/sitemap.xml`);
  });
});

describe("sitemap", () => {
  it("lists the public pages on the production domain", async () => {
    // Scenario: The sitemap lists the public pages on the production domain
    feeds([], []);

    const urls = await sitemapUrls();

    expect(urls).toEqual(PAGES);
    expect(urls.some((url) => url.includes("/dashboard"))).toBe(false);
  });

  it("lists every published post and public carousel", async () => {
    // Scenario: The sitemap lists every published post and public carousel
    feeds([POST], [CAROUSEL]);

    const entries = await sitemap();
    const post = entries.find((entry) => entry.url === `${SITE}/blog/post-1`);
    const carousel = entries.find(
      (entry) => entry.url === `${SITE}/carousels/carousel-1`,
    );

    expect(post?.lastModified).toEqual(new Date(POST.published_at));
    expect(carousel?.lastModified).toEqual(new Date(CAROUSEL.updated_at));
    expect(mockCarousels).toHaveBeenCalledWith(100, 0, { revalidate: 3600 });
    expect(mockPosts).toHaveBeenCalledWith(50, 0, { revalidate: 3600 });
  });

  it("still renders when the content feeds are unavailable", async () => {
    // Scenario: The sitemap still renders when the content feeds are unavailable
    feeds(null, []);

    expect(await sitemapUrls()).toEqual(PAGES);
  });

  it("pages through a feed longer than one page", async () => {
    // Scenario: The sitemap pages through feeds longer than one page
    const second = { ...POST, id: "post-2" };
    const third = { ...POST, id: "post-3" };
    mockPosts
      .mockResolvedValueOnce({
        items: [POST, second],
        total: 3,
        limit: 50,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [third],
        total: 3,
        limit: 50,
        offset: 50,
      });
    mockCarousels
      .mockResolvedValueOnce(carouselPage([CAROUSEL], 2))
      .mockResolvedValueOnce(
        carouselPage([{ ...CAROUSEL, id: "carousel-2" }], 2),
      );

    const urls = await sitemapUrls();

    expect(urls).toContain(`${SITE}/blog/post-3`);
    expect(urls).toContain(`${SITE}/carousels/carousel-2`);
    expect(mockPosts).toHaveBeenNthCalledWith(2, 50, 50, { revalidate: 3600 });
    expect(mockCarousels).toHaveBeenNthCalledWith(2, 100, 100, {
      revalidate: 3600,
    });
    expect(mockPosts).toHaveBeenCalledTimes(2);
  });

  it("stops paging at the safety cap", async () => {
    // Scenario: The sitemap pages through feeds longer than one page
    mockPosts.mockResolvedValue({
      items: [POST],
      total: 10_000,
      limit: 50,
      offset: 0,
    });
    mockCarousels.mockResolvedValue(carouselPage([]));

    await sitemap();

    expect(mockPosts).toHaveBeenCalledTimes(20);
  });
});
