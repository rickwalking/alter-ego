import { beforeEach, describe, expect, it, vi } from "vitest";
import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    get: (name: string) => (name === "locale" ? { value: "pt" } : undefined),
  })),
  // AE-0416: the request locale also reads Accept-Language.
  headers: vi.fn(async () => ({ get: () => null })),
}));

vi.mock("next-intl/server", () => ({
  getTranslations: vi.fn(async () => (key: string) => `blog.${key}`),
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

const VIEW = {
  title: "Opinião impopular",
  subtitle: "o modelo de IA não é o gargalo.",
  markdown: "# x",
  design: {
    ...FALLBACK_DESIGN_TOKENS,
    images: {
      ...FALLBACK_DESIGN_TOKENS.images,
      hero: "/api/carousels/p/images/slide_1.jpg?lang=pt",
    },
  },
};

beforeEach(() => {
  mockResolve.mockReset();
});

// Feature: Public blog renders correctly for anonymous visitors (AE-0412)
// Scenario: Each post page has its own metadata
describe("generateMetadata for /blog/[id]", () => {
  it("uses the post title, subtitle and hero", async () => {
    mockResolve.mockResolvedValue(VIEW);

    const metadata = await generateMetadata(props("post-1"));

    expect(mockResolve).toHaveBeenCalledWith("post-1", "pt");
    expect(metadata.title).toBe("Opinião impopular · blog.metaTitleSuffix");
    expect(metadata.description).toBe("o modelo de IA não é o gargalo.");
    expect(metadata.openGraph).toMatchObject({
      type: "article",
      images: ["/api/carousels/p/images/slide_1.jpg?lang=pt"],
    });
  });

  it("prefers the lang query over the cookie", async () => {
    mockResolve.mockResolvedValue(VIEW);
    await generateMetadata(props("post-1", "en"));
    expect(mockResolve).toHaveBeenCalledWith("post-1", "en");
  });

  it("truncates a long description and handles missing title and hero", async () => {
    mockResolve.mockResolvedValue({
      ...VIEW,
      title: "",
      subtitle: "x".repeat(300),
      design: FALLBACK_DESIGN_TOKENS,
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
