import { describe, expect, it } from "vitest";
import {
  buildPublicCarouselCards,
  carouselLanguageTag,
  carouselNeighbors,
  carouselSubtitle,
  carouselTitle,
  publicCarouselSubtitle,
  publicCarouselTitle,
  publicCarouselCoverUrl,
  resolveCarouselLanguage,
  toPublicCarouselCard,
} from "@/lib/public-carousels";
import type {
  CarouselProjectListResponse,
  CarouselPublicResponse,
} from "@/schemas/carousel";

type Project = CarouselProjectListResponse["items"][number];

function project(overrides: Partial<Project> = {}): Project {
  return {
    id: "proj-1",
    topic: "Raw topic",
    audience: "Devs",
    niche: "AI",
    language: "pt-BR",
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
        slides: ["/api/carousels/proj-1/images/slide_1.jpg"],
        rendered_slides_pt: [
          "/api/carousels/proj-1/slide-images/pt/slide_1.jpg",
          "/api/carousels/proj-1/slide-images/pt/slide_2.jpg",
        ],
        rendered_slides_en: [
          "/api/carousels/proj-1/slide-images/en/slide_1.jpg",
          "/api/carousels/proj-1/slide-images/en/slide_2.jpg",
          "/api/carousels/proj-1/slide-images/en/slide_3.jpg",
        ],
      },
    },
    created_at: "2026-10-20T11:40:01Z",
    updated_at: "2026-10-20T15:00:37Z",
    ...overrides,
  };
}

function publicCarousel(
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
        { slide_number: 2, heading: "Segundo", image_url: "/pt-2.jpg" },
      ],
      en: [{ slide_number: 1, heading: "Opening", image_url: "/en-1.jpg" }],
    },
    cover_url: "/pt-1.jpg",
    ...overrides,
  };
}

describe("public carousel cards (AE-0444)", () => {
  it("maps a project to a localized card with a public cover", () => {
    const card = toPublicCarouselCard(project(), "pt", "Sem título");

    expect(card).toMatchObject({
      id: "proj-1",
      title: "Título PT",
      createdAt: "2026-10-20T11:40:01Z",
      language: "pt-BR",
      slideCount: 3,
      href: "/carousels/proj-1",
      coverUrl: "/api/carousels/proj-1/slide-images/pt/slide_1.jpg",
    });
  });

  // Scenario: The gallery shows each cover in the reader's language
  it("uses the English slide 1 as the cover for an English reader", () => {
    const card = toPublicCarouselCard(project(), "en", "Untitled");

    expect(card.coverUrl).toBe(
      "/api/carousels/proj-1/slide-images/en/slide_1.jpg",
    );
  });

  // Scenario: The gallery shows each cover in the reader's language
  it("maps a stored preview cover to the public route in that language", () => {
    const card = toPublicCarouselCard(
      project({
        design_tokens: {
          images: {
            hero: "/api/carousels/proj-1/preview/images/slide_1.jpg?lang=pt",
            rendered_slides_en: [
              "/api/carousels/proj-1/preview/images/slide_1.jpg?lang=en",
            ],
          },
        },
      }),
      "en",
      "Untitled",
    );

    expect(card.coverUrl).toBe(
      "/api/carousels/proj-1/images/slide_1.jpg?lang=en",
    );
  });

  // Scenario: The gallery shows each cover in the reader's language
  it("falls back to the hero when the reader's language has no render", () => {
    const card = toPublicCarouselCard(
      project({
        design_tokens: {
          images: {
            hero: "/api/carousels/proj-1/preview/images/slide_1.jpg?lang=pt",
          },
        },
      }),
      "en",
      "Untitled",
    );

    expect(card.coverUrl).toBe(
      "/api/carousels/proj-1/images/slide_1.jpg?lang=pt",
    );
  });

  it("prefers the English title and falls back to the topic", () => {
    const english = toPublicCarouselCard(project(), "en", "Untitled");
    const fallback = toPublicCarouselCard(
      project({ title: null, title_en: null, topic: "Topic fallback" }),
      "pt",
      "Sem título",
    );

    expect(english.title).toBe("Title EN");
    expect(fallback.title).toBe("Topic fallback");
  });

  it("uses the fallback title when every candidate is a placeholder", () => {
    const card = toPublicCarouselCard(
      project({ title: "Slide 1", title_en: null, topic: "" }),
      "pt",
      "Sem título",
    );

    expect(card.title).toBe("Sem título");
  });

  it("falls back to the first slide when the hero is missing", () => {
    const card = toPublicCarouselCard(
      project({
        design_tokens: {
          images: { slides: ["/api/carousels/proj-1/images/slide_2.jpg"] },
        },
      }),
      "pt",
      "Sem título",
    );

    expect(card.coverUrl).toBe("/api/carousels/proj-1/images/slide_2.jpg");
  });

  it("has no cover or slide count without design tokens", () => {
    const card = toPublicCarouselCard(
      project({ design_tokens: null, slide_count: null }),
      "pt",
      "Sem título",
    );

    expect(card.coverUrl).toBeNull();
    expect(card.slideCount).toBeNull();
  });

  it("uses the stored slide_count when tokens carry no image lists", () => {
    const card = toPublicCarouselCard(
      project({ design_tokens: { images: {} }, slide_count: 7 }),
      "pt",
      "Sem título",
    );

    expect(card.slideCount).toBe(7);
  });

  it("builds a card per feed item", () => {
    const cards = buildPublicCarouselCards(
      [project(), project({ id: "proj-2" })],
      "pt",
      "Sem título",
    );

    expect(cards.map((card) => card.id)).toEqual(["proj-1", "proj-2"]);
  });
});

