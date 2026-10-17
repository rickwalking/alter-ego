// AE-0414 — Gherkin: frontend/tests/features/content-review-manual-fixes-ae0414.feature
// Scenario: A live counter warns when copy is over budget on a v4 deck
import { describe, expect, it } from "vitest";
import {
  localizedSlidesHaveBudgetViolations,
  measureBudgetUsage,
  resolveBodyBudget,
  resolveExtraBudget,
  resolveHeadingBudget,
  resolveItemBudget,
} from "./presentation-copy-budgets";

describe("presentation copy budgets (AE-0414)", () => {
  it.each([
    "hero_lower_third_v1",
    "hero_lower_third_v2",
    "hero_lower_third_v3",
    "hero_lower_third_v4",
    null,
    undefined,
  ])("applies the hero budgets for %s", (policy) => {
    expect(resolveBodyBudget("content", policy)).toEqual({
      maxCharacters: 220,
      maxLines: 6,
    });
    expect(resolveHeadingBudget("intro", policy)).toEqual({
      maxCharacters: 72,
      maxLines: 3,
    });
    expect(resolveItemBudget("summary_points", "title", policy)).toEqual({
      maxCharacters: 36,
    });
  });

  it("uses the tighter pov_hook_v1 budgets", () => {
    expect(resolveHeadingBudget("intro", "pov_hook_v1")?.maxCharacters).toBe(
      60,
    );
    expect(resolveBodyBudget("intro", "pov_hook_v1")).toEqual({
      maxCharacters: 40,
      maxLines: 1,
    });
    expect(resolveBodyBudget("content", "pov_hook_v1")?.maxCharacters).toBe(
      200,
    );
  });

  it("has no budget for an unknown policy or an unbudgeted field", () => {
    expect(resolveBodyBudget("content", "some_future_v9")).toBeNull();
    expect(resolveBodyBudget("cta", "hero_lower_third_v4")).toBeNull();
    expect(
      resolveItemBudget("stats", "title", "hero_lower_third_v4"),
    ).toBeNull();
    expect(resolveExtraBudget("tldr_strip", "hero_lower_third_v4")).toBeNull();
  });

  it("budgets structured items and CTA extras", () => {
    expect(
      resolveItemBudget("features", "body", "hero_lower_third_v4"),
    ).toEqual({ maxCharacters: 100 });
    expect(
      resolveItemBudget("actions", "title", "hero_lower_third_v4"),
    ).toEqual({ maxCharacters: 30 });
    expect(resolveExtraBudget("creator_name", "hero_lower_third_v4")).toEqual({
      maxCharacters: 60,
    });
  });

  it("measures a field with and without a budget", () => {
    const budget = resolveBodyBudget("content", "hero_lower_third_v4");
    expect(measureBudgetUsage("x".repeat(5000), budget)).toEqual({
      characters: 5000,
      lines: 1,
      budget,
      exceeded: true,
    });
    expect(measureBudgetUsage("a\nb", null)).toEqual({
      characters: 3,
      lines: 2,
      budget: null,
      exceeded: false,
    });
    expect(measureBudgetUsage("", budget).lines).toBe(0);
  });

  it("flags over-budget copy on a v4 deck (approve-with-edits guard)", () => {
    const slide = {
      slide_index: 3,
      slide_type: "content",
      presentation_pt: { heading: "Ok", body: "curto" },
      presentation_en: { heading: "Ok", body: "y".repeat(221) },
    };
    expect(
      localizedSlidesHaveBudgetViolations([slide], "hero_lower_third_v4"),
    ).toBe(true);
    expect(localizedSlidesHaveBudgetViolations([slide], "unknown_v1")).toBe(
      false,
    );
  });
});
