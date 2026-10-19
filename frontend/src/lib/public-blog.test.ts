import { beforeEach, describe, expect, it, vi } from "vitest";
import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";
import { resolvePublicBlogView } from "./public-blog";

// Scenarios: see tests/features/public-blog-detail.feature

vi.mock("@/lib/server-fetch", () => ({
  fetchPublicBlogPost: vi.fn(),
  fetchBlogWithDesign: vi.fn(),
}));

import { fetchBlogWithDesign, fetchPublicBlogPost } from "@/lib/server-fetch";

const mockFetchPost = vi.mocked(fetchPublicBlogPost);
const mockFetchDesign = vi.mocked(fetchBlogWithDesign);

const STANDALONE_POST = {
  id: "post-1",
  slug: "post-1",
  title: "Standalone post",
  excerpt: "An excerpt",
  featured_image_url: null,
  published_at: "2026-07-01T00:00:00Z",
  keywords: [],
  origin: "standalone",
  project_id: null,
  content: { body: "# Standalone body" },
};

const CAROUSEL_POST = {
  ...STANDALONE_POST,
  id: "post-2",
  origin: "carousel",
  project_id: "project-9",
  content: { markdown: "# Carousel body", translations: { en: "# EN body" } },
};

const DESIGN_DATA = {
  blog: {
    title: "Carousel title",
    subtitle: "Sub",
    markdown: "# Designed",
    language: "pt",
    available_languages: ["pt", "en"],
  },
  design: {
    ...FALLBACK_DESIGN_TOKENS,
    theme_name: "designed-theme",
  },
};

beforeEach(() => {
  mockFetchPost.mockReset();
  mockFetchDesign.mockReset();
});

describe("resolvePublicBlogView (AE-0297)", () => {
  it("renders a standalone published post with the default public theme", async () => {
    mockFetchPost.mockResolvedValue(STANDALONE_POST);

    const view = await resolvePublicBlogView("post-1", "pt");
    expect(view).not.toBeNull();
    expect(view?.title).toBe("Standalone post");
    expect(view?.markdown).toBe("# Standalone body");
    expect(view?.design.theme_name).toBe(FALLBACK_DESIGN_TOKENS.theme_name);
    expect(mockFetchDesign).not.toHaveBeenCalled();
  });

  it("enriches a carousel-origin post through its project design", async () => {
    mockFetchPost.mockResolvedValue(CAROUSEL_POST);
    mockFetchDesign.mockResolvedValue(DESIGN_DATA);

    const view = await resolvePublicBlogView("post-2", "pt");
    expect(mockFetchDesign).toHaveBeenCalledWith("project-9", "pt");
    expect(view?.design.theme_name).toBe("designed-theme");
    expect(view?.markdown).toBe("# Designed");
  });

  it("falls back to the default theme when the design fetch fails (never 404)", async () => {
    mockFetchPost.mockResolvedValue(CAROUSEL_POST);
    mockFetchDesign.mockResolvedValue(null);

    const view = await resolvePublicBlogView("post-2", "en");
    expect(view).not.toBeNull();
    expect(view?.design.theme_name).toBe(FALLBACK_DESIGN_TOKENS.theme_name);
    // Localized translation is preferred over the raw markdown.
    expect(view?.markdown).toBe("# EN body");
  });

  it("keeps legacy carousel-projection URLs working", async () => {
    mockFetchPost.mockResolvedValue(null);
    mockFetchDesign.mockResolvedValue(DESIGN_DATA);

    const view = await resolvePublicBlogView("project-9", "pt");
    expect(mockFetchDesign).toHaveBeenCalledWith("project-9", "pt");
    expect(view?.title).toBe("Carousel title");
  });

  it("returns null (→ not-found) when nothing resolves", async () => {
    mockFetchPost.mockResolvedValue(null);
    mockFetchDesign.mockResolvedValue(null);

    expect(await resolvePublicBlogView("unknown-id", "pt")).toBeNull();
  });
});

