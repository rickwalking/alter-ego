import { describe, expect, it } from "vitest";
import { captionInvalid, linkedinInvalid } from "./copy-limits";

/** Gherkin: tests/features/final-review-copy-edit-ae0505.feature. */

function hashtags(count: number): string {
  return Array.from({ length: count }, (_, i) => `#t${i}`).join(" ");
}

describe("copy limits (AE-0505)", () => {
  /** Scenario: The reviewer saves an edited caption in the final review */
  it("accepts a caption at the Instagram limits and refuses one past them", () => {
    expect(captionInvalid("x".repeat(2200))).toBe(false);
    expect(captionInvalid("x".repeat(2201))).toBe(true);
    expect(captionInvalid(hashtags(30))).toBe(false);
    expect(captionInvalid(hashtags(31))).toBe(true);
  });

  /** Scenario: The reviewer saves a LinkedIn post per language */
  it("accepts a LinkedIn post at 3,000 characters and refuses 3,001", () => {
    expect(linkedinInvalid("x".repeat(3000))).toBe(false);
    expect(linkedinInvalid("x".repeat(3001))).toBe(true);
  });
});
