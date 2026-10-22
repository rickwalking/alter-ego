import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { BG_CARD, BG_DEEP, BG_SIDEBAR, TEXT_DIM } from "./neon";

const WCAG_AA_BODY_TEXT = 4.5;

function hexRgb(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbaParts(rgba: string): [number, number, number, number] {
  const [r, g, b, a] = rgba
    .replace(/[^\d.,]/g, "")
    .split(",")
    .map(Number);
  return [r ?? 0, g ?? 0, b ?? 0, a ?? 1];
}

function luminance([r, g, b]: [number, number, number]): number {
  const lin = (c: number): number => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function contrastOver(foreground: string, background: string): number {
  const [r, g, b, a] = rgbaParts(foreground);
  const bg = hexRgb(background);
  const blended: [number, number, number] = [
    r * a + bg[0] * (1 - a),
    g * a + bg[1] * (1 - a),
    b * a + bg[2] * (1 - a),
  ];
  const [hi, lo] = [luminance(blended), luminance(bg)].sort((x, y) => y - x);
  return ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05);
}

describe("dim text contrast", () => {
  // Scenario: Dim text meets WCAG AA contrast
  it.each([
    ["page", BG_DEEP],
    ["card", BG_CARD],
    ["sidebar", BG_SIDEBAR],
  ])("is at least 4.5:1 on the %s background", (_, background) => {
    expect(contrastOver(TEXT_DIM, background)).toBeGreaterThanOrEqual(
      WCAG_AA_BODY_TEXT,
    );
  });

  // Scenario: Dim text meets WCAG AA contrast
  it("is the same colour in the CSS theme", () => {
    const css = readFileSync(
      join(process.cwd(), "src/app/globals.css"),
      "utf8",
    );
    const start = css.indexOf("--color-text-dim:");
    const value = css.slice(start, css.indexOf(";", start));
    expect(rgbaParts(value)).toEqual(rgbaParts(TEXT_DIM));
  });
});
