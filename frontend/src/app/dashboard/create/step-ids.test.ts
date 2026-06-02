import { describe, it, expect } from "vitest";
import {
  CREATE_STEP_IDS,
  EDITORIAL_PHASE_TO_STEP,
  isFutureCreateStep,
  isHistoricalCreateStep,
  resolveStepFromWorkflowPhase,
} from "@/app/dashboard/create/step-ids";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";

describe("create step ids", () => {
  it("maps published phase to publish tab", () => {
    expect(resolveStepFromWorkflowPhase(EDITORIAL_PHASES.PUBLISHED)).toBe(
      CREATE_STEP_IDS.PUBLISH,
    );
    expect(EDITORIAL_PHASE_TO_STEP[EDITORIAL_PHASES.PUBLISHED]).toBe(
      CREATE_STEP_IDS.PUBLISH,
    );
  });

  it("isHistoricalCreateStep when view is before workflow step", () => {
    expect(
      isHistoricalCreateStep(CREATE_STEP_IDS.OUTLINE, CREATE_STEP_IDS.IMAGES),
    ).toBe(true);
    expect(
      isHistoricalCreateStep(CREATE_STEP_IDS.IMAGES, CREATE_STEP_IDS.OUTLINE),
    ).toBe(false);
  });

  it("isFutureCreateStep when view is after workflow step", () => {
    expect(
      isFutureCreateStep(CREATE_STEP_IDS.PUBLISH, CREATE_STEP_IDS.CONTENT),
    ).toBe(true);
    expect(
      isFutureCreateStep(CREATE_STEP_IDS.OUTLINE, CREATE_STEP_IDS.IMAGES),
    ).toBe(false);
  });
});
