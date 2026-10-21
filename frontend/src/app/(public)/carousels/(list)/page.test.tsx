import { describe, expect, it, vi } from "vitest";

vi.mock("next-intl/server", () => ({
  getTranslations: vi.fn(() =>
    Promise.resolve((key: string) => `carousels.${key}`),
  ),
}));

import { generateMetadata } from "./page";

describe("Public carousels page metadata (AE-0444)", () => {
  it("has its own metadata", async () => {
    const metadata = await generateMetadata();

    expect(metadata).toMatchObject({
      title: "carousels.metaTitle",
      description: "carousels.metaDescription",
      openGraph: {
        title: "carousels.metaTitle",
        description: "carousels.metaDescription",
        type: "website",
      },
    });
  });
});
