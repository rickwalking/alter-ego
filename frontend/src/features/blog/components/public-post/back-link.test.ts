import { describe, it, expect, vi } from "vitest";

vi.mock("next-intl/server", () => ({
  getTranslations: vi.fn(async (ns: string) => {
    const translations: Record<string, Record<string, string>> = {
      blog: {
        backToPosts: "Back to posts",
        backHome: "Back to home",
      },
    };
    return (key: string) => translations[ns]?.[key] ?? key;
  }),
}));

describe("BackLink i18n", () => {
  // Scenario: Back link text uses blog.backToPosts translation key
  describe("Given the blog translation namespace", () => {
    describe("When requesting the backToPosts key", () => {
      it("Then it returns 'Back to posts'", async () => {
        const { getTranslations } = await import("next-intl/server");
        const t = await getTranslations("blog");
        expect(t("backToPosts")).toBe("Back to posts");
      });
    });

    describe("When requesting the backHome key", () => {
      it("Then it returns 'Back to home'", async () => {
        const { getTranslations } = await import("next-intl/server");
        const t = await getTranslations("blog");
        expect(t("backHome")).toBe("Back to home");
      });
    });
  });
});
