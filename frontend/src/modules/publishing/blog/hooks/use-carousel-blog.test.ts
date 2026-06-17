import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import {
  useCarouselProject,
  useCarouselProjects,
  useCarouselBlogPosts,
  useCarouselBlog,
  useCarouselBlogWithDesign,
  useCarouselDesign,
  useCarouselSlides,
} from "@/modules/publishing/blog/hooks/use-carousel-blog";
import { API_ENDPOINTS, DEFAULT_BLOG_LANGUAGE } from "@/constants/api";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";
const mockApiCall = vi.mocked(apiCall);

const MOCK_PROJECT = {
  id: "abc-123",
  topic: "Gemma 4",
  audience: "Developers",
  niche: "AI/ML",
  title: "Gemma 4 Deep Dive",
  subtitle: "Understanding Google's Latest Model",
  theme: "ai_competition",
  status: "completed",
  blog_markdown: "# Content",
  blog_translations: { pt: "# Conteúdo", en: "# Content" },
  caption: "Check this out!",
  design_tokens: null,
  created_at: "2026-04-20T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
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
    hero: "/api/carousels/abc-123/images/hero",
    slides: ["/api/carousels/abc-123/images/slide_1.jpg"],
  },
  layout: {
    badge_label: "AI/ML",
    swipe_text: "Deslize →",
    progress_segments: 7,
  },
  theme_name: "ai_competition",
};

const MOCK_BLOG = {
  markdown: "# Gemma 4\n\nContent here",
  title: "Gemma 4 Deep Dive",
  subtitle: "Understanding the model",
  language: "pt",
  available_languages: ["pt", "en"],
};

const MOCK_BLOG_WITH_DESIGN = {
  ...MOCK_BLOG,
  design: MOCK_DESIGN,
};

const MOCK_SLIDE = {
  id: "slide-1",
  slide_number: 1,
  slide_type: "content",
  heading: "Introduction",
  body: "Slide body",
  image_path: null,
  created_at: "2026-04-20T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useCarouselProject", () => {
  // Scenario: useCarouselProject hook constructs correct query
  it("fetches a single project by ID", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCarouselProject("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_PROJECT);
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSELS + "/abc-123",
      expect.anything(),
    );
  });

  it("is disabled when ID is empty", () => {
    const { result } = renderHook(() => useCarouselProject(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("uses the correct query key with project ID", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCarouselProject("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_PROJECT);
  });
});

describe("useCarouselProjects", () => {
  it("fetches all projects without status filter", async () => {
    const mockResponse = {
      items: [MOCK_PROJECT],
      total: 1,
      limit: 20,
      offset: 0,
    };
    mockApiCall.mockResolvedValueOnce(mockResponse);
    const { result } = renderHook(() => useCarouselProjects(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockResponse);
  });

  it("fetches projects with status filter", async () => {
    const mockResponse = {
      items: [MOCK_PROJECT],
      total: 1,
      limit: 20,
      offset: 0,
    };
    mockApiCall.mockResolvedValueOnce(mockResponse);
    const { result } = renderHook(() => useCarouselProjects("completed"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      expect.stringContaining("status=completed"),
      expect.anything(),
    );
  });
});

describe("useCarouselBlogPosts", () => {
  it("fetches completed carousel projects", async () => {
    const mockResponse = {
      items: [MOCK_PROJECT],
      total: 1,
      limit: 20,
      offset: 0,
    };
    mockApiCall.mockResolvedValueOnce(mockResponse);
    const { result } = renderHook(() => useCarouselBlogPosts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockResponse);
    expect(mockApiCall).toHaveBeenCalledWith(
      expect.stringContaining("status=completed"),
      expect.anything(),
    );
  });
});

describe("useCarouselBlog", () => {
  // Scenario: useCarouselBlog uses default language
  it("uses default language when none specified", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_BLOG);
    const { result } = renderHook(() => useCarouselBlog("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_BLOG_LANG("abc-123", DEFAULT_BLOG_LANGUAGE),
      expect.anything(),
    );
  });

  it("uses specified language when provided", async () => {
    mockApiCall.mockResolvedValueOnce({ ...MOCK_BLOG, language: "en" });
    const { result } = renderHook(() => useCarouselBlog("abc-123", "en"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_BLOG_LANG("abc-123", "en"),
      expect.anything(),
    );
  });

  it("is disabled when ID is empty", () => {
    const { result } = renderHook(() => useCarouselBlog(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useCarouselBlogWithDesign", () => {
  it("fetches blog with design tokens", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_BLOG_WITH_DESIGN);
    const { result } = renderHook(
      () => useCarouselBlogWithDesign("abc-123", "pt"),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_BLOG_WITH_DESIGN);
    expect(mockApiCall).toHaveBeenCalledWith(
      expect.stringContaining("include_design=true"),
      expect.anything(),
    );
  });

  it("is disabled when ID is empty", () => {
    const { result } = renderHook(() => useCarouselBlogWithDesign(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useCarouselDesign", () => {
  it("fetches design tokens for a carousel", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_DESIGN);
    const { result } = renderHook(() => useCarouselDesign("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_DESIGN);
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_DESIGN("abc-123"),
      expect.anything(),
    );
  });

  it("is disabled when ID is empty", () => {
    const { result } = renderHook(() => useCarouselDesign(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useCarouselSlides", () => {
  it("fetches slides for a carousel", async () => {
    mockApiCall.mockResolvedValueOnce([MOCK_SLIDE]);
    const { result } = renderHook(() => useCarouselSlides("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([MOCK_SLIDE]);
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_SLIDES("abc-123"),
      expect.anything(),
    );
  });

  it("is disabled when ID is empty", () => {
    const { result } = renderHook(() => useCarouselSlides(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});
