import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CreateStepHistoryPanel } from "./create-step-history-panel";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import type { EditorialWorkflowState } from "@/modules/publishing";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (key === "outlineTitle") {
      return `${String(values?.count)} outline slides`;
    }
    if (key === "contentTitle") {
      return `${String(values?.count)} drafts`;
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

  it("lists research sources, falling back to the untitled label", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      research_findings: [{ source: "Paper A" }, { summary: "no source" }],
    };
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.RESEARCH}
        state={state}
      />,
    );
    expect(screen.getByText("researchTitle")).toBeInTheDocument();
    expect(screen.getByText("Paper A")).toBeInTheDocument();
    expect(screen.getByText("untitledSlide")).toBeInTheDocument();
  });

  it("uses the outline heading, then the untitled label", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      outline: [{ heading: "From heading" }, {}],
    };
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.OUTLINE}
        state={state}
      />,
    );
    expect(screen.getByText("From heading")).toBeInTheDocument();
    expect(screen.getByText("untitledSlide")).toBeInTheDocument();
  });

  it("shows the draft count when the content step has no slides", () => {
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.CONTENT}
        state={baseState}
      />,
    );
    expect(screen.getByText("0 drafts")).toBeInTheDocument();
  });

  it("shows the read-only content review once drafts exist", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      slide_drafts: [{ title: "Draft one", body: "Body text" }],
    };
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.CONTENT}
        state={state}
      />,
    );
    // The content review labels each slide (the mock echoes the key).
    expect(screen.getByText("slideLabel")).toBeInTheDocument();
    expect(screen.queryByText("1 drafts")).not.toBeInTheDocument();
  });

  it("counts images and notes an applied design", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      image_assets: ["a.png", "b.png"],
      design_applied: true,
    };
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.IMAGES}
        state={state}
      />,
    );
    expect(screen.getByText("imagesTitle · designApplied")).toBeInTheDocument();
  });

  it("counts zero images when none were generated", () => {
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.IMAGES}
        state={baseState}
      />,
    );
    expect(screen.getByText("imagesTitle")).toBeInTheDocument();
  });

  it("shows the review hint on the review step", () => {
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.REVIEW}
        state={baseState}
      />,
    );
    expect(screen.getByText("reviewHint")).toBeInTheDocument();
  });

  it("shows the publish placeholder when no copy exists yet", () => {
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.PUBLISH}
        state={{ ...baseState, caption: "  " }}
      />,
    );
    expect(screen.getByText("publishEmpty")).toBeInTheDocument();
  });

  it("shows only the LinkedIn copy when the caption is blank", () => {
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.PUBLISH}
        state={{ ...baseState, linkedin_post_pt: "Post PT" }}
      />,
    );
    expect(screen.getByText("publishLinkedInLabel")).toBeInTheDocument();
    expect(screen.queryByText("Instagram caption")).not.toBeInTheDocument();
  });

  it("falls back to the empty notice for the brief step", () => {
    render(
      <CreateStepHistoryPanel
        viewStepId={CREATE_STEP_IDS.BRIEF}
        state={baseState}
      />,
    );
    expect(screen.getByText("empty")).toBeInTheDocument();
  });
});
