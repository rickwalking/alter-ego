import { describe, expect, it } from "vitest";

import { CALENDAR_COLORS } from "./constants";

function channels(color: string): number[] {
  if (color.startsWith("#")) {
    const n = Number.parseInt(color.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1];
  }
  return color
    .replace(/[^\d.,]/g, "")
    .split(",")
    .map(Number);
}

function luminance(rgb: number[]): number {
  const [r = 0, g = 0, b = 0] = rgb.map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(foreground: string, background: string): number {
  const [r = 0, g = 0, b = 0, a = 1] = channels(foreground);
  const bg = channels(background);
  const blended = [r, g, b].map((c, i) => c * a + (bg[i] ?? 0) * (1 - a));
  const [hi = 0, lo = 0] = [luminance(blended), luminance(bg)].sort(
    (x, y) => y - x,
  );
  return (hi + 0.05) / (lo + 0.05);
}

describe("calendar dim text", () => {
  // Scenario: Calendar dim text meets WCAG AA contrast
  it.each([
    ["header", "#06121c"],
    ["card", CALENDAR_COLORS.card],
  ])("is at least 4.5:1 on the %s background", (_, background) => {
    expect(contrast(CALENDAR_COLORS.tD, background)).toBeGreaterThanOrEqual(
      4.5,
    );
  });
});
