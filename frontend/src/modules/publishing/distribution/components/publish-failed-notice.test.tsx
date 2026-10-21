import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PublishFailedNotice } from "./publish-failed-notice";

/**
 * When phase_status is "failed" the publish page shows the WorkflowFailedCard
 * (error message + "Back to workspace" link) instead of the
 * awaitingFinalApproval message. The failed branch is extracted into
 * PublishFailedNotice so it can be tested without the full page harness.
 */
describe("PublishFailedNotice (publish page failed state)", () => {
  const WORKSPACE_HREF = "/dashboard/create/project-1/workspace?step=outline";

  /**
   * Given the editorial workflow has phase_status "failed"
   * When the publish page renders
   * Then the WorkflowFailedCard with the backend error message is shown
   * And a "Back to workspace" link is shown
   * And the awaitingFinalApproval message is NOT shown
   */
  // Scenario: Failed phase shows error card on the publish page
  it("shows the failed card, error message and back-to-workspace link", () => {
    render(
      <PublishFailedNotice
        currentPhase="content"
        errorMessage="Invalid JSON response from LLM"
        workspaceHref={WORKSPACE_HREF}
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Content failed")).toBeInTheDocument();
    expect(
      screen.getByText("Invalid JSON response from LLM"),
    ).toBeInTheDocument();

    const backLink = screen.getByRole("link", {
      name: "← Back to workspace",
    });
    expect(backLink).toHaveAttribute("href", WORKSPACE_HREF);

    expect(screen.queryByText(/Complete final review/)).not.toBeInTheDocument();
  });

  // Scenario: Retry from the publish failed card navigates back to workspace
  it("navigates to the workspace when the retry button is clicked", async () => {
    const assignMock = vi.fn();
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { href: "" },
    });
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
