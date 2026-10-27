import { describe, expect, it } from "vitest";
import { formatGenerationDuration } from "./create-generation-log-model";

describe("generation duration formatting", () => {
  /** Scenario: Generation log groups runs and phases accessibly */
  it("rounds total seconds before splitting minutes", () => {
    expect(formatGenerationDuration(59999)).toBe("1 min 0 s");
    expect(formatGenerationDuration(3599999)).toBe("60 min 0 s");
    expect(formatGenerationDuration(1250)).toBe("1.3 s");
    expect(formatGenerationDuration(null)).toBe("—");
  });
});
