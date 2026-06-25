import { describe, it, expect } from "vitest";
import {
  resolveWorkflowStatusVisual,
  titlecaseStatus,
} from "./workflow-status";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";

// Scenarios: see tests/features/create-workflow-status-badge.feature

describe("resolveWorkflowStatusVisual", () => {
  it.each([
    {
      status: WORKFLOW_PHASE_STATUS.PENDING,
      expected: { variant: "amber", pulse: false, labelKey: "draft" },
    },
    {
      status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      expected: { variant: "cyan", pulse: true, labelKey: "inProgress" },
    },
    {
      status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      expected: { variant: "magenta", pulse: false, labelKey: "awaitingHuman" },
    },
    {
      status: WORKFLOW_PHASE_STATUS.APPROVED,
      expected: { variant: "teal", pulse: false, labelKey: "approved" },
    },
    {
      status: EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH,
      expected: { variant: "teal", pulse: false, labelKey: "readyToPublish" },
    },
    {
      status: WORKFLOW_PHASE_STATUS.REJECTED,
      expected: { variant: "red", pulse: false, labelKey: "rejected" },
    },
    {
      status: WORKFLOW_PHASE_STATUS.FAILED,
      expected: { variant: "red", pulse: false, labelKey: "failed" },
    },
    {
      status: "published",
      expected: { variant: "green", pulse: false, labelKey: "published" },
    },
    {
      status: "completed",
      expected: { variant: "green", pulse: false, labelKey: "completed" },
    },
  ])("maps $status to a semantic variant", ({ status, expected }) => {
    expect(resolveWorkflowStatusVisual(status)).toEqual(expected);
  });

  it("resolves a missing status to Draft (amber, no dot)", () => {
    expect(resolveWorkflowStatusVisual(null)).toEqual({
      variant: "amber",
      pulse: false,
      labelKey: "draft",
    });
    expect(resolveWorkflowStatusVisual(undefined).labelKey).toBe("draft");
    expect(resolveWorkflowStatusVisual("").labelKey).toBe("draft");
  });

  it("falls back to neutral cyan with no label key for an unknown status", () => {
    expect(resolveWorkflowStatusVisual("brand_new_state")).toEqual({
      variant: "cyan",
      pulse: false,
      labelKey: null,
    });
  });

  it("only the in_progress state pulses", () => {
    const pulsing = [
      WORKFLOW_PHASE_STATUS.PENDING,
      WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      WORKFLOW_PHASE_STATUS.APPROVED,
      WORKFLOW_PHASE_STATUS.FAILED,
    ].filter((s) => resolveWorkflowStatusVisual(s).pulse);
    expect(pulsing).toEqual([WORKFLOW_PHASE_STATUS.IN_PROGRESS]);
  });
});

describe("titlecaseStatus", () => {
  it("titlecases snake/kebab tokens", () => {
    expect(titlecaseStatus("brand_new_state")).toBe("Brand New State");
    expect(titlecaseStatus("in-review")).toBe("In Review");
  });

  it("returns an empty string for a missing value", () => {
    expect(titlecaseStatus(null)).toBe("");
    expect(titlecaseStatus(undefined)).toBe("");
  });
});
