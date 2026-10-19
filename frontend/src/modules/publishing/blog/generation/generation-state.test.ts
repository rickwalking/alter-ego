import { describe, expect, it } from "vitest";
import { readGenerationState } from "./generation-state";

// Scenarios: see tests/features/blog_generate_ae0425.feature
// ("Generation progress is polled and shown", "A failed generation shows a retry affordance")

describe("readGenerationState (AE-0425)", () => {
  it("reads a full run state", () => {
    const state = readGenerationState({
      generation: {
        status: "partial",
        attempt: 2,
        warnings: ["carousel_private", 3],
        errors: [{ code: "image_failed", slot: "sec_1", reason: "x" }, "bad"],
        recoverable: true,
        image_slots: 10,
        image_count: 9,
      },
    });
    expect(state).toEqual({
      status: "partial",
      attempt: 2,
      warnings: ["carousel_private"],
      errors: [{ code: "image_failed", slot: "sec_1", reason: "x" }],
      recoverable: true,
      imageSlots: 10,
      imageCount: 9,
    });
  });

  it("defaults missing fields", () => {
    expect(readGenerationState({ generation: { status: "failed" } })).toEqual({
      status: "failed",
      attempt: 1,
      warnings: [],
      errors: [],
      recoverable: false,
      imageSlots: 0,
      imageCount: 0,
    });
  });

  it("is null when the post was never generated", () => {
    expect(readGenerationState(undefined)).toBeNull();
    expect(readGenerationState({})).toBeNull();
    expect(readGenerationState({ generation: [] })).toBeNull();
    expect(readGenerationState({ generation: { status: "weird" } })).toBeNull();
    expect(readGenerationState({ generation: { status: 1 } })).toBeNull();
  });

  it("ignores malformed error entries and counts", () => {
    const state = readGenerationState({
      generation: {
        status: "failed",
        errors: { code: "x" },
        image_slots: -1,
      },
    });
    expect(state?.errors).toEqual([]);
    expect(state?.imageSlots).toBe(0);
  });
});
