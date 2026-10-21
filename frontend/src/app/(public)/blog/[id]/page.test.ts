import { beforeEach, describe, expect, it, vi } from "vitest";
import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve({
      get: (name: string) => (name === "locale" ? { value: "pt" } : undefined),
    }),
  ),
  headers: vi.fn(() => Promise.resolve({ get: () => null })),
}));

vi.mock("next-intl/server", () => ({
  getTranslations: vi.fn(() => Promise.resolve((key: string) => `blog.${key}`)),
}));

vi.mock("@/lib/public-blog", () => ({
  resolvePublicBlogView: vi.fn(),
}));

import { resolvePublicBlogView } from "@/lib/public-blog";
import { generateMetadata } from "./page";

const mockResolve = vi.mocked(resolvePublicBlogView);

function props(id: string, lang?: string) {
  return {
    params: Promise.resolve({ id }),
    searchParams: Promise.resolve(lang ? { lang } : {}),
  };
}

/**
 * A view carrying the post's own v2 cover and sections; the OG image must be
 * that cover, never a carousel design image.
 */
const VIEW = {
  title: "Opinião impopular",
  subtitle: "o modelo de IA não é o gargalo.",
  cover: { url: "https://cdn.example/cover.jpg", alt: "Capa" },
  sections: [{ id: "sec_1", heading: null, body_md: "x", image: null }],
  design: FALLBACK_DESIGN_TOKENS,
};

beforeEach(() => {
  mockResolve.mockReset();
});

// Scenario: Each post page has its own metadata
describe("generateMetadata for /blog/[id]", () => {
  it("uses the post title, subtitle and cover", async () => {
    mockResolve.mockResolvedValue(VIEW);

    const metadata = await generateMetadata(props("post-1"));

    expect(mockResolve).toHaveBeenCalledWith("post-1", "pt");
    expect(metadata.title).toBe("Opinião impopular · blog.metaTitleSuffix");
    expect(metadata.description).toBe("o modelo de IA não é o gargalo.");
    expect(metadata.openGraph).toMatchObject({
      type: "article",
      images: ["https://cdn.example/cover.jpg"],
    });
  });

  it("prefers the lang query over the cookie", async () => {
    mockResolve.mockResolvedValue(VIEW);
    await generateMetadata(props("post-1", "en"));
    expect(mockResolve).toHaveBeenCalledWith("post-1", "en");
  });

  // Scenario: The listing card uses a fallback when the cover is null
  it("truncates a long description and handles missing title and cover", async () => {
    mockResolve.mockResolvedValue({
      ...VIEW,
      title: "",
      subtitle: "x".repeat(300),
      cover: null,
    });

    const metadata = await generateMetadata(props("post-2", "xx"));

    expect(metadata.title).toBe("blog.untitledPost · blog.metaTitleSuffix");
    expect(metadata.description).toHaveLength(160);
    expect(String(metadata.description).endsWith("…")).toBe(true);
    expect(metadata.openGraph?.images).toBeUndefined();
  });

  it("omits the description without a subtitle", async () => {
    mockResolve.mockResolvedValue({ ...VIEW, subtitle: null });
    const metadata = await generateMetadata(props("post-3"));
    expect(metadata.description).toBeUndefined();
  });

  // Scenario: Metadata for an unknown post
  it("keeps the generic site metadata for an unknown post", async () => {
    mockResolve.mockResolvedValue(null);
    expect(await generateMetadata(props("missing"))).toEqual({});
  });
});
