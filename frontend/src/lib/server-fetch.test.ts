import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchCompletedProjects,
  fetchCarouselDesign,
  fetchPublicBlogPost,
  fetchPublicBlogPosts,
  fetchPublicCarousel,
  fetchPublicCarousels,
} from "@/lib/server-fetch";

vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");

const MOCK_PROJECT_LIST = {
  items: [
    {
      id: "abc-123",
      topic: "Gemma 4",
      audience: "Developers",
      niche: "AI/ML",
      language: "pt-BR",
      title: "Gemma 4",
      subtitle: null,
      theme: "ai_competition",
      status: "completed",
      primary_color: null,
      accent_color: null,
      background_color: null,
      blog_markdown: null,
      blog_translations: null,
      caption: null,
      design_tokens: null,
      created_at: "2026-04-20T00:00:00Z",
      updated_at: "2026-04-20T00:00:00Z",
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
};

const MOCK_DESIGN = {
  colors: {
    primary: "#3b82f6",
    accent: "#f59e0b",
    bg: "#0a0e17",
    text: "#ffffff",
    text_muted: "rgba(255,255,255,0.63)",
    text_dim: "rgba(255,255,255,0.48)",
    border: "#3b82f633",
    glow: "#3b82f60D",
  },
  typography: {
    font_family_heading: "'Segoe UI', sans-serif",
    font_family_body: "'Segoe UI', sans-serif",
    font_family_badge: "'Courier New', monospace",
  },
  images: {
    hero: "/api/carousels/1/images/hero",
    slides: [],
  },
  layout: {
    badge_label: "AI/ML",
    swipe_text: "Swipe →",
    progress_segments: 7,
  },
  theme_name: "ai_competition",
};

describe("server-fetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("fetchCompletedProjects", () => {
    it("returns validated project list on success", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_PROJECT_LIST),
      });
      vi.spyOn(globalThis, "fetch").mockImplementation(mockFetch);

      const result = await fetchCompletedProjects(20);

      expect(result.items).toHaveLength(1);
      expect(result.items[0].id).toBe("abc-123");
      expect(result.total).toBe(1);
    });

    it("returns empty list on fetch failure", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValue(
        new Error("Network error"),
      );

      const result = await fetchCompletedProjects(20);

      expect(result.items).toHaveLength(0);
      expect(result.total).toBe(0);
    });

    it("returns empty list on non-ok response", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({}),
      } as Response);

      const result = await fetchCompletedProjects(20);

      expect(result.items).toHaveLength(0);
    });

    it("passes limit parameter to URL", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_PROJECT_LIST),
      });
      vi.spyOn(globalThis, "fetch").mockImplementation(mockFetch);

      await fetchCompletedProjects(5);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("limit=5");
    });

    // Feature: Landing page truth, links and public header (AE-0443)
    // Scenario: Published-carousel stat counts only public, completed projects
    //   Given the public carousel list is fetched for the landing page
    //   When the request is built
    //   Then it filters by status=completed so drafts are never counted
    it("filters the public list to completed projects", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_PROJECT_LIST),
      });
      vi.spyOn(globalThis, "fetch").mockImplementation(mockFetch);

      await fetchCompletedProjects(5);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("public=true");
      expect(calledUrl).toContain("status=completed");
    });
  });

  describe("fetchCarouselDesign (AE-0423)", () => {
    // Scenario: The public read never fetches carousel blog markdown
    it("fetches only the design endpoint", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_DESIGN),
      });
      vi.spyOn(globalThis, "fetch").mockImplementation(mockFetch);

      const result = await fetchCarouselDesign("test-id", "en");

      expect(result?.theme_name).toBe("ai_competition");
      expect(mockFetch).toHaveBeenCalledTimes(1);
      const url = String(mockFetch.mock.calls[0][0]);
      expect(url).toContain("/design");
      expect(url).not.toContain("/blog");
    });

    it("returns null on fetch failure", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValue(
        new Error("Network error"),
      );

      expect(await fetchCarouselDesign("test-id")).toBeNull();
    });
  });

  describe("fetchPublicCarousels (AE-0444)", () => {
    it("requests public completed carousels newest-first", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_PROJECT_LIST),
      });
      vi.spyOn(globalThis, "fetch").mockImplementation(mockFetch);

      const result = await fetchPublicCarousels(12, 24);

      expect(result.items).toHaveLength(1);
      const url = String(mockFetch.mock.calls[0][0]);
      expect(url).toContain("public=true");
      expect(url).toContain("status=completed");
      expect(url).toContain("sort=created_at");
      expect(url).toContain("limit=12");
      expect(url).toContain("offset=24");
    });

    it("falls open to an empty page on failure", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("boom"));

      await expect(fetchPublicCarousels(12, 0)).resolves.toEqual({
        items: [],
        total: 0,
        limit: 12,
        offset: 0,
      });
    });

    it("falls open when the payload fails validation", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ items: "nope" }),
      } as Response);

      await expect(fetchPublicCarousels(12, 0)).resolves.toMatchObject({
        items: [],
        total: 0,
      });
    });
  });

  describe("fetchPublicCarousel (AE-0444)", () => {
    const MOCK_PUBLIC_CAROUSEL = {
      id: "proj-1",
      title: "Título",
      title_en: "Title",
      subtitle: null,
      subtitle_en: null,
      language: "pt-BR",
      created_at: "2026-10-20T11:40:01Z",
      slide_count: 1,
      available_languages: ["pt"],
      slides_by_language: {
        pt: [
          {
            slide_number: 1,
            heading: "Abertura",
            image_url: "/api/carousels/proj-1/images/slide_1.jpg",
          },
        ],
      },
      cover_url: "/api/carousels/proj-1/images/slide_1.jpg",
    };

    it("returns the validated public projection", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_PUBLIC_CAROUSEL),
      });
      vi.spyOn(globalThis, "fetch").mockImplementation(mockFetch);

      const result = await fetchPublicCarousel("proj-1");

      expect(result?.title).toBe("Título");
      expect(String(mockFetch.mock.calls[0][0])).toContain(
        "/api/carousels/proj-1/public",
      );
    });

    it("returns null for an unknown, private or failed carousel", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: false,
        status: 404,
      } as Response);

      expect(await fetchPublicCarousel("missing")).toBeNull();
    });

    it("returns null when the payload fails validation", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: "proj-1" }),
      } as Response);

      expect(await fetchPublicCarousel("proj-1")).toBeNull();
    });
  });

  describe("fetchPublicBlogPost (AE-0297)", () => {
    const MOCK_PUBLIC_POST = {
      id: "e7e871c7-9f5f-4b70-b226-a2d2adeb06fa",
      slug: "a-post",
      title: "A post",
      excerpt: "Excerpt",
      featured_image_url: null,
      published_at: "2026-07-01T00:00:00Z",
      meta_title: null,
      meta_description: null,
      keywords: [],
      canonical_url: null,
      origin: "standalone",
      project_id: null,
      content: { markdown: "# Body" },
    };

    it("returns the validated lean post on success", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_PUBLIC_POST),
      });
      vi.spyOn(globalThis, "fetch").mockImplementation(mockFetch);

      const result = await fetchPublicBlogPost(MOCK_PUBLIC_POST.id);
      expect(result?.title).toBe("A post");
      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(
        `/api/public/blog-posts/${MOCK_PUBLIC_POST.id}`,
      );
    });

    it("returns null on 404 (hidden or unknown post)", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: false,
        status: 404,
      } as Response);
      expect(await fetchPublicBlogPost("nope")).toBeNull();
    });
  });

  describe("fetchPublicBlogPosts (AE-0297)", () => {
    it("returns null on failure so the listing can fall open", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("boom"));
      expect(await fetchPublicBlogPosts(20)).toBeNull();
    });
  });
});
