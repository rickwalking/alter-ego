import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CarouselProgress } from "./create-carousel-progress";
import { SlideProgressGrid } from "./slide-progress-grid";

// AE-0299 — visual-token migration of the Fluxo Editorial progress panel.
// Pure refactor (AE-0153): behavior/data contract unchanged; these tests pin
// the Neon-token + a11y invariants the migration introduced.

const WORKSPACE_DIR = join(process.cwd(), "src/app/dashboard/create/workspace");
const MIGRATED_FILES = [
  "create-workflow-progress.tsx",
  "create-carousel-progress.tsx",
  "phase-item.tsx",
  "phase-progress-detail.tsx",
  "slide-progress-grid.tsx",
  "progress-icons.tsx",
];
const LEGACY_TOKEN_PATTERNS = [
  "var(--color-primary)",
  "var(--color-text)]",
  "bg-destructive",
  "text-destructive",
  "bg-warning",
  "text-warning",
];

describe("AE-0299 legacy-token eradication", () => {
  it.each(MIGRATED_FILES)("%s carries no legacy shadcn tokens", (file) => {
    const source = readFileSync(join(WORKSPACE_DIR, file), "utf8");
    for (const pattern of LEGACY_TOKEN_PATTERNS) {
      expect(source, `${file} still references ${pattern}`).not.toContain(
        pattern,
      );
    }
  });
});

describe("CarouselProgress (AE-0299)", () => {
  it("active state renders exactly one status live region with a reduced-motion-safe pulse", () => {
    const { container } = render(
      <CarouselProgress
        currentPhase="generating_images"
        isComplete={false}
        hasError={false}
        phaseProgress={{
          phase: "generating_images",
          label: "Generating 6 slide images",
          current: 3,
          total: 6,
        }}
      />,
    );
    const statusRegions = screen.getAllByRole("status");
    expect(statusRegions).toHaveLength(1);
    expect(statusRegions[0]).toHaveTextContent("In progress");
    const pulse = container.querySelector(".animate-pulse");
    expect(pulse).not.toBeNull();
    expect(pulse?.className).toContain("motion-reduce:animate-none");
  });

  it("complete state renders exactly one status live region (completed badge)", () => {
    render(<CarouselProgress currentPhase="" isComplete hasError={false} />);
    const statusRegions = screen.getAllByRole("status");
    expect(statusRegions).toHaveLength(1);
    expect(statusRegions[0]).toHaveTextContent("Completed");
  });

  it("error state renders a NeonAlert with the failure message", () => {
    render(
      <CarouselProgress
        currentPhase=""
        isComplete={false}
        hasError
        errorMessage="boom from upstream"
      />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("boom from upstream");
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("keeps the phase checklist and progress bar behavior unchanged", () => {
    render(
      <CarouselProgress
        currentPhase="drafting"
        isComplete={false}
        hasError={false}
        phaseProgress={{
          phase: "drafting",
          label: "Drafting bilingual slide content",
          current: 2,
          total: 6,
        }}
      />,
    );
    expect(screen.getByTestId("phase-item-drafting")).toBeInTheDocument();
    expect(screen.getByTestId("phase-progress-bar")).toBeInTheDocument();
    expect(screen.getByText("2 / 6")).toBeInTheDocument();
  });
});

describe("SlideProgressGrid i18n (AE-0299)", () => {
  it("renders the localized slide label instead of hardcoded copy", () => {
    render(
      <SlideProgressGrid
        slides={[
          { number: 1, status: "done" },
          { number: 2, status: "in_flight" },
        ]}
      />,
    );
    expect(screen.getByText("Slide 1")).toBeInTheDocument();
    expect(screen.getByTestId("phase-slide-2")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Per-slide image generation status"),
    ).toBeInTheDocument();
  });
});
