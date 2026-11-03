import { describe, expect, it } from "vitest";
import { EDITORIAL_WORKFLOW_CONFLICT_CODES } from "@/constants/editorial-workflow";
import { resumeErrorMessage } from "./resume-workflow";

/**
 * Gherkin: backend/tests/features/website_cover_review_switch_ae0594.feature
 */

const translate = (key: string): string => `t:${key}`;

describe("resumeErrorMessage", () => {
  // Scenario: No approval lands while a cover switch is between write and render
  it.each([
    EDITORIAL_WORKFLOW_CONFLICT_CODES.BUILD_IN_PROGRESS,
    EDITORIAL_WORKFLOW_CONFLICT_CODES.MUTATION_IN_PROGRESS,
  ])("explains that the slides are still rendering for %s", (code) => {
    expect(resumeErrorMessage(code, translate)).toBe("t:renderPending");
  });

  // Scenario: No approval lands while a cover switch is between write and render
  it("keeps the other conflict messages and passes unknown text through", () => {
    expect(
      resumeErrorMessage(
        EDITORIAL_WORKFLOW_CONFLICT_CODES.VERSION_CONFLICT,
        translate,
      ),
    ).toBe("t:versionConflict");
    expect(resumeErrorMessage("plain failure", translate)).toBe(
      "plain failure",
    );
  });
});