describe("public carousel share image", () => {
  // Scenario: The viewer shares the cover in the shown language
  it("uses slide 1 of the shown language", () => {
    expect(publicCarouselCoverUrl(publicCarousel(), "en")).toBe("/en-1.jpg");
    expect(publicCarouselCoverUrl(publicCarousel(), "pt")).toBe("/pt-1.jpg");
  });

  // Scenario: The viewer shares the cover in the shown language
  it("falls back to the API cover when the language has no slides", () => {
    const carousel = publicCarousel({
      slides_by_language: {},
      cover_url: "/cover.jpg",
    });
    expect(publicCarouselCoverUrl(carousel, "en")).toBe("/cover.jpg");
  });
});

describe("carousel language + text helpers (AE-0444)", () => {
  it("renders a short uppercase language tag", () => {
    expect(carouselLanguageTag("pt-BR")).toBe("PT");
    expect(carouselLanguageTag("en-US")).toBe("EN");
    expect(carouselLanguageTag("")).toBe("PT");
  });

  it("resolves the requested language, then the UI locale", () => {
    const carousel = publicCarousel();

    expect(resolveCarouselLanguage(carousel, "en", "pt")).toBe("en");
    expect(resolveCarouselLanguage(carousel, "xx", "en")).toBe("en");
    expect(resolveCarouselLanguage(carousel, undefined, "pt")).toBe("pt");
  });

  it("falls back to the first available language", () => {
    const carousel = publicCarousel({ available_languages: ["en"] });

    expect(resolveCarouselLanguage(carousel, "pt", "pt")).toBe("en");
  });

  it("cleans emphasis markup and skips blank candidates", () => {
    expect(carouselTitle(["<strong>Title</strong>"], "Fallback")).toBe("Title");
    expect(carouselSubtitle([null, "  ", "A **subtitle**"])).toBe("A subtitle");
  });

  it("localizes the public projection title and subtitle", () => {
    const carousel = publicCarousel();

    expect(publicCarouselTitle(carousel, "en", "Untitled")).toBe("Title EN");
    expect(publicCarouselSubtitle(carousel, "en")).toBe("Subtitle EN");
    expect(publicCarouselTitle(carousel, "pt", "Sem título")).toBe("Título PT");
  });

  // Scenario: An untitled carousel is titled with its topic
  it("titles an untitled projection with its topic", () => {
    const carousel = publicCarousel({
      title: null,
      title_en: null,
      topic: "GPT 5.6 saiu",
    });

    expect(publicCarouselTitle(carousel, "pt", "Sem título")).toBe(
      "GPT 5.6 saiu",
    );
    expect(publicCarouselTitle(carousel, "en", "Untitled")).toBe(
      "GPT 5.6 saiu",
    );
  });

  // Scenario: A localized title still wins over the topic
  it("prefers a localized title over the topic", () => {
    const carousel = publicCarousel({ topic: "Raw topic" });

    expect(publicCarouselTitle(carousel, "en", "Untitled")).toBe("Title EN");
  });

  // Scenario: A carousel with neither title nor topic uses the localized fallback
  it("uses the localized fallback without a title or topic", () => {
    const carousel = publicCarousel({
      title: null,
      title_en: null,
      topic: null,
    });

    expect(publicCarouselTitle(carousel, "pt", "Sem título")).toBe(
      "Sem título",
    );
  });
});

describe("carousel neighbors (AE-0444)", () => {
  const items = [
    project({ id: "a" }),
    project({ id: "b" }),
    project({ id: "c" }),
  ];

  it("links the previous and next carousel in feed order", () => {
    const neighbors = carouselNeighbors({
      items,
      currentId: "b",
      locale: "pt",
      fallbackTitle: "Sem título",
    });

    expect(neighbors.previous?.href).toBe("/carousels/a");
    expect(neighbors.next?.href).toBe("/carousels/c");
  });

  it("has no neighbors at the edges or for an unknown id", () => {
    const first = carouselNeighbors({
      items,
      currentId: "a",
      locale: "pt",
      fallbackTitle: "Sem título",
    });
    const missing = carouselNeighbors({
      items,
      currentId: "z",
      locale: "pt",
      fallbackTitle: "Sem título",
    });

    expect(first.previous).toBeNull();
    expect(first.next?.id).toBe("b");
    expect(missing).toEqual({ previous: null, next: null });
  });
});
