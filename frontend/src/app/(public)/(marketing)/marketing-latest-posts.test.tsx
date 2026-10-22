/**
 * The landing "Latest Posts" section lists published blog posts only.
 * Gherkin: tests/features/landing-latest-posts-published-only-ae0449.feature
 */
import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CarouselProjectListResponse } from "@/schemas/carousel";
import type { PublicBlogPostSummary } from "@/schemas/public-blog-post";

vi.mock("@/lib/server-fetch", () => ({
  fetchCompletedProjects: vi.fn(),
  fetchPublicBlogPosts: vi.fn(),
}));

import {
  fetchCompletedProjects,
  fetchPublicBlogPosts,
} from "@/lib/server-fetch";
import { MarketingLatestPosts } from "@/app/(public)/(marketing)/marketing-latest-posts";
import { loadLandingFeeds } from "@/app/(public)/(marketing)/marketing-latest-posts-data";
import type { Translator } from "@/app/(public)/(marketing)/types";

const mockProjects = vi.mocked(fetchCompletedProjects);
const mockPosts = vi.mocked(fetchPublicBlogPosts);

const DRAFT_SOURCE_ID = "901e51bb-0000-4000-8000-000000000001";
const HIDDEN_SOURCE_ID = "519c7b57-0000-4000-8000-000000000002";
const SCHEDULED_SOURCE_ID = "5344b6c6-0000-4000-8000-000000000003";
const PUBLISHED_SOURCE_ID = "fe1bd677-0000-4000-8000-000000000004";
const PUBLISHED_POST_ID = "aa11bb22-0000-4000-8000-000000000005";
const EMPTY_STATE = "blog.noPosts";
const LOCALE = "en";

function translator(namespace: string): Translator {
  return ((key: string) => `${namespace}.${key}`) as unknown as Translator;
}

function project(
  id: string,
  title: string,
): CarouselProjectListResponse["items"][number] {
  return {
    id,
    title,
    title_en: `${title} EN`,
    subtitle: `${title} subtítulo`,
    subtitle_en: `${title} subtitle`,
    topic: title,
    niche: "IA",
    created_at: "2026-10-20T10:00:00Z",
    design_tokens: { images: { hero: "slides/hero.png" } },
  } as unknown as CarouselProjectListResponse["items"][number];
}

function carouselFeed(
  items: CarouselProjectListResponse["items"],
): CarouselProjectListResponse {
  return { items, total: items.length, limit: 20, offset: 0 };
}

function publishedPost(
  overrides: Partial<PublicBlogPostSummary> = {},
): PublicBlogPostSummary {
  return {
    id: PUBLISHED_POST_ID,
    slug: "published-post",
    title: "Published post",
    excerpt: "Published excerpt",
    featured_image_url: "https://cdn.example/cover.jpg",
    published_at: "2026-10-19T10:00:00Z",
    keywords: [],
    origin: "carousel",
    project_id: PUBLISHED_SOURCE_ID,
    ...overrides,
  };
}

function postFeed(items: PublicBlogPostSummary[]) {
  return { items, total: items.length, limit: 5, offset: 0 };
}

async function renderHome(): Promise<HTMLElement> {
  const { cards } = await loadLandingFeeds(LOCALE);
  render(
    <MarketingLatestPosts
      t={translator("home")}
      tb={translator("blog")}
      cards={cards}
      locale={LOCALE}
    />,
  );
  return screen.getByTestId("latest-posts");
}

beforeEach(() => {
  mockProjects.mockReset();
  mockPosts.mockReset();
});

describe("landing Latest Posts (AE-0449)", () => {
  // Scenario: A public carousel whose blog post is a draft is not listed
  it("does not list a public carousel whose blog post is a draft", async () => {
    mockProjects.mockResolvedValue(
      carouselFeed([project(DRAFT_SOURCE_ID, "Draft carousel")]),
    );
    mockPosts.mockResolvedValue(postFeed([]));

    const section = await renderHome();

    expect(within(section).getByText(EMPTY_STATE)).toBeInTheDocument();
    expect(within(section).queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryByText(/Draft carousel/)).not.toBeInTheDocument();
  });

  // Scenario: Only published posts are listed and they open the public blog post
  it("lists only the published post and links it to the public blog post", async () => {
    mockProjects.mockResolvedValue(
      carouselFeed([
        project(DRAFT_SOURCE_ID, "Draft carousel"),
        project(HIDDEN_SOURCE_ID, "Hidden carousel"),
        project(SCHEDULED_SOURCE_ID, "Scheduled carousel"),
        project(PUBLISHED_SOURCE_ID, "Published carousel"),
      ]),
    );
    mockPosts.mockResolvedValue(postFeed([publishedPost()]));

    const section = await renderHome();
    const links = within(section).getAllByRole("link");

    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", `/blog/${PUBLISHED_POST_ID}`);
    expect(screen.queryByText(/Draft carousel/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Hidden carousel/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Scheduled carousel/)).not.toBeInTheDocument();
  });

  // Scenario: A published post card keeps one language and its own cover
  it("renders the English copy and the post's own cover", async () => {
    mockProjects.mockResolvedValue(
      carouselFeed([project(PUBLISHED_SOURCE_ID, "Publicado")]),
    );
    mockPosts.mockResolvedValue(postFeed([publishedPost()]));

    const section = await renderHome();

    expect(within(section).getByText("Publicado EN")).toBeInTheDocument();
    expect(within(section).getByText("Publicado subtitle")).toBeInTheDocument();
    expect(
      within(section).queryByText("Publicado subtítulo"),
    ).not.toBeInTheDocument();
    const image = section.querySelector("img");
    expect(image?.getAttribute("src") ?? "").not.toContain("hero.png");
  });

  // Scenario: The landing page shows the empty state when the public feed fails
  it("shows the empty state when the public blog feed is unavailable", async () => {
    mockProjects.mockResolvedValue(
      carouselFeed([project(DRAFT_SOURCE_ID, "Draft carousel")]),
    );
    mockPosts.mockResolvedValue(null);

    const section = await renderHome();

    expect(within(section).getByText(EMPTY_STATE)).toBeInTheDocument();
    expect(screen.queryByText(/Draft carousel/)).not.toBeInTheDocument();
  });

  it("keeps the public carousel total for the stats", async () => {
    mockProjects.mockResolvedValue(
      carouselFeed([
        project(DRAFT_SOURCE_ID, "Draft carousel"),
        project(PUBLISHED_SOURCE_ID, "Published carousel"),
      ]),
    );
    mockPosts.mockResolvedValue(postFeed([]));

    const feeds = await loadLandingFeeds(LOCALE);

    expect(feeds.carouselTotal).toBe(2);
    expect(mockPosts).toHaveBeenCalledWith(5);
  });

  it("shows the untitled label for a post without a usable title", async () => {
    mockProjects.mockResolvedValue(carouselFeed([]));
    mockPosts.mockResolvedValue(
      postFeed([publishedPost({ title: "", project_id: null })]),
    );

    const section = await renderHome();

    expect(within(section).getByText("blog.untitledPost")).toBeInTheDocument();
  });
});
