import { beforeEach, describe, expect, it, vi } from "vitest";
import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";
import { resolvePublicBlogView } from "./public-blog";

// Feature: Public blog renders the v2 document (AE-0423)
// frontend/tests/features/blog_sections_ae0423.feature
// (also public-blog-detail.feature, public-blog-polish-ae0412.feature,
//  blog_no_carousel_slides_ae0422.feature)

vi.mock("@/lib/server-fetch", () => ({
  fetchPublicBlogPost: vi.fn(),
  fetchCarouselDesign: vi.fn(),
}));

import * as serverFetch from "@/lib/server-fetch";
import { fetchCarouselDesign, fetchPublicBlogPost } from "@/lib/server-fetch";

const mockFetchPost = vi.mocked(fetchPublicBlogPost);
const mockFetchDesign = vi.mocked(fetchCarouselDesign);

const PT_DOCUMENT = {
  schema: "blog.v2",
  cover: { url: "https://cdn.example/cover.jpg", alt: "Capa" },
  sections: [
    {
      id: "sec_1",
      heading: "O que aconteceu",
      body_md: "Por que <strong>importa</strong>?",
      image: { url: "https://cdn.example/s1.jpg", alt: "Diagrama do fluxo" },
    },
    { id: "sec_2", heading: "Depois", body_md: "Fim.", image: null },
  ],
  translations: {
    en: {
      schema: "blog.v2",
      cover: null,
      sections: [
        { id: "sec_3", heading: "What happened", body_md: "EN.", image: null },
      ],
    },
  },
};

const STANDALONE_POST = {
  id: "post-1",
  slug: "post-1",
  title: "Standalone post",
  excerpt: "An excerpt",
  featured_image_url: "https://cdn.example/cover.jpg",
  published_at: "2026-07-01T00:00:00Z",
  keywords: [],
  origin: "standalone",
  project_id: null,
  content: PT_DOCUMENT,
};

const CAROUSEL_POST = {
  ...STANDALONE_POST,
  id: "post-2",
  origin: "carousel",
  project_id: "project-9",
};

const DESIGN = {
  ...FALLBACK_DESIGN_TOKENS,
  theme_name: "designed-theme",
  images: {
    hero: "/api/carousels/p/preview/images/slide_1.jpg?lang=en",
    slides: ["/api/carousels/p/slide-images/en/slide_2.jpg"],
    rendered_slides_pt: ["/api/carousels/p/slide-images/pt/slide_1.jpg"],
    rendered_slides_en: null,
  },
};

beforeEach(() => {
  mockFetchPost.mockReset();
  mockFetchDesign.mockReset();
});

