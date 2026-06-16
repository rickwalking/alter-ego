import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CreateStepHistoryPanel } from "./create-step-history-panel";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import type { EditorialWorkflowState } from "@/modules/publishing";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (key === "outlineTitle") {
      return `${values?.count} outline slides`;
    }
    if (key === "contentTitle") {
      return `${values?.count} drafts`;
    }
    if (key === "publishCaptionLabel") {
      return "Instagram caption";
    }
    return key;
  },
}));

const baseState: EditorialWorkflowState = {
  project_id: "p1",
  current_phase: "content",
  phase_status: "approved",
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
};

describe("CreateStepHistoryPanel", () => {
  it("renders outline slide titles", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      outline: [{ title: "Hook slide" }, { title: "Summary" }],
    };
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.OUTLINE}
        state={state}
      />,
    );
    expect(screen.getByText("2 outline slides")).toBeInTheDocument();
    expect(screen.getByText("Hook slide")).toBeInTheDocument();
  });

  it("renders publish caption when present", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      caption: "Check out this carousel #ai",
      linkedin_post_pt: "Long form post",
    };
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.PUBLISH}
        state={state}
      />,
    );
    expect(screen.getByText("Instagram caption")).toBeInTheDocument();
    expect(screen.getByText(/Check out this carousel/)).toBeInTheDocument();
  });
});
