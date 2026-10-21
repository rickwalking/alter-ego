import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorkflowStatusBadge } from "./workflow-status-badge";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

/**
 * The translator mock echoes the key so the tests assert which label key was
 * looked up. Outside production an unknown status throws (drift guard); the
 * titlecase fallback is the production-only last resort. A labelled chip must
 * still announce the status word (not colour alone) and is not a live region.
 */
describe("WorkflowStatusBadge", () => {
  it("renders a live pulsing dot for in_progress", () => {
    const { container } = render(<WorkflowStatusBadge status="in_progress" />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveAttribute("aria-label", "status.inProgress");
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

  it("titlecases an unknown status as its own label (production guard)", () => {
    vi.stubEnv("NODE_ENV", "production");
    try {
      render(<WorkflowStatusBadge status="brand_new_state" />);
      expect(screen.getByRole("status")).toHaveTextContent("Brand New State");
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("keeps the status in the accessible name on a label override", () => {
    render(<WorkflowStatusBadge status="failed" label="content" />);
    const badge = screen.getByLabelText("content, status.failed");
    expect(badge).toHaveTextContent("content");
    expect(badge).not.toHaveAttribute("role", "status");
  });

  it("resolves a missing status to the Draft label", () => {
    render(<WorkflowStatusBadge status={null} />);
    expect(screen.getByRole("status")).toHaveAttribute(
      "aria-label",
      "status.draft",
    );
  });
});
