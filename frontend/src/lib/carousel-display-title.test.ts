import { describe, expect, it } from "vitest";
import {
  carouselDisplayTitle,
  stripInlineMarkup,
} from "./carousel-display-title";

describe("carouselDisplayTitle", () => {
  it("prefers a non-blank title over the topic", () => {
    expect(carouselDisplayTitle({ title: "AI Guide", topic: "AI topic" })).toBe(
      "AI Guide",
    );
  });

  it.each([
    ["null", null],
    ["empty", ""],
    ["whitespace", "   "],
  ])("falls back to the topic when the title is %s", (_kind, title) => {
    expect(carouselDisplayTitle({ title, topic: "AI topic" })).toBe("AI topic");
  });

  it("strips inline markup from the title", () => {
    expect(
      carouselDisplayTitle({
        title: "**Bold** <em>Moves</em>",
        topic: "AI topic",
      }),
    ).toBe("Bold Moves");
  });

  it("strips inline markup from the topic fallback", () => {
    expect(
      carouselDisplayTitle({ title: null, topic: "__Tema__ **válido**" }),
    ).toBe("Tema válido");
  });

  it("returns an empty string only when both the title and the topic are blank", () => {
    expect(carouselDisplayTitle({ title: "** **", topic: "  " })).toBe("");
  });
});

describe("stripInlineMarkup", () => {
  it("removes emphasis tags with attributes and the __ delimiters", () => {
    expect(
      stripInlineMarkup('<strong class="x">A</strong> **b** __c__ <em>d</em>'),
    ).toBe("A b c d");
  });
});