describe("resolvePublicBlogView (AE-0423 v2 render)", () => {
  // Scenario: The cover renders as the article hero
  // Scenario: Each section renders its own heading, body and image
  it("renders the post's own cover and sections with the default theme", async () => {
    mockFetchPost.mockResolvedValue(STANDALONE_POST);

    const view = await resolvePublicBlogView("post-1", "pt");

    expect(view?.title).toBe("Standalone post");
    expect(view?.subtitle).toBe("An excerpt");
    expect(view?.cover).toEqual({
      url: "https://cdn.example/cover.jpg",
      alt: "Capa",
    });
    expect(view?.sections.map((s) => s.heading)).toEqual([
      "O que aconteceu",
      "Depois",
    ]);
    expect(view?.sections[0].image?.alt).toBe("Diagrama do fluxo");
    expect(view?.sections[1].image).toBeNull();
    expect(view?.design.theme_name).toBe(FALLBACK_DESIGN_TOKENS.theme_name);
    expect(mockFetchDesign).not.toHaveBeenCalled();
  });

  // Scenario: Emphasis markup in the body is rendered as emphasis (AE-0412)
  it("converts emphasis HTML in section bodies to markdown", async () => {
    mockFetchPost.mockResolvedValue(STANDALONE_POST);
    const view = await resolvePublicBlogView("post-1", "pt");
    expect(view?.sections[0].body_md).toBe("Por que **importa**?");
  });

  // Scenario: No carousel slide image is ever used
  // Scenario: The public read never fetches carousel blog markdown
  it("themes a carousel-origin post from its design but takes no design image", async () => {
    mockFetchPost.mockResolvedValue(CAROUSEL_POST);
    mockFetchDesign.mockResolvedValue(DESIGN);

    const view = await resolvePublicBlogView("post-2", "pt");

    expect(mockFetchDesign).toHaveBeenCalledWith("project-9", "pt");
    expect(view?.design.theme_name).toBe("designed-theme");
    expect(view?.design.images.hero).toBe("");
    expect(view?.design.images.slides).toEqual([]);
    expect(view?.design.images.rendered_slides_pt).toBeNull();
    expect(JSON.stringify(view)).not.toContain("/slide-images/");
    expect(view?.sections).toHaveLength(2);
    expect(Object.keys(serverFetch)).not.toContain("fetchBlogWithDesign");
  });

  it("falls back to the default theme when the design fetch fails (never 404)", async () => {
    mockFetchPost.mockResolvedValue(CAROUSEL_POST);
    mockFetchDesign.mockResolvedValue(null);

    const view = await resolvePublicBlogView("post-2", "pt");
    expect(view?.design.theme_name).toBe(FALLBACK_DESIGN_TOKENS.theme_name);
  });

  // Scenario: An English translation renders under the en locale
  // Scenario: PT/EN content buttons switch the rendered document
  it("renders the EN translation and keeps the PT cover when EN has none", async () => {
    mockFetchPost.mockResolvedValue(STANDALONE_POST);
    const view = await resolvePublicBlogView("post-1", "en");
    expect(view?.sections.map((s) => s.heading)).toEqual(["What happened"]);
    expect(view?.cover?.url).toBe("https://cdn.example/cover.jpg");
  });

  it("falls back to PT when the translation is absent (never 404)", async () => {
    mockFetchPost.mockResolvedValue({
      ...STANDALONE_POST,
      content: { ...PT_DOCUMENT, translations: {} },
    });
    const view = await resolvePublicBlogView("post-1", "en");
    expect(view?.sections[0].heading).toBe("O que aconteceu");
  });

  // Scenario: A carousel-origin post with no v2 row is 404
  // Scenario: An unpublished v2 post is not publicly viewable
  it("returns null (not-found) when the public API has no post", async () => {
    mockFetchPost.mockResolvedValue(null);
    expect(await resolvePublicBlogView("project-9", "pt")).toBeNull();
    expect(mockFetchDesign).not.toHaveBeenCalled();
  });

  // Scenario: A non-v2 content blob is rejected by the parse helper
  it("fails safe to not-found on a non-v2 content blob", async () => {
    mockFetchPost.mockResolvedValue({
      ...STANDALONE_POST,
      content: { markdown: "# legacy" },
    });
    expect(await resolvePublicBlogView("post-1", "pt")).toBeNull();
  });

  // Scenario: Every title candidate is a placeholder (AE-0412)
  it("returns an empty title for a placeholder", async () => {
    mockFetchPost.mockResolvedValue({ ...STANDALONE_POST, title: "slide" });
    const view = await resolvePublicBlogView("post-1", "pt");
    expect(view?.title).toBe("");
  });

  // Scenario: A subtitle equal to the title is not repeated (AE-0412)
  it("drops a subtitle that repeats the title", async () => {
    mockFetchPost.mockResolvedValue({
      ...STANDALONE_POST,
      excerpt: "Standalone <b>post</b>",
    });
    const view = await resolvePublicBlogView("post-1", "pt");
    expect(view?.subtitle).toBeNull();
  });

  it("maps owner-only preview image URLs to the public route", async () => {
    mockFetchPost.mockResolvedValue({
      ...STANDALONE_POST,
      excerpt: null,
      content: {
        ...PT_DOCUMENT,
        cover: {
          url: "/api/carousels/p/preview/images/hero.jpg?lang=pt",
          alt: "Capa",
        },
      },
    });
    const view = await resolvePublicBlogView("post-1", "pt");
    expect(view?.cover?.url).toBe("/api/carousels/p/images/hero.jpg?lang=pt");
    expect(view?.subtitle).toBeNull();
  });
});
