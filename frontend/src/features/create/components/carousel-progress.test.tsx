import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { CarouselProgress } from "./carousel-progress";
import { PIPELINE_PHASES } from "@/constants/create";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => {
    const translations: Record<string, string> = {
      "progress.complete": "Complete!",
      "progress.failed": "Generation failed",
      "progress.currentlyProcessing": "Currently processing",
      "progress.stalled": "Still working after {seconds}s",
      "progress.phases.researching": "Researching",
      "progress.phases.drafting": "Drafting",
      "progress.phases.designing": "Designing",
      "progress.phases.generating_images": "Generating Images",
      "progress.phases.exporting": "Exporting",
      "progress.phases.completed": "Completed",
    };
    return (key: string, params?: Record<string, unknown>) => {
      const raw = translations[key] ?? key;
      if (!params) return raw;
      return raw.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? ""));
    };
  }),
}));

describe("CarouselProgress Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the CarouselProgress is rendered in a complete state", () => {
    describe("When isComplete is true", () => {
      it("Then the complete message should be displayed", () => {
        render(
          <CarouselProgress
            currentPhase="completed"
            isComplete={true}
            hasError={false}
          />
        );
        expect(screen.getByText(/complete!/i)).toBeInTheDocument();
      });

      it("Then no phase list should be shown", () => {
        render(
          <CarouselProgress
            currentPhase="completed"
            isComplete={true}
            hasError={false}
          />
        );
        PIPELINE_PHASES.forEach((phase) => {
          expect(screen.queryByTestId(`phase-item-${phase}`)).not.toBeInTheDocument();
        });
      });
    });
  });

  describe("Given the CarouselProgress is rendered in an error state", () => {
    describe("When hasError is true", () => {
      it("Then the error message should be displayed", () => {
        render(
          <CarouselProgress
            currentPhase="researching"
            isComplete={false}
            hasError={true}
          />
        );
        expect(screen.getByText(/generation failed/i)).toBeInTheDocument();
      });

      it("Then no phase list should be shown", () => {
        render(
          <CarouselProgress
            currentPhase="researching"
            isComplete={false}
            hasError={true}
          />
        );
        PIPELINE_PHASES.forEach((phase) => {
          expect(screen.queryByTestId(`phase-item-${phase}`)).not.toBeInTheDocument();
        });
      });

      it("Then the backend error message is surfaced when provided", () => {
        render(
          <CarouselProgress
            currentPhase="drafting"
            isComplete={false}
            hasError={true}
            errorMessage="Anthropic rate limit exceeded"
          />
        );
        expect(
          screen.getByText(/anthropic rate limit exceeded/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe("Given the CarouselProgress is rendered in an active state", () => {
    describe("When the current phase is researching (first phase)", () => {
      it("Then all phases should be displayed", () => {
        render(
          <CarouselProgress
            currentPhase="researching"
            isComplete={false}
            hasError={false}
          />
        );
        PIPELINE_PHASES.forEach((phase) => {
          expect(screen.getByTestId(`phase-item-${phase}`)).toBeInTheDocument();
        });
      });

      it("Then the researching phase should be marked as active", () => {
        render(
          <CarouselProgress
            currentPhase="researching"
            isComplete={false}
            hasError={false}
          />
        );
        expect(screen.getByTestId("phase-label-researching")).toHaveClass(
          "text-[var(--color-primary)]"
        );
      });

      it("Then no phases should show check marks", () => {
        render(
          <CarouselProgress
            currentPhase="researching"
            isComplete={false}
            hasError={false}
          />
        );
        expect(screen.queryByTestId("phase-check")).not.toBeInTheDocument();
      });
    });

    describe("When the current phase is drafting (second phase)", () => {
      it("Then researching should be marked as past", () => {
        render(
          <CarouselProgress
            currentPhase="drafting"
            isComplete={false}
            hasError={false}
          />
        );
        expect(screen.getByTestId("phase-label-researching")).toHaveClass(
          "text-[var(--color-text)]"
        );
      });

      it("Then drafting should be marked as active", () => {
        render(
          <CarouselProgress
            currentPhase="drafting"
            isComplete={false}
            hasError={false}
          />
        );
        expect(screen.getByTestId("phase-label-drafting")).toHaveClass(
          "text-[var(--color-primary)]"
        );
      });

      it("Then future phases should be muted", () => {
        render(
          <CarouselProgress
            currentPhase="drafting"
            isComplete={false}
            hasError={false}
          />
        );
        expect(screen.getByTestId("phase-label-designing")).toHaveClass(
          "text-[var(--color-text-muted)]"
        );
      });
    });

    describe("When the current phase is completed", () => {
      it("Then all phases except the last should be marked as past", () => {
        render(
          <CarouselProgress
            currentPhase="completed"
            isComplete={false}
            hasError={false}
          />
        );
        PIPELINE_PHASES.slice(0, -1).forEach((phase) => {
          expect(screen.getByTestId(`phase-label-${phase}`)).toHaveClass(
            "text-[var(--color-text)]"
          );
        });
      });

      it("Then the completed phase should be marked as active", () => {
        render(
          <CarouselProgress
            currentPhase="completed"
            isComplete={false}
            hasError={false}
          />
        );
        expect(screen.getByTestId("phase-label-completed")).toHaveClass(
          "text-[var(--color-primary)]"
        );
      });
    });

    describe("When the current phase is generating_images (fourth phase)", () => {
      it("Then researching, drafting, and designing should be marked as past", () => {
        render(
          <CarouselProgress
            currentPhase="generating_images"
            isComplete={false}
            hasError={false}
          />
        );
        ["researching", "drafting", "designing"].forEach((phase) => {
          expect(screen.getByTestId(`phase-label-${phase}`)).toHaveClass(
            "text-[var(--color-text)]"
          );
        });
      });

      it("Then generating_images should be marked as active", () => {
        render(
          <CarouselProgress
            currentPhase="generating_images"
            isComplete={false}
            hasError={false}
          />
        );
        expect(screen.getByTestId("phase-label-generating_images")).toHaveClass(
          "text-[var(--color-primary)]"
        );
      });

      it("Then exporting and completed should be muted", () => {
        render(
          <CarouselProgress
            currentPhase="generating_images"
            isComplete={false}
            hasError={false}
          />
        );
        ["exporting", "completed"].forEach((phase) => {
          expect(screen.getByTestId(`phase-label-${phase}`)).toHaveClass(
            "text-[var(--color-text-muted)]"
          );
        });
      });
    });

    describe("When a phase stalls past the threshold", () => {
      it("Then a stall warning is surfaced", () => {
        // updatedAt far in the past → elapsed far beyond threshold
        const longAgo = new Date(Date.now() - 120_000).toISOString();
        render(
          <CarouselProgress
            currentPhase="drafting"
            isComplete={false}
            hasError={false}
            updatedAt={longAgo}
          />
        );
        expect(screen.getByText(/still working after/i)).toBeInTheDocument();
      });

      it("Then the 'currently processing' header names the active phase", () => {
        render(
          <CarouselProgress
            currentPhase="drafting"
            isComplete={false}
            hasError={false}
          />
        );
        // Header shows the name in addition to the list — both should exist.
        const labels = screen.getAllByText(/drafting/i);
        expect(labels.length).toBeGreaterThanOrEqual(2);
      });
    });
  });

  describe("Given the phase ordering logic", () => {
    describe("When checking the number of phases displayed", () => {
      it("Then all six phases should be rendered", () => {
        render(
          <CarouselProgress
            currentPhase="designing"
            isComplete={false}
            hasError={false}
          />
        );
        PIPELINE_PHASES.forEach((phase) => {
          expect(screen.getByTestId(`phase-item-${phase}`)).toBeInTheDocument();
        });
      });
    });
  });
});
