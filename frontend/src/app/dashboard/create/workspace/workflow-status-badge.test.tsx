import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorkflowStatusBadge } from "./workflow-status-badge";

// Scenarios: see tests/features/create-workflow-status-badge.feature

vi.mock("next-intl", () => ({
  // Echo the key so we can assert which label key was looked up.
  useTranslations: () => (key: string) => key,
}));

describe("WorkflowStatusBadge", () => {
  it("renders a live pulsing dot for in_progress", () => {
    const { container } = render(<WorkflowStatusBadge status="in_progress" />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveAttribute("aria-label", "status.inProgress");
    // The dot is the animated leading element inside the badge.
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("does not pulse for a settled state", () => {
    const { container } = render(<WorkflowStatusBadge status="failed" />);
    expect(container.querySelector(".animate-pulse")).toBeNull();
    expect(screen.getByRole("status")).toHaveAttribute(
      "aria-label",
      "status.failed",
    );
  });

  it("titlecases an unknown status as its own label", () => {
    render(<WorkflowStatusBadge status="brand_new_state" />);
    expect(screen.getByRole("status")).toHaveTextContent("Brand New State");
  });

  it("honours a label override while keeping the semantic colour", () => {
    render(<WorkflowStatusBadge status="failed" label="content" />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveTextContent("content");
    expect(badge).toHaveAttribute("aria-label", "content");
  });

  it("resolves a missing status to the Draft label", () => {
    render(<WorkflowStatusBadge status={null} />);
    expect(screen.getByRole("status")).toHaveAttribute(
      "aria-label",
      "status.draft",
    );
  });
});
