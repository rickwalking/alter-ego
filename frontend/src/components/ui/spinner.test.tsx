import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Spinner } from "./spinner";

describe("Spinner Component", () => {
  describe("Given the Spinner component is rendered", () => {
    describe("When the Spinner is displayed", () => {
      it("Then the Spinner should be in the document", () => {
        render(<Spinner data-testid="spinner" />);
        expect(screen.getByTestId("spinner")).toBeInTheDocument();
      });
    });

    describe("When the Spinner is rendered with default props", () => {
      it("Then it should have aria-hidden attribute for accessibility", () => {
        render(<Spinner />);
        const spinner = document.querySelector("svg");
        expect(spinner).toHaveAttribute("aria-hidden", "true");
      });

      it("Then it should have the animate-spin class", () => {
        render(<Spinner data-testid="spinner" />);
        expect(screen.getByTestId("spinner")).toHaveClass("animate-spin");
      });
    });

    describe("When different size props are provided", () => {
      it("Then the sm size should have correct dimensions", () => {
        render(<Spinner size="sm" data-testid="spinner" />);
        expect(screen.getByTestId("spinner")).toHaveClass("h-4 w-4");
      });

      it("Then the md size should have correct dimensions", () => {
        render(<Spinner size="md" data-testid="spinner" />);
        expect(screen.getByTestId("spinner")).toHaveClass("h-6 w-6");
      });

      it("Then the lg size should have correct dimensions", () => {
        render(<Spinner size="lg" data-testid="spinner" />);
        expect(screen.getByTestId("spinner")).toHaveClass("h-8 w-8");
      });

      it("Then the default size should be md", () => {
        render(<Spinner data-testid="spinner" />);
        expect(screen.getByTestId("spinner")).toHaveClass("h-6 w-6");
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Spinner", () => {
        render(<Spinner className="custom-class" data-testid="spinner" />);
        expect(screen.getByTestId("spinner")).toHaveClass("custom-class");
      });
    });

    describe("When additional SVG props are provided", () => {
      it("Then the props should be passed to the SVG element", () => {
        render(<Spinner data-testid="spinner" style={{ color: "red" }} />);
        const spinner = screen.getByTestId("spinner");
        expect(spinner).toHaveAttribute("style", "color: red;");
      });
    });

    describe("When switching between sizes", () => {
      it("Then the size classes should update correctly", () => {
        const { rerender } = render(
          <Spinner size="sm" data-testid="spinner" />,
        );
        let spinner = screen.getByTestId("spinner");
        expect(spinner).toHaveClass("h-4 w-4");

        rerender(<Spinner size="md" data-testid="spinner" />);
        spinner = screen.getByTestId("spinner");
        expect(spinner).toHaveClass("h-6 w-6");

        rerender(<Spinner size="lg" data-testid="spinner" />);
        spinner = screen.getByTestId("spinner");
        expect(spinner).toHaveClass("h-8 w-8");
      });
    });

    describe("When the Spinner SVG structure is verified", () => {
      it("Then it should contain a circle and path elements", () => {
        render(<Spinner />);
        const svg = document.querySelector("svg");
        expect(svg).toBeInTheDocument();
        expect(svg?.querySelector("circle")).toBeInTheDocument();
        expect(svg?.querySelector("path")).toBeInTheDocument();
      });

      it("Then the SVG should have correct viewBox", () => {
        render(<Spinner />);
        const svg = document.querySelector("svg");
        expect(svg).toHaveAttribute("viewBox", "0 0 24 24");
      });
    });
  });
});
