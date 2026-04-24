import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchCompletedProjects,
  fetchBlogWithDesign,
  fetchBlogWithDesignCombined,
} from "@/lib/server-fetch";

vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");

const MOCK_PROJECT_LIST = {
  items: [
    {
      id: "abc-123",
      topic: "Gemma 4",
      audience: "Developers",
      niche: "AI/ML",
      title: "Gemma 4",
      subtitle: null,
      theme: "ai_competition",
      status: "completed",
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

const MOCK_BLOG = {
  markdown: "# Test Blog Content",
  title: "Test Title",
  subtitle: "Test Subtitle",
  language: "en",
  available_languages: ["pt", "en"],
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
    progress_segments: 6,
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
      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

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
  });

  describe("fetchBlogWithDesign", () => {
    it("returns blog and design data on success", async () => {
      vi.spyOn(globalThis, "fetch").mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/blog/")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(MOCK_BLOG),
          } as Response);
        }
        if (url.includes("/design")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(MOCK_DESIGN),
          } as Response);
        }
        return Promise.resolve({ ok: false, status: 404 } as Response);
      });

      const result = await fetchBlogWithDesign("test-id", "en");

      expect(result).not.toBeNull();
      expect(result!.blog.title).toBe("Test Title");
      expect(result!.design.theme_name).toBe("ai_competition");
    });

    it("returns null on fetch failure", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

      const result = await fetchBlogWithDesign("test-id");

      expect(result).toBeNull();
    });

    it("returns null on non-ok blog response", async () => {
      vi.spyOn(globalThis, "fetch").mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/blog/")) {
          return Promise.resolve({ ok: false, status: 404 } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(MOCK_DESIGN),
        } as Response);
      });

      const result = await fetchBlogWithDesign("bad-id");

      expect(result).toBeNull();
    });
  });

  describe("fetchBlogWithDesignCombined", () => {
    it("returns combined data on success", async () => {
      const MOCK_COMBINED = {
        ...MOCK_BLOG,
        design: MOCK_DESIGN,
      };

      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_COMBINED),
      } as Response);

      const result = await fetchBlogWithDesignCombined("test-id", "en");

      expect(result).not.toBeNull();
      expect(result!.title).toBe("Test Title");
      expect(result!.design.theme_name).toBe("ai_competition");
    });

    it("returns null on fetch failure", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

      const result = await fetchBlogWithDesignCombined("test-id");

      expect(result).toBeNull();
    });
  });
});
