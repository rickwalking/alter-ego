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