// Feature: Public blog renders correctly for anonymous visitors (AE-0412)
// tests/features/public-blog-polish-ae0412.feature
describe("resolvePublicBlogView sanitizing (AE-0412)", () => {
  const PREVIEW_DESIGN_DATA = {
    blog: {
      title: "slide",
      subtitle: "Use <strong>ChatGPT</strong>",
      markdown: "# slide\n\nWhy <strong>ChatGPT</strong>?",
      language: "en",
      available_languages: ["pt", "en"],
    },
    design: {
      ...FALLBACK_DESIGN_TOKENS,
      images: {
        ...FALLBACK_DESIGN_TOKENS.images,
        hero: "/api/carousels/p/preview/images/slide_1.jpg?lang=en",
        slides: [
          "/api/carousels/p/preview/images/slide_2.jpg?lang=en",
          "/api/carousels/p/slide-images/en/slide_3.jpg",
        ],
      },
    },
  };

  // Feature: Public blog body never renders carousel slides (AE-0422)
  // frontend/tests/features/blog_no_carousel_slides_ae0422.feature
  // Scenario: Theme still comes from the carousel design
  //   Given the carousel design exposes colors and typography
  //   When the blog page renders
  //   Then the section headings use the design typography
  //   And no image URL is taken from the design
  it("keeps carousel theme tokens but drops every design image", async () => {
    mockFetchPost.mockResolvedValue(CAROUSEL_POST);
    mockFetchDesign.mockResolvedValue(PREVIEW_DESIGN_DATA);

    const view = await resolvePublicBlogView("post-2", "en");
    expect(view?.design.theme_name).toBe(FALLBACK_DESIGN_TOKENS.theme_name);
    expect(view?.design.typography).toEqual(FALLBACK_DESIGN_TOKENS.typography);
    // No carousel design image reaches the public page — not even as a
    // rendered `/slide-images/` URL (AE-0422, ADR-0025).
    expect(view?.design.images.hero).toBe("");
    expect(view?.design.images.slides).toEqual([]);
    expect(view?.design.images.rendered_slides_pt ?? null).toBeNull();
    expect(view?.design.images.blog_image_map ?? null).toBeNull();
  });

  // Scenario: A placeholder title falls back to a real title
  // Scenario: Emphasis markup in the body is rendered as emphasis
  it("falls back from a placeholder title and converts emphasis HTML", async () => {
    mockFetchPost.mockResolvedValue({
      ...CAROUSEL_POST,
      title: "Gemini 4 Argon chegou.",
    });
    mockFetchDesign.mockResolvedValue(PREVIEW_DESIGN_DATA);

    const view = await resolvePublicBlogView("post-2", "en");
    expect(view?.title).toBe("Gemini 4 Argon chegou.");
    expect(view?.subtitle).toBe("Use ChatGPT");
    expect(view?.markdown).toBe("# slide\n\nWhy **ChatGPT**?");
  });

  // Scenario: Every title candidate is a placeholder
  it("returns an empty title when no candidate is real", async () => {
    mockFetchPost.mockResolvedValue(null);
    mockFetchDesign.mockResolvedValue(PREVIEW_DESIGN_DATA);

    const view = await resolvePublicBlogView("project-9", "en");
    expect(view?.title).toBe("");
  });

  // Scenario: A subtitle equal to the title is not repeated
  it("drops a subtitle that repeats the title", async () => {
    mockFetchPost.mockResolvedValue(null);
    mockFetchDesign.mockResolvedValue({
      ...DESIGN_DATA,
      blog: { ...DESIGN_DATA.blog, subtitle: "Carousel <b>title</b>" },
    });

    const view = await resolvePublicBlogView("project-9", "pt");
    expect(view?.subtitle).toBeNull();
  });

  it("keeps an empty hero empty", async () => {
    mockFetchPost.mockResolvedValue(STANDALONE_POST);

    const view = await resolvePublicBlogView("post-1", "pt");
    expect(view?.design.images.hero).toBe("");
    expect(view?.subtitle).toBe("An excerpt");
  });
});
