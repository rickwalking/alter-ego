import { describe, expect, it } from "vitest";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import {
  isPublishReady,
  offersCoverPicker,
  offersRadarTemplates,
} from "./publish-readiness";

function workflow(
  overrides: Partial<EditorialWorkflowState>,
): EditorialWorkflowState {
  return {
    project_id: "p1",
    current_phase: "content",
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "draft",
    ...overrides,
  };
}

describe("isPublishReady", () => {
  // Scenario: The publish page of an unfinished carousel says it is not ready
  it("is not ready before the final review", () => {
    for (const phase of [
      "research",
      "outline",
      "content",
      "design",
      "images",
    ]) {
      expect(
        isPublishReady(
          { pdf_path: "x.pdf" },
          workflow({ current_phase: phase }),
        ),
      ).toBe(false);
    }
  });

  it("is ready at the final review, once published or once approved", () => {
    expect(
      isPublishReady(
        { pdf_path: null },
        workflow({ current_phase: "final_review" }),
      ),
    ).toBe(true);
    expect(
      isPublishReady(
        { pdf_path: null },
        workflow({ current_phase: "published" }),
      ),
    ).toBe(true);
    expect(
      isPublishReady(
        { pdf_path: null },
        workflow({ workflow_status: "approved_for_publish" }),
      ),
    ).toBe(true);
  });

  it("falls back to the PDF for a project without workflow state", () => {
    expect(isPublishReady({ pdf_path: "x.pdf" }, null)).toBe(true);
    expect(isPublishReady({ pdf_path: null }, null)).toBe(false);
    expect(isPublishReady({}, null)).toBe(false);
  });
});

describe("offersRadarTemplates", () => {
  // Scenario: A POV project is not offered Radar templates
  it("offers the Radar layouts only to Radar IA projects", () => {
    expect(offersRadarTemplates({ content_mode: "news_analysis" })).toBe(true);
    expect(offersRadarTemplates({})).toBe(true);
    expect(offersRadarTemplates({ content_mode: "pov" })).toBe(false);
    expect(offersRadarTemplates({ content_mode: "pov_news" })).toBe(false);
  });
});

describe("offersCoverPicker", () => {
  /**
   * (frontend/tests/features/publish-cover-picker-ae0445.feature)
   */
  // Scenario: The picker is shown for Ponto de Vista carousels only
  it("offers the slide-1 cover picker only to Ponto de Vista projects", () => {
    expect(offersCoverPicker({ content_mode: "pov" })).toBe(true);
    expect(offersCoverPicker({ content_mode: "pov_news" })).toBe(true);
    expect(offersCoverPicker({ content_mode: "news_analysis" })).toBe(false);
    expect(offersCoverPicker({})).toBe(false);
  });
});
