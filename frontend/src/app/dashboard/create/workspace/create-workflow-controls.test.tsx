import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import type { CreateWorkflowControlsProps } from "@/modules/editorial";
import { CreateWorkflowControls } from "./create-workflow-controls";

/** Gherkin: tests/features/final-review-copy-edit-ae0505.feature. */

const COPY_NOTE =
  "Save or discard the caption or LinkedIn edit before approving or requesting changes.";

function props(
  overrides: Partial<CreateWorkflowControlsProps> = {},
): CreateWorkflowControlsProps {
  return {
    state: {
      project_id: "p1",
      current_phase: "final_review",
      phase_status: "awaiting_human",
    } as CreateWorkflowControlsProps["state"],
    showLiveControls: true,
    loading: false,
    feedback: "",
    setFeedback: vi.fn(),
    feedbackError: null,
    setFeedbackError: vi.fn(),
    sendBackTarget: "content",
    setSendBackTarget: vi.fn(),
    handleRevise: vi.fn(),
    approve: vi.fn(),
    contentHasEdits: false,
    contentSlides: [],
    personaApproveBlocked: false,
    presentationApproveBlocked: false,
    editBudgetBlocked: false,
    designReviseBlocked: false,
    showPublishLink: false,
    ...overrides,
  };
}

describe("CreateWorkflowControls copy guard (AE-0505)", () => {
  /** Scenario: Approve and send back wait for unsaved or saving texts */
  it("blocks approve and send back while a review text is busy", () => {
    const current = props({ copyBlocked: true });
    render(<CreateWorkflowControls {...current} />);

    expect(
      screen.getByRole("button", { name: "Approve Phase" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Request revision" }),
    ).toBeDisabled();
    expect(screen.getByText(COPY_NOTE)).toBeInTheDocument();
  });

  /** Scenario: Approve and send back wait for unsaved or saving texts */
  it("lets approve and send back through once the texts are saved", () => {
    const current = props({ copyBlocked: false });
    render(<CreateWorkflowControls {...current} />);

    fireEvent.click(screen.getByRole("button", { name: "Approve Phase" }));
    fireEvent.click(screen.getByRole("button", { name: "Request revision" }));
    expect(current.approve).toHaveBeenCalledTimes(1);
    expect(current.handleRevise).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(COPY_NOTE)).not.toBeInTheDocument();
  });
});
