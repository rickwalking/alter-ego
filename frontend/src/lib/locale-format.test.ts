import { describe, expect, it } from "vitest";
import {
  formatLocaleDate,
  formatLocaleDateTime,
  formatLocaleNumber,
  formatLocaleRelative,
  formatLocaleTime,
  toDateLocaleTag,
  toSupportedLocale,
} from "@/lib/locale-format";

const LOCAL_AFTERNOON = new Date(2026, 9, 17, 14, 5);
const MINUTE_MS = 60_000;
const NOW_MS = LOCAL_AFTERNOON.getTime();

describe("toSupportedLocale", () => {
  // Scenario: An unknown locale falls back to the default locale
  it.each([
    ["pt", "pt"],
    ["en", "en"],
    ["fr", "en"],
    ["", "en"],
    [null, "en"],
    [undefined, "en"],
  ])("maps %j to %s", (locale, expected) => {
    expect(toSupportedLocale(locale)).toBe(expected);
  });

  it("returns the BCP 47 tag Intl needs", () => {
    expect(toDateLocaleTag("pt")).toBe("pt-BR");
    expect(toDateLocaleTag("en")).toBe("en-US");
    expect(toDateLocaleTag("fr")).toBe("en-US");
  });
});

describe("formatLocaleDate", () => {
  // Scenario: A date is formatted in the active locale
  it("formats per locale", () => {
    expect(formatLocaleDate(LOCAL_AFTERNOON, "pt")).toBe("17/10/2026");
    expect(formatLocaleDate(LOCAL_AFTERNOON, "en")).toBe("Oct 17, 2026");
  });

  // Scenario: An unknown locale falls back to the default locale
  it("falls back to the default locale", () => {
    expect(formatLocaleDate(LOCAL_AFTERNOON, "fr")).toBe("Oct 17, 2026");
  });

  it("accepts ISO strings, timestamps and an explicit time zone", () => {
    expect(formatLocaleDate("2026-10-14T23:30:00Z", "pt", "UTC")).toBe(
      "14/10/2026",
    );
    expect(formatLocaleDate(NOW_MS, "pt")).toBe("17/10/2026");
  });

  // Scenario: An invalid or missing date prints nothing
  it.each(["", "not-a-date", null, undefined, Number.NaN])(
    "returns an empty string for %j",
    (value) => {
      expect(formatLocaleDate(value, "pt")).toBe("");
    },
  );
});

describe("formatLocaleDateTime and formatLocaleTime", () => {
  // Scenario: A date and time is formatted in the active locale
  it("formats the date with a clock time", () => {
    expect(formatLocaleDateTime(LOCAL_AFTERNOON, "pt")).toBe(
      "17/10/2026, 14:05",
    );
    expect(formatLocaleDateTime(LOCAL_AFTERNOON, "en")).toMatch(
      /^Oct 17, 2026, 2:05\sPM$/,
    );
  });

  it("formats a clock time alone", () => {
    expect(formatLocaleTime(LOCAL_AFTERNOON, "pt")).toBe("14:05");
    expect(formatLocaleTime(LOCAL_AFTERNOON, "en")).toMatch(/^2:05\sPM$/);
  });

  it("returns an empty string for an invalid instant", () => {
    expect(formatLocaleDateTime("nope", "pt")).toBe("");
    expect(formatLocaleTime(undefined, "en")).toBe("");
  });
});

describe("formatLocaleRelative", () => {
  // Scenario: A recent instant is shown as relative time in the active locale
  it.each([
    [0, "pt", "agora"],
    [0, "en", "now"],
    [5, "pt", "há 5 min."],
    [5, "en", "5m ago"],
    [59, "en", "59m ago"],
    [60, "en", "1h ago"],
    [180, "pt", "há 3 h"],
  ])("%i minutes ago in %s reads %s", (minutes, locale, expected) => {
    const instant = NOW_MS - minutes * MINUTE_MS;
    expect(formatLocaleRelative(instant, locale, NOW_MS)).toBe(expected);
  });

  it("reads a future instant (clock skew) as now", () => {
    expect(formatLocaleRelative(NOW_MS + MINUTE_MS, "en", NOW_MS)).toBe("now");
  });

  it("reads an instant older than a day as a date", () => {
    const twoDaysAgo = new Date(2026, 9, 15, 14, 5);
    expect(formatLocaleRelative(twoDaysAgo, "pt", NOW_MS)).toBe("15/10/2026");
  });

  it("returns an empty string for an invalid instant", () => {
    expect(formatLocaleRelative("nope", "pt", NOW_MS)).toBe("");
  });

  it("defaults to the current time", () => {
    expect(formatLocaleRelative(new Date(), "en")).toBe("now");
  });
});

describe("formatLocaleNumber", () => {
  it("groups digits per locale", () => {
    expect(formatLocaleNumber(1234, "pt")).toBe("1.234");
    expect(formatLocaleNumber(1234, "en")).toBe("1,234");
  });
});
