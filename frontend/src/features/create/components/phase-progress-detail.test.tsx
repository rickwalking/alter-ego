import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PhaseProgressDetail } from "./phase-progress-detail";
import { SLIDE_GENERATION_STATUS } from "@/constants/create";

describe("PhaseProgressDetail", () => {
  describe("Given only a label", () => {
    it("should render the label and nothing else", () => {
      render(<PhaseProgressDetail label="Searching the web" />);
      expect(screen.getByTestId("phase-progress-label")).toHaveTextContent(
        "Searching the web",
      );
      expect(screen.queryByTestId("phase-progress-bar")).toBeNull();
      expect(screen.queryByTestId("phase-progress-slides")).toBeNull();
    });
  });

  describe("Given current/total progress", () => {
    it("should render a progress bar with the right width", () => {
      render(<PhaseProgressDetail label="Images" current={3} total={4} />);
      const bar = screen.getByTestId("phase-progress-bar");
      expect(bar).toHaveStyle({ width: "75%" });
    });

    it("should display the fraction and percentage", () => {
      render(<PhaseProgressDetail label="Images" current={1} total={2} />);
      expect(screen.getByText("1 / 2")).toBeInTheDocument();
      expect(screen.getByText("50%")).toBeInTheDocument();
    });

    it("should cap the bar width at 100% when current exceeds total", () => {
      render(<PhaseProgressDetail label="Images" current={10} total={4} />);
      const bar = screen.getByTestId("phase-progress-bar");
      expect(bar).toHaveStyle({ width: "100%" });
    });

    it("should skip the bar when total is zero", () => {
      render(<PhaseProgressDetail label="Zero" current={0} total={0} />);
      expect(screen.queryByTestId("phase-progress-bar")).toBeNull();
    });
  });

  describe("Given slide progress data", () => {
    it("should render the slide grid", () => {
      render(
        <PhaseProgressDetail
          label="Images"
          slides={[
            { number: 1, status: SLIDE_GENERATION_STATUS.DONE },
            { number: 2, status: SLIDE_GENERATION_STATUS.IN_FLIGHT },
          ]}
        />,
      );
      expect(screen.getByTestId("phase-progress-slides")).toBeInTheDocument();
      expect(screen.getByTestId("phase-slide-1")).toBeInTheDocument();
    });
  });

  describe("Given a detail line", () => {
    it("should display the italicized detail", () => {
      render(
        <PhaseProgressDetail label="Images" detail="via OpenAI Hyperreal" />,
      );
      expect(screen.getByText("via OpenAI Hyperreal")).toBeInTheDocument();
    });
  });
});
