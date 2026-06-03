import { describe, it, expect } from "vitest";
import {
  appendCacheBuster,
  slideUrlsForPublishPanel,
  toAuthenticatedPreviewSlideUrl,
  toPublicCarouselImageUrl,
} from "@/lib/carousel-media-url";

describe("carousel-media-url", () => {
  it("appends cache buster with ? when no query exists", () => {
    expect(
      appendCacheBuster("/api/carousels/id/images/slide_1.jpg", "v1"),
    ).toBe("/api/carousels/id/images/slide_1.jpg?v=v1");
  });

  it("appends cache buster with & when lang query exists", () => {
    expect(
      appendCacheBuster(
        "/api/carousels/id/preview/images/slide_1.jpg?lang=pt",
        "v1",
      ),
    ).toBe("/api/carousels/id/preview/images/slide_1.jpg?lang=pt&v=v1");
  });

  it("rewrites public hero paths to authenticated preview routes", () => {
    expect(
      toAuthenticatedPreviewSlideUrl(
        "/api/carousels/proj-1/images/slide_1",
        "proj-1",
        "pt",
      ),
    ).toBe("/api/carousels/proj-1/preview/images/slide_1.jpg?lang=pt");
  });

  it("rewrites rendered slide paths to authenticated preview routes", () => {
    expect(
      toAuthenticatedPreviewSlideUrl(
        "/api/carousels/proj-1/slide-images/pt/slide_2.jpg",
        "proj-1",
        "en",
      ),
    ).toBe("/api/carousels/proj-1/preview/images/slide_2.jpg?lang=en");
  });

  it("rewrites authenticated preview URLs to public image routes", () => {
    expect(
      toPublicCarouselImageUrl(
        "/api/carousels/proj-1/preview/images/hero.jpg?lang=pt",
      ),
    ).toBe("/api/carousels/proj-1/images/hero.jpg");
    expect(
      toPublicCarouselImageUrl("/api/carousels/proj-1/images/slide_1.jpg"),
    ).toBe("/api/carousels/proj-1/images/slide_1.jpg");
  });

  it("builds publish panel slide URLs with preview routes and cache buster", () => {
    expect(
      slideUrlsForPublishPanel(
        "proj-1",
        ["/api/carousels/proj-1/preview/images/slide_1.jpg?lang=pt"],
        "pt",
        "2026-04-20T00:00:00Z",
      ),
    ).toEqual([
      "/api/carousels/proj-1/preview/images/slide_1.jpg?lang=pt&v=2026-04-20T00%3A00%3A00Z",
    ]);
  });
});
