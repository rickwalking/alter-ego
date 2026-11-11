/** Gherkin: frontend/tests/features/public-privacy-page.feature */
import { describe, expect, it, vi } from "vitest";
import type { GetRequestConfigParams, RequestConfig } from "next-intl/server";

const visitor = vi.hoisted(() => ({ locale: "en" }));

vi.mock("next-intl/server", () => ({
  getRequestConfig: (
    create: (params: GetRequestConfigParams) => Promise<RequestConfig>,
  ) => create,
}));
vi.mock("./request-locale", () => ({
  getRequestLocale: () => Promise.resolve(visitor.locale),
}));

async function config(locale?: string): Promise<RequestConfig> {
  const { default: create } = await import("./request");
  const build = create as unknown as (
    params: GetRequestConfigParams,
  ) => Promise<RequestConfig>;
  return build({ locale, requestLocale: Promise.resolve(undefined) });
}

describe("i18n request config", () => {
  // Scenario: The privacy policy renders in Portuguese for every visitor
  it("loads the explicit locale over an English visitor's", async () => {
    visitor.locale = "en";
    const result = await config("pt");

    expect(result.locale).toBe("pt");
    expect(result.messages).toHaveProperty("privacy.title");
  });

  // Scenario: The privacy policy renders in Portuguese for every visitor
  it("uses the visitor's locale without an explicit one", async () => {
    visitor.locale = "en";
    const result = await config();

    expect(result.locale).toBe("en");
    expect(result.messages).not.toHaveProperty("privacy");
  });

  // Scenario: The privacy policy renders in Portuguese for every visitor
  it("ignores an unsupported explicit locale", async () => {
    visitor.locale = "pt";
    const result = await config("fr");

    expect(result.locale).toBe("pt");
  });
});
