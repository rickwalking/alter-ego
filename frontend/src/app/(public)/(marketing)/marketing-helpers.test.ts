import { describe, expect, it } from "vitest";
import { cardLocale } from "@/app/(public)/(marketing)/marketing-helpers";

describe("cardLocale", () => {
  it("maps an unsupported locale to the default locale", () => {
    expect(cardLocale("fr")).toBe("en");
    expect(cardLocale("en")).toBe("en");
    expect(cardLocale("pt")).toBe("pt");
  });
});
