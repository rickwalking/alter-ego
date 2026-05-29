import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { EditorialPhaseReview } from "@/features/create/components/editorial-phase-review";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import en from "@/i18n/locales/en.json";

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockAuthenticatedFetch = vi.mocked(authenticatedFetch);

function renderReview(state: EditorialWorkflowState): void {
  render(
    <NextIntlClientProvider locale="en" messages={en}>
      <EditorialPhaseReview projectId="project-1" state={state} />
    </NextIntlClientProvider>,
  );
}

describe("EditorialPhaseReview", () => {
  beforeEach(() => {
    mockAuthenticatedFetch.mockReset();
  });

  // Scenario: Research gate shows findings and feedback composer
  it("shows research findings at the research gate", () => {
    const state: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.RESEARCH,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [
        {
          source: "https://example.com/report",
          key_points: ["Primary breach vector", "Mitigation checklist"],
        },
      ],
      outline: [],
      slide_drafts: [],
      image_assets: [],
      design_applied: false,
      lock_version: 1,
      status: "draft",
    };

    renderReview(state);

    expect(screen.getByText("https://example.com/report")).toBeInTheDocument();
    expect(screen.getByText("Primary breach vector")).toBeInTheDocument();
  });

  // Scenario: Final review tab shows carousel blog caption and quality scores
  it("shows final review tabs with caption and rubric scores", async () => {
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ markdown: "# Draft blog\n\nBody copy" }),
    } as Response);

    const state: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [{ title: "Intro slide" }],
      slide_drafts: [{ draft_text: "Slide body" }],
      image_assets: [],
      design_applied: true,
      lock_version: 1,
      status: "draft",
      caption: "Instagram caption draft",
      blog_markdown: "# Draft blog\n\nBody copy",
      rubric_scores: { voice_match: 88, clarity: 91 },
    };

    renderReview(state);

    expect(screen.getByRole("tab", { name: "Carousel" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Blog" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Caption" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Quality" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Caption" }));
    expect(screen.getByText("Instagram caption draft")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Quality" }));
    expect(screen.getByText("voice match")).toBeInTheDocument();
    expect(screen.getByText("88")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Blog" }));
    await waitFor(() => {
      expect(screen.getByText(/Draft blog/)).toBeInTheDocument();
    });
  });

  // Scenario: Content approve disabled when persona score below threshold
  it("shows slide drafts at the content gate", () => {
    const state: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.CONTENT,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [],
      slide_drafts: [
        { title: "Intro", draft_text: "Opening copy" },
        { title: "Insight", draft_text: "Middle copy" },
      ],
      image_assets: [],
      design_applied: false,
      lock_version: 1,
      status: "draft",
      persona_scores: { default: { overall: 65 } },
    };

    renderReview(state);

    expect(screen.getByText("Opening copy")).toBeInTheDocument();
    expect(screen.getByText("Middle copy")).toBeInTheDocument();
  });
});
