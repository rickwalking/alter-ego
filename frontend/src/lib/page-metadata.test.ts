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

import { pageMetadata } from "./page-metadata";

describe("pageMetadata", () => {
  // Scenario: Dashboard pages have their own titles
  it("names the page and the site in the title and og:title", async () => {
    locale.value = "en";
    const metadata = await pageMetadata("calendar");
    expect(metadata.title).toBe("Calendar · Pedro Marins");
    expect(metadata.openGraph?.title).toBe("Calendar · Pedro Marins");
  });

  // Scenario: Titles follow the interface language
  it("uses the interface language", async () => {
    locale.value = "pt";
    expect((await pageMetadata("calendar")).title).toBe(
      "Calendário · Pedro Marins",
    );
    locale.value = "en";
  });

  // Scenario: Page Open Graph tags keep a type and the page description
  it("keeps og:type on a page without a description", async () => {
    locale.value = "en";
    const metadata = await pageMetadata("calendar");
    expect(metadata.openGraph).toEqual({
      title: "Calendar · Pedro Marins",
      type: "website",
    });
    expect(metadata.description).toBeUndefined();
  });
});
