import { describe, it, expect } from "vitest";
import {
  API_ENDPOINTS,
  ROUTE_PATHS,
  HTTP_METHODS,
  CONTENT_TYPES,
  BLOG_LANGUAGES,
  DEFAULT_BLOG_LANGUAGE,
} from "@/constants/api";

describe("API_ENDPOINTS", () => {
  it("defines CAROUSELS endpoint", () => {
    expect(API_ENDPOINTS.CAROUSELS).toBe("/api/carousels");
  });

  // Scenario: API endpoints generate correct carousel URLs
  it("generates CAROUSEL_BLOG_LANG URL with id and language", () => {
    expect(API_ENDPOINTS.CAROUSEL_BLOG_LANG("abc-123", "pt")).toBe(
      "/api/carousels/abc-123/blog/pt",
    );
  });

  it("generates CAROUSEL_BLOG_LANG URL for English", () => {
    expect(API_ENDPOINTS.CAROUSEL_BLOG_LANG("xyz", "en")).toBe(
      "/api/carousels/xyz/blog/en",
    );
  });

  it("generates CAROUSEL_DESIGN URL", () => {
    expect(API_ENDPOINTS.CAROUSEL_DESIGN("id1")).toBe(
      "/api/carousels/id1/design",
    );
  });

  it("generates CAROUSEL_SLIDES URL", () => {
    expect(API_ENDPOINTS.CAROUSEL_SLIDES("id1")).toBe(
      "/api/carousels/id1/slides",
    );
  });

  it("generates CAROUSEL_IMAGE URL", () => {
    expect(API_ENDPOINTS.CAROUSEL_IMAGE("id1", "hero")).toBe(
      "/api/carousels/id1/images/hero",
    );
  });

  it("generates CAROUSEL_IMAGE URL with extension", () => {
    expect(API_ENDPOINTS.CAROUSEL_IMAGE("id1", "slide_1.jpg")).toBe(
      "/api/carousels/id1/images/slide_1.jpg",
    );
  });

  it("preserves DOCUMENTS endpoint", () => {
    expect(API_ENDPOINTS.DOCUMENTS).toBe("/api/documents");
  });

  it("preserves CONVERSATIONS endpoint with trailing slash", () => {
    expect(API_ENDPOINTS.CONVERSATIONS).toBe("/api/conversations");
  });

  it("preserves SEARCH endpoint", () => {
    expect(API_ENDPOINTS.SEARCH).toBe("/api/search");
  });
});

describe("ROUTE_PATHS", () => {
  it("defines HOME", () => {
    expect(ROUTE_PATHS.HOME).toBe("/");
  });

  it("defines CHAT", () => {
    expect(ROUTE_PATHS.CHAT).toBe("/chat");
  });

  it("defines KNOWLEDGE", () => {
    expect(ROUTE_PATHS.KNOWLEDGE).toBe("/knowledge");
  });

  it("defines BLOG", () => {
    expect(ROUTE_PATHS.BLOG).toBe("/blog");
  });

  it("generates BLOG_POST path with slug", () => {
    expect(ROUTE_PATHS.BLOG_POST("abc123")).toBe("/blog/abc123");
  });
});

describe("HTTP_METHODS", () => {
  it("defines GET", () => {
    expect(HTTP_METHODS.GET).toBe("GET");
  });

  it("defines POST", () => {
    expect(HTTP_METHODS.POST).toBe("POST");
  });

  it("defines PUT", () => {
    expect(HTTP_METHODS.PUT).toBe("PUT");
  });

  it("defines DELETE", () => {
    expect(HTTP_METHODS.DELETE).toBe("DELETE");
  });
});

describe("CONTENT_TYPES", () => {
  it("defines JSON", () => {
    expect(CONTENT_TYPES.JSON).toBe("application/json");
  });

  it("defines FORM_DATA", () => {
    expect(CONTENT_TYPES.FORM_DATA).toBe("multipart/form-data");
  });
});

describe("BLOG_LANGUAGES", () => {
  // Scenario: Blog languages constant has correct values
  it("maps PORTUGUESE to 'pt'", () => {
    expect(BLOG_LANGUAGES.PORTUGUESE).toBe("pt");
  });

  it("maps ENGLISH to 'en'", () => {
    expect(BLOG_LANGUAGES.ENGLISH).toBe("en");
  });
});

describe("DEFAULT_BLOG_LANGUAGE", () => {
  // Scenario: Default blog language is Portuguese
  it("equals 'pt'", () => {
    expect(DEFAULT_BLOG_LANGUAGE).toBe("pt");
  });

  it("matches BLOG_LANGUAGES.PORTUGUESE", () => {
    expect(DEFAULT_BLOG_LANGUAGE).toBe(BLOG_LANGUAGES.PORTUGUESE);
  });
});
