import { describe, expect, it, vi } from "vitest";
import { DEFAULT_LOCALE } from "./config";
import { matchAcceptLanguage, resolveLocale } from "./locale";

const headerValues = vi.hoisted(() => ({
  cookie: undefined as string | undefined,
  acceptLanguage: null as string | null,
}));

vi.mock("next/headers", () => ({
  cookies: () =>
    Promise.resolve({
      get: (name: string) =>
        name === "locale" && headerValues.cookie !== undefined
          ? { value: headerValues.cookie }
          : undefined,
    }),
  headers: () =>
    Promise.resolve({
      get: (name: string) =>
        name === "accept-language" ? headerValues.acceptLanguage : null,
    }),
}));

describe("resolveLocale (AE-0416)", () => {
  // Scenario: A locale cookie wins over the browser language
  it("prefers a valid locale cookie", () => {
    expect(resolveLocale({ cookie: "en", acceptLanguage: "pt-BR" })).toBe("en");
  });

  // Scenario: Without a cookie the best Accept-Language match is used
  it("falls back to the browser language without a cookie", () => {
    expect(
      resolveLocale({
        cookie: undefined,
        acceptLanguage: "pt-BR,pt;q=0.9,en;q=0.8",
      }),
    ).toBe("pt");
  });

  // Scenario: An invalid cookie value is ignored
  it("ignores an unsupported cookie value", () => {
    expect(resolveLocale({ cookie: "xx", acceptLanguage: "pt" })).toBe("pt");
  });

  // Scenario: An unsupported browser language falls back to the default
  it("uses the default when nothing matches", () => {
    expect(
      resolveLocale({ cookie: undefined, acceptLanguage: "fr-FR, de;q=0.8" }),
    ).toBe(DEFAULT_LOCALE);
    expect(resolveLocale({ cookie: undefined, acceptLanguage: null })).toBe(
      DEFAULT_LOCALE,
    );
  });
});

describe("matchAcceptLanguage (AE-0416)", () => {
  // Scenario: Quality values decide between supported languages
  it("picks the supported language with the highest quality", () => {
    expect(matchAcceptLanguage("en;q=0.4, pt;q=0.9")).toBe("pt");
  });

  it("keeps the header order for equal qualities", () => {
    expect(matchAcceptLanguage("en, pt")).toBe("en");
    expect(matchAcceptLanguage("PT-br, en")).toBe("pt");
  });

  it("skips unsupported languages before a supported one", () => {
    expect(matchAcceptLanguage("fr-CA, fr;q=0.9, en;q=0.5")).toBe("en");
  });

  // Scenario: A language refused with q=0 is never picked
  it("never picks a language refused with q=0", () => {
    expect(matchAcceptLanguage("pt;q=0, en;q=0.5")).toBe("en");
    expect(matchAcceptLanguage("pt;q=0")).toBeNull();
  });

  it("reads the quality among other parameters", () => {
    expect(matchAcceptLanguage("en;level=1;q=0.2, pt;q=0.3")).toBe("pt");
  });

  it("returns null for an empty or wildcard-only header", () => {
    expect(matchAcceptLanguage("")).toBeNull();
    expect(matchAcceptLanguage(undefined)).toBeNull();
    expect(matchAcceptLanguage("*")).toBeNull();
    expect(matchAcceptLanguage(" , ;q=0.5")).toBeNull();
  });
});

describe("getRequestLocale (AE-0416)", () => {
  it("reads the cookie and the Accept-Language header of the request", async () => {
    const { getRequestLocale } = await import("./request-locale");
    headerValues.cookie = undefined;
    headerValues.acceptLanguage = "pt-BR,pt;q=0.9";
    await expect(getRequestLocale()).resolves.toBe("pt");
    headerValues.cookie = "en";
    await expect(getRequestLocale()).resolves.toBe("en");
  });
});
