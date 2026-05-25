import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Skeleton } from "./skeleton";

describe("Skeleton Component", () => {
  describe("Given the Skeleton component is rendered", () => {
    describe("When the Skeleton is displayed", () => {
      it("Then the Skeleton should be in the document", () => {
        render(<Skeleton data-testid="skeleton" />);
        expect(screen.getByTestId("skeleton")).toBeInTheDocument();
      });
    });

    describe("When the Skeleton is rendered with default styling", () => {
      it("Then it should have the animate-pulse class", () => {
        render(<Skeleton data-testid="skeleton" />);
        expect(screen.getByTestId("skeleton")).toHaveClass("animate-pulse");
      });

      it("Then it should have the base skeleton classes", () => {
        render(<Skeleton data-testid="skeleton" />);
        const skeleton = screen.getByTestId("skeleton");
        expect(skeleton).toHaveClass("rounded-md");
        expect(skeleton).toHaveClass("bg-[var(--color-muted)]");
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Skeleton", () => {
        render(<Skeleton className="custom-class" data-testid="skeleton" />);
        expect(screen.getByTestId("skeleton")).toHaveClass("custom-class");
      });
    });

    describe("When the Skeleton contains children", () => {
      it("Then the children should be rendered inside the Skeleton", () => {
        render(
          <Skeleton data-testid="skeleton">
            <div>Loading content</div>
          </Skeleton>,
        );
        expect(screen.getByTestId("skeleton")).toBeInTheDocument();
        expect(screen.getByText("Loading content")).toBeInTheDocument();
      });
    });

    describe("When the Skeleton is used as a loading placeholder", () => {
      it("Then it should be usable for various content types", () => {
        const { rerender } = render(
          <Skeleton className="h-4 w-full" data-testid="skeleton" />,
        );
        expect(screen.getByTestId("skeleton")).toHaveClass("h-4", "w-full");

        rerender(
          <Skeleton
            className="h-12 w-12 rounded-full"
            data-testid="skeleton"
          />,
        );
        expect(screen.getByTestId("skeleton")).toHaveClass(
          "h-12",
          "w-12",
          "rounded-full",
        );

        rerender(<Skeleton className="h-32 w-full" data-testid="skeleton" />);
        expect(screen.getByTestId("skeleton")).toHaveClass("h-32", "w-full");
      });
    });

    describe("When multiple Skeletons are rendered", () => {
      it("Then each Skeleton should be independently styled", () => {
        render(
          <>
            <Skeleton className="skeleton-1" data-testid="skeleton-1" />
            <Skeleton className="skeleton-2" data-testid="skeleton-2" />
            <Skeleton className="skeleton-3" data-testid="skeleton-3" />
          </>,
        );
        expect(screen.getByTestId("skeleton-1")).toHaveClass("skeleton-1");
        expect(screen.getByTestId("skeleton-2")).toHaveClass("skeleton-2");
        expect(screen.getByTestId("skeleton-3")).toHaveClass("skeleton-3");
      });
    });
  });
});
