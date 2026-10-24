/** Gherkin: frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature */
import { describe, expect, it } from "vitest";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial";
import { mergeWorkflowState } from "./use-editorial-workflow-utils";

const PREVIOUS: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: "content",
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
  checklist_slide_indexes: [8],
};

describe("checklist slides across workflow events", () => {
  /** Scenario: A start response or a live update keeps the checklist slides */
  it("keeps them through a partial event", () => {
    const merged = mergeWorkflowState("project-1", PREVIOUS, {
      phase: "content",
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    });
    expect(merged.checklist_slide_indexes).toEqual([8]);
  });

  /** Scenario: A start response or a live update keeps the checklist slides */
  it("keeps them through a full snapshot that does not carry them", () => {
    const merged = mergeWorkflowState("project-1", PREVIOUS, {
      project_id: "project-1",
      current_phase: "content",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [],
      slide_drafts: [],
    });
    expect(merged.checklist_slide_indexes).toEqual([8]);
  });

  /** Scenario: A start response or a live update keeps the checklist slides */
  it("takes them from a response that computes them", () => {
    const merged = mergeWorkflowState("project-1", null, {
      ...PREVIOUS,
      checklist_slide_indexes: [3, 4],
    });
    expect(merged.checklist_slide_indexes).toEqual([3, 4]);
  });
});
