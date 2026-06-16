import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WorkflowFailedCard } from "./workflow-failed-card";

// Feature: Workflow Error Feedback & Retry (AE-0009)
describe("WorkflowFailedCard", () => {
  // Scenario: Failed phase shows error card on workspace
  //   Given the editorial workflow has phase_status "failed"
  //   And current_phase is "content"
  //   When the workspace page renders
  //   Then a prominent error card is displayed
  //   And the card shows "Content failed"
  //   And the card shows the backend error message
  //   And a "Retry Workflow" button is visible
  it("renders the failed phase label and backend error message", () => {
    render(
      <WorkflowFailedCard
        currentPhase="content"
        errorMessage="Invalid JSON response from LLM"
        onRetry={vi.fn()}
        isRetrying={false}
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Content failed")).toBeInTheDocument();
    expect(
      screen.getByText("Invalid JSON response from LLM"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Retry Workflow" }),
    ).toBeInTheDocument();
  });

  // Scenario: Failed phase shows error card on workspace
  //   Falls back to the raw phase id when no i18n label exists.
  it("falls back to the raw phase id for unmapped phases", () => {
    render(
      <WorkflowFailedCard
        currentPhase="unknown_phase"
        errorMessage={null}
        onRetry={vi.fn()}
        isRetrying={false}
      />,
    );

    expect(screen.getByText("unknown_phase failed")).toBeInTheDocument();
  });

  // Scenario: Failed phase shows error card on workspace
  //   The error detail block is omitted when no message is present.
  it("omits the error detail block when errorMessage is absent", () => {
    render(
      <WorkflowFailedCard
        currentPhase="content"
        errorMessage={undefined}
        onRetry={vi.fn()}
        isRetrying={false}
      />,
    );

    expect(screen.queryByText("Error details")).not.toBeInTheDocument();
  });

  // Scenario: Retry button restarts the workflow
  //   When the user clicks "Retry Workflow"
  //   Then the workflow start() is called with the project's inputs
  it("calls onRetry when the retry button is clicked", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <WorkflowFailedCard
        currentPhase="content"
        errorMessage="boom"
        onRetry={onRetry}
        isRetrying={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Retry Workflow" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  // Scenario: Retry button restarts the workflow
  //   And the button is disabled while retrying
  it("disables the retry button and shows the retrying label while in-flight", () => {
    render(
      <WorkflowFailedCard
        currentPhase="content"
        errorMessage="boom"
        onRetry={vi.fn()}
        isRetrying
      />,
    );

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(screen.getByText("Restarting workflow…")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Retry Workflow" }),
    ).not.toBeInTheDocument();
  });

  // Scenario: Retry button restarts the workflow
  //   A disabled button cannot trigger onRetry (idempotency at the UI layer).
  it("does not call onRetry when disabled and clicked", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <WorkflowFailedCard
        currentPhase="content"
        errorMessage="boom"
        onRetry={onRetry}
        isRetrying
      />,
    );

    await user.click(screen.getByRole("button"));

    expect(onRetry).not.toHaveBeenCalled();
  });
});
