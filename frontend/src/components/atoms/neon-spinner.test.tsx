import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonSpinner, Spinner } from "@/components/atoms/neon-spinner";

// Feature: Reusable Spinner Component (consolidated atom)
// Consolidates the former ui/spinner.tsx into the NeonSpinner atom (AE-0068).

describe("NeonSpinner (pure SVG atom)", () => {
  // Scenario: Default spinner renders for assistive technology
  describe("When a NeonSpinner is rendered with no props", () => {
    it("Then it exposes role=status", () => {
      render(<NeonSpinner />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("Then it falls back to the default 'Loading' aria-label", () => {
      render(<NeonSpinner />);
      expect(screen.getByRole("status")).toHaveAttribute(
        "aria-label",
        "Loading",
      );
    });

    it("Then it uses the medium size class by default", () => {
      const { container } = render(<NeonSpinner />);
      expect(container.querySelector("svg")).toHaveClass("h-6", "w-6");
    });
  });

  // Scenario: Spinner supports size variants
  describe("When a NeonSpinner is rendered with size variants", () => {
    it("Then the small variant applies the small size class", () => {
      const { container } = render(<NeonSpinner size="sm" />);
      expect(container.querySelector("svg")).toHaveClass("h-4", "w-4");
    });

    it("Then the large variant applies the large size class", () => {
      const { container } = render(<NeonSpinner size="lg" />);
      expect(container.querySelector("svg")).toHaveClass("h-8", "w-8");
    });
  });

  // Scenario: Spinner forwards a custom className
  describe("When a NeonSpinner is rendered with a className", () => {
    it("Then the className is applied to the svg", () => {
      const { container } = render(<NeonSpinner className="my-custom-class" />);
      expect(container.querySelector("svg")).toHaveClass("my-custom-class");
    });
  });
});

describe("Spinner (labeled wrapper)", () => {
  // Scenario: Spinner renders with default props
  describe("When a Spinner is rendered with no props", () => {
    it("Then it exposes a single role=status live region", () => {
      render(<Spinner />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("Then it falls back to the default 'Loading' aria-label", () => {
      render(<Spinner />);
      expect(screen.getByRole("status")).toHaveAttribute(
        "aria-label",
        "Loading",
      );
    });

    it("Then it renders no visible label text", () => {
      const { container } = render(<Spinner />);
      expect(container.querySelector("span")).toBeNull();
    });

    it("Then the inner svg uses the medium size class", () => {
      const { container } = render(<Spinner />);
      expect(container.querySelector("svg")).toHaveClass("h-6", "w-6");
    });
  });

  // Scenario: Spinner renders with custom label
  describe("When a Spinner is rendered with a label", () => {
    it("Then it includes the visible label text", () => {
      render(<Spinner label="Loading strategies" />);
      expect(screen.getByText("Loading strategies")).toBeInTheDocument();
    });

    it("Then the label is used as the aria-label", () => {
      render(<Spinner label="Loading strategies" />);
      expect(screen.getByRole("status")).toHaveAttribute(
        "aria-label",
        "Loading strategies",
      );
    });
  });

  // Scenario: Spinner supports size variants
  describe("When a Spinner is rendered with size variants", () => {
    it("Then the small variant applies the small size class to the svg", () => {
      const { container } = render(<Spinner size="sm" />);
      expect(container.querySelector("svg")).toHaveClass("h-4", "w-4");
    });

    it("Then the large variant applies the large size class to the svg", () => {
      const { container } = render(<Spinner size="lg" />);
      expect(container.querySelector("svg")).toHaveClass("h-8", "w-8");
    });
  });

  // Scenario: Spinner forwards a custom className to the wrapper
  describe("When a Spinner is rendered with a className", () => {
    it("Then the className is applied to the wrapper", () => {
      render(<Spinner className="my-custom-class" />);
      expect(screen.getByRole("status")).toHaveClass("my-custom-class");
    });
  });
});
