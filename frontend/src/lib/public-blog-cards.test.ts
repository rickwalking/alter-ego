import { describe, expect, it } from "vitest";
import { buildPublicBlogCards } from "@/lib/public-blog-cards";
import type { CarouselProjectListResponse } from "@/schemas/carousel";
import type { PublicBlogPostSummary } from "@/schemas/public-blog-post";

// Feature: Public blog renders correctly for anonymous visitors (AE-0412)
// tests/features/public-blog-polish-ae0412.feature

type Project = CarouselProjectListResponse["items"][number];

function project(overrides: Partial<Project> = {}): Project {
  return {
    id: "proj-1",
    topic: "Raw topic",
    audience: "Devs",
    niche: "AI models",
    title: "Título PT",
    subtitle: "Subtítulo PT",
    title_en: "Title EN",
    subtitle_en: "Subtitle EN",
    theme: "default",
    status: "completed",
    primary_color: null,
    accent_color: null,
    background_color: null,
    blog_markdown: null,
    caption: null,
    design_tokens: {
      images: {
        hero: "/api/carousels/proj-1/preview/images/slide_1.jpg?lang=pt",
      },
    },
    created_at: "2026-10-14T00:00:00Z",
    updated_at: "2026-10-14T00:00:00Z",
    ...overrides,
  };
}

function feed(items: Project[]): CarouselProjectListResponse {
  return { items, total: items.length, limit: 20, offset: 0 };
}

const POST: PublicBlogPostSummary = {
  id: "post-1",
  slug: "post-1",
  title: "Post title",
  excerpt: "An **excerpt**",
  featured_image_url: null,
  published_at: "2026-10-15T00:00:00Z",
  keywords: [],
  origin: "standalone",
  project_id: null,
};

describe("buildPublicBlogCards", () => {
  // Scenario: Listing card maps an owner-only preview hero to the public route
  it("uses the public image route for carousel heroes", () => {
    const [card] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([project()]),
      locale: "pt",
    });
    expect(card.imageUrl).toBe(
      "/api/carousels/proj-1/images/slide_1.jpg?lang=pt",
    );
    expect(card.imageUrl).not.toContain("/preview/images/");
    expect(card.href).toBe("/blog/proj-1");
  });

  it("leaves the image undefined when the project has no hero", () => {
    const [card] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([project({ design_tokens: null })]),
      locale: "pt",
    });
    expect(card.imageUrl).toBeUndefined();
  });

  it("localizes title and subtitle", () => {
    const [pt] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([project()]),
      locale: "pt",
    });
    const [en] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([project()]),
      locale: "en",
    });
    expect(pt.title).toBe("Título PT");
    expect(pt.subtitle).toBe("Subtítulo PT");
    expect(en.title).toBe("Title EN");
    expect(en.subtitle).toBe("Subtitle EN");
  });

  // Scenario: A placeholder title falls back to a real title
  it("skips a placeholder English title", () => {
    const [card] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([
        project({ title_en: "slide", title: "Gemini 4 Argon chegou." }),
      ]),
      locale: "en",
    });
    expect(card.title).toBe("Gemini 4 Argon chegou.");
  });

  it("falls back to the topic, then to the public post title", () => {
    const [topicCard] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([project({ title: null, title_en: null })]),
      locale: "pt",
    });
    expect(topicCard.title).toBe("Raw topic");

    const [postCard] = buildPublicBlogCards({
      publicFeed: { items: [{ ...POST, project_id: "proj-1" }] },
      carouselFeed: feed([
        project({ title: null, title_en: "slide", topic: "slide" }),
      ]),
      locale: "en",
    });
    expect(postCard.title).toBe("Post title");
    expect(postCard.id).toBe("post-1");
    expect(postCard.href).toBe("/blog/post-1");
  });

  // Scenario: Emphasis markup in a title is not shown raw
  it("strips emphasis markup from titles", () => {
    const [card] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([
        project({
          title: "Por que todo mundo usa <strong>ChatGPT</strong>?",
        }),
      ]),
      locale: "pt",
    });
    expect(card.title).toBe("Por que todo mundo usa ChatGPT?");
  });

  // Scenario: A long niche is not used as a category chip
  it("only keeps a short niche as the category", () => {
    const [shortNiche, longNiche] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([
        project(),
        project({
          id: "proj-2",
          niche:
            "Goodhart's Law gaming, context anxiety, anti-gaming gates in agentic AI",
        }),
      ]),
      locale: "pt",
    });
    expect(shortNiche.niche).toBe("AI models");
    expect(longNiche.niche).toBeUndefined();
  });

  // Scenario: A subtitle equal to the title is not repeated
  it("drops a subtitle that repeats the title and truncates long ones", () => {
    const [same, long] = buildPublicBlogCards({
      publicFeed: null,
      carouselFeed: feed([
        project({ subtitle: "Título PT" }),
        project({
          id: "proj-2",
          subtitle: Array.from({ length: 20 }, (_, i) => `w${i}`).join(" "),
        }),
      ]),
      locale: "pt",
    });
    expect(same.subtitle).toBeUndefined();
    expect(long.subtitle).toBe(
      `${Array.from({ length: 15 }, (_, i) => `w${i}`).join(" ")}...`,
    );
  });

  it("maps a standalone public post", () => {
    const [card] = buildPublicBlogCards({
      publicFeed: {
        items: [
          {
            ...POST,
            featured_image_url:
              "/api/carousels/x/preview/images/hero.jpg?lang=en",
          },
        ],
      },
      carouselFeed: feed([]),
      locale: "pt",
    });
    expect(card).toEqual({
      id: "post-1",
      title: "Post title",
      subtitle: "An excerpt",
      imageUrl: "/api/carousels/x/images/hero.jpg?lang=en",
      createdAt: "2026-10-15T00:00:00Z",
      href: "/blog/post-1",
    });
  });

  it("handles a standalone post without excerpt, image or date", () => {
    const [card] = buildPublicBlogCards({
      publicFeed: {
        items: [{ ...POST, excerpt: null, published_at: null }],
      },
      carouselFeed: feed([]),
      locale: "pt",
    });
    expect(card.subtitle).toBeUndefined();
    expect(card.imageUrl).toBeUndefined();
    expect(card.createdAt).toBe("");
  });
});
