import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PhaseItem } from "./phase-item";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

// Scenarios: see features/carousel_workspace.feature (PhaseItem)
describe("PhaseItem", () => {
  describe("Given a phase that is active", () => {
    it("should render a spinner and mark aria-current step", () => {
      render(<PhaseItem phase="drafting" isActive isPast={false} index={1} />);
      const container = screen.getByTestId("phase-item-drafting");
      const marker = container.querySelector("[aria-current='step']");
      expect(marker).not.toBeNull();
    });

    it("should not display the index number when active", () => {
      render(<PhaseItem phase="drafting" isActive isPast={false} index={1} />);
      expect(screen.queryByText("2")).toBeNull();
    });
  });

  describe("Given a phase that is in the past", () => {
    it("should render the check icon", () => {
      render(<PhaseItem phase="researching" isActive={false} isPast index={0} />);
      expect(screen.getByTestId("phase-check")).toBeInTheDocument();
    });
  });

  describe("Given a phase that is pending", () => {
    it("should display the 1-indexed position", () => {
      render(
        <PhaseItem phase="exporting" isActive={false} isPast={false} index={4} />,
      );
      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("should not be aria-current", () => {
      render(
        <PhaseItem phase="exporting" isActive={false} isPast={false} index={4} />,
      );
      const container = screen.getByTestId("phase-item-exporting");
      expect(container.querySelector("[aria-current='step']")).toBeNull();
    });
  });
});
