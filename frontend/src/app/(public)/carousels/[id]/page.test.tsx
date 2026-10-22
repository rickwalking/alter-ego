import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CarouselPublicResponse } from "@/schemas/carousel";

vi.mock("@/i18n/request-locale", () => ({
  getRequestLocale: vi.fn(() => Promise.resolve("pt")),
}));

vi.mock("next-intl/server", () => ({
  getTranslations: vi.fn(() =>
    Promise.resolve((key: string) => `carousels.${key}`),
  ),
}));

vi.mock("@/lib/server-fetch", () => ({
  fetchPublicCarousel: vi.fn(),
  fetchPublicCarousels: vi.fn(),
}));

import { fetchPublicCarousel } from "@/lib/server-fetch";
import { generateMetadata } from "./page";

const mockFetch = vi.mocked(fetchPublicCarousel);

function carousel(
  overrides: Partial<CarouselPublicResponse> = {},
): CarouselPublicResponse {
  return {
    id: "proj-1",
    title: "Título PT",
    title_en: "Title EN",
    subtitle: "Subtítulo PT",
    subtitle_en: "Subtitle EN",
    language: "pt-BR",
    created_at: "2026-10-20T11:40:01Z",
    slide_count: 2,
    available_languages: ["pt", "en"],
    slides_by_language: {
      pt: [
        { slide_number: 1, heading: "Abertura", image_url: "/pt-1.jpg" },
        { slide_number: 2, heading: "Contexto", image_url: "/pt-2.jpg" },
      ],
      en: [
        { slide_number: 1, heading: "Opening", image_url: "/en-1.jpg" },
        { slide_number: 2, heading: "Context", image_url: "/en-2.jpg" },
      ],
    },
    cover_url: "/pt-1.jpg",
    ...overrides,
  };
}

function props(id: string, lang?: string) {
  return {
    params: Promise.resolve({ id }),
    searchParams: Promise.resolve(lang ? { lang } : {}),
  };
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("Public carousel viewer page metadata (AE-0444)", () => {
  it("uses the English title, subtitle and cover", async () => {
    // Scenario: A carousel share image uses the production domain
    mockFetch.mockResolvedValueOnce(carousel());

    const metadata = await generateMetadata(props("meta-en", "en"));

    expect(metadata.title).toBe("Title EN · carousels.metaTitleSuffix");
    expect(metadata.description).toBe("Subtitle EN");
    expect(metadata.openGraph).toMatchObject({
      type: "article",
      images: ["https://marinssolutions.com/pt-1.jpg"],
    });
  });

  it("serves og:image and twitter:image from the production domain", async () => {
    // Scenario: A carousel share image uses the production domain
    mockFetch.mockResolvedValueOnce(carousel());

    const metadata = await generateMetadata(props("meta-share", "en"));
    const shareImages = [
      ...[metadata.openGraph?.images ?? []].flat(),
      ...[metadata.twitter?.images ?? []].flat(),
    ].map(String);

    expect(shareImages).toEqual([
      "https://marinssolutions.com/pt-1.jpg",
      "https://marinssolutions.com/pt-1.jpg",
    ]);
    expect(shareImages.some((url) => url.includes("alterego.app"))).toBe(false);
  });

  it("falls back to the UI locale for an unknown lang", async () => {
    mockFetch.mockResolvedValueOnce(carousel());

    const metadata = await generateMetadata(props("meta-fallback", "xx"));

    expect(metadata.title).toBe("Título PT · carousels.metaTitleSuffix");
  });

  it("falls back to the generic description and omits the OG image", async () => {
    mockFetch.mockResolvedValueOnce(
      carousel({ subtitle: null, subtitle_en: null, cover_url: null }),
    );

    const metadata = await generateMetadata(props("meta-empty", "pt"));

    expect(metadata.description).toBe("carousels.metaDescription");
    expect(metadata.openGraph?.images).toBeUndefined();
  });

  // Scenario: An untitled carousel is titled with its topic
  it("titles an untitled carousel with its topic", async () => {
    mockFetch.mockResolvedValueOnce(
      carousel({ title: null, title_en: null, topic: "GPT 5.6 saiu" }),
    );

    const metadata = await generateMetadata(props("meta-topic", "pt"));

    expect(metadata.title).toBe("GPT 5.6 saiu · carousels.metaTitleSuffix");
    expect(metadata.openGraph?.title).toBe(metadata.title);
    expect(metadata.twitter?.title).toBe(metadata.title);
  });

  it("keeps generic metadata for an unknown carousel", async () => {
    mockFetch.mockResolvedValueOnce(null);

    expect(await generateMetadata(props("meta-missing"))).toEqual({});
  });
});
