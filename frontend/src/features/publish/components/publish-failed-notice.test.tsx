import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PublishFailedNotice } from "./publish-failed-notice";

// Feature: Workflow Error Feedback & Retry (AE-0009, AC#19)
//   The publish page, when phase_status === "failed", shows the
//   WorkflowFailedCard (error message + "Back to workspace" link) instead of
//   the awaitingFinalApproval message. The failed branch is extracted into
//   PublishFailedNotice so it can be tested without the full page harness.
describe("PublishFailedNotice (publish page failed state)", () => {
  const WORKSPACE_HREF = "/dashboard/create/project-1/workspace?step=outline";

  // Scenario: Failed phase shows error card on the publish page
  //   Given the editorial workflow has phase_status "failed"
  //   When the publish page renders
  //   Then the WorkflowFailedCard with the backend error message is shown
  //   And a "Back to workspace" link is shown
  //   And the awaitingFinalApproval message is NOT shown
  it("shows the failed card, error message and back-to-workspace link", () => {
    render(
      <PublishFailedNotice
        currentPhase="content"
        errorMessage="Invalid JSON response from LLM"
        workspaceHref={WORKSPACE_HREF}
      />,
    );

    // WorkflowFailedCard renders as an alert with the phase + error message.
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Content failed")).toBeInTheDocument();
    expect(
      screen.getByText("Invalid JSON response from LLM"),
    ).toBeInTheDocument();

    // "Back to workspace" link points at the create workspace.
    const backLink = screen.getByRole("link", {
      name: "← Back to workspace",
    });
    expect(backLink).toHaveAttribute("href", WORKSPACE_HREF);

    // The awaitingFinalApproval branch is NOT rendered in the failed state.
    expect(screen.queryByText(/Complete final review/)).not.toBeInTheDocument();
  });

  // Scenario: Retry from the publish failed card navigates back to workspace
  it("navigates to the workspace when the retry button is clicked", async () => {
    const assignMock = vi.fn();
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...originalLocation, href: "" },
    });
    // Capture href assignment.
    Object.defineProperty(window.location, "href", {
      configurable: true,
      set: assignMock,
      get: () => "",
    });

    const user = userEvent.setup();
    render(
      <PublishFailedNotice
        currentPhase="content"
        errorMessage="boom"
        workspaceHref={WORKSPACE_HREF}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Retry Workflow" }));

    expect(assignMock).toHaveBeenCalledWith(WORKSPACE_HREF);

    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });
});
