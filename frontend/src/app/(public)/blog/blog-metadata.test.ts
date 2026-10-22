import { describe, expect, it, vi } from "vitest";

const locale = vi.hoisted(() => ({ value: "en" }));
vi.mock("next-intl/server", async () => {
  const en = (await import("@/i18n/locales/en.json")).default;
  const pt = (await import("@/i18n/locales/pt.json")).default;
  return {
    getTranslations: (namespace: string) => {
      const messages = locale.value === "pt" ? pt : en;
      const byNamespace: Record<string, Record<string, unknown>> = {
        pageTitles: messages.pageTitles,
        blog: messages.blog,
      };
      return Promise.resolve((key: string) => {
        const value = byNamespace[namespace]?.[key];
        return typeof value === "string" ? value : key;
      });
    },
  };
});

import { generateMetadata } from "./page";

describe("/blog metadata", () => {
  // Scenario: Page Open Graph tags keep a type and the page description
  it.each([
    ["en", "Read the blog posts Pedro Marins has published."],
    ["pt", "Leia os posts que Pedro Marins publicou no blog."],
  ])(
    "has its own og:description and og:type in %s",
    async (lang, description) => {
      locale.value = lang;
      const metadata = await generateMetadata();
      const title = "Blog · Pedro Marins";
      expect(metadata.title).toBe(title);
      expect(metadata.description).toBe(description);
      expect(metadata.openGraph).toEqual({
        title,
        description,
        type: "website",
      });
    },
  );
});
