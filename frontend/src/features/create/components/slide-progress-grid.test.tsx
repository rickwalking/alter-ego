import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SlideProgressGrid } from "./slide-progress-grid";
import { SLIDE_GENERATION_STATUS } from "@/constants/create";

describe("SlideProgressGrid", () => {
  describe("Given an empty slide list", () => {
    it("should render nothing (no data-testid leaked)", () => {
      const { container } = render(<SlideProgressGrid slides={[]} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe("Given a populated slide list", () => {
    const slides = [
      { number: 1, status: SLIDE_GENERATION_STATUS.DONE, scene: "Intro scene" },
      {
        number: 2,
        status: SLIDE_GENERATION_STATUS.IN_FLIGHT,
        scene: "Body scene",
      },
      { number: 3, status: SLIDE_GENERATION_STATUS.FAILED, scene: "Scene 3" },
      { number: 4, status: SLIDE_GENERATION_STATUS.PENDING },
    ];

    it("should render one list item per slide keyed by number", () => {
      render(<SlideProgressGrid slides={slides} />);
      expect(screen.getByTestId("phase-slide-1")).toBeInTheDocument();
      expect(screen.getByTestId("phase-slide-2")).toBeInTheDocument();
      expect(screen.getByTestId("phase-slide-3")).toBeInTheDocument();
      expect(screen.getByTestId("phase-slide-4")).toBeInTheDocument();
    });

    it("should expose status via data-status for styling and assertions", () => {
      render(<SlideProgressGrid slides={slides} />);
      expect(screen.getByTestId("phase-slide-1")).toHaveAttribute(
        "data-status",
        "done",
      );
      expect(screen.getByTestId("phase-slide-3")).toHaveAttribute(
        "data-status",
        "failed",
      );
    });

    it("should render the scene description when provided", () => {
      render(<SlideProgressGrid slides={slides} />);
      expect(screen.getByText("Intro scene")).toBeInTheDocument();
      expect(screen.getByText("Body scene")).toBeInTheDocument();
    });

    it("should skip the scene line when absent", () => {
      render(<SlideProgressGrid slides={[slides[3]]} />);
      // slide #4 has no scene — only the "Slide 4" label should appear.
      expect(screen.getByText("Slide 4")).toBeInTheDocument();
    });
  });
});
