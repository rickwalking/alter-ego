import { describe, expect, it, vi } from "vitest";

const locale = vi.hoisted(() => ({ value: "en" }));
vi.mock("next-intl/server", async () => {
  const en = (await import("@/i18n/locales/en.json")).default;
  const pt = (await import("@/i18n/locales/pt.json")).default;
  return {
    getTranslations: (namespace: string) => {
      const titles: Record<string, string> = (locale.value === "pt" ? pt : en)
        .pageTitles;
      return Promise.resolve((key: string) =>
        namespace === "pageTitles" ? (titles[key] ?? key) : key,
      );
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
});
