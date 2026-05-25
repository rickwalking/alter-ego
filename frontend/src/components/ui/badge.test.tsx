import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./badge";

describe("Badge Component", () => {
  describe("Given the Badge component is rendered", () => {
    describe("When the Badge contains text content", () => {
      it("Then the Badge should display the text", () => {
        render(<Badge>New</Badge>);
        expect(screen.getByText("New")).toBeInTheDocument();
      });
    });

    describe("When the default variant is used", () => {
      it("Then the Badge should have default styling with primary colors", () => {
        render(<Badge data-testid="badge">Default</Badge>);
        const badge = screen.getByTestId("badge");
        expect(badge).toHaveClass("bg-[var(--color-primary)]");
        expect(badge).toHaveClass("text-[var(--color-primary-foreground)]");
      });
    });

    describe("When the secondary variant is specified", () => {
      it("Then the Badge should have secondary styling", () => {
        render(
          <Badge variant="secondary" data-testid="badge">
            Secondary
          </Badge>,
        );
        const badge = screen.getByTestId("badge");
        expect(badge).toHaveClass("bg-[var(--color-secondary)]");
        expect(badge).toHaveClass("text-[var(--color-secondary-foreground)]");
      });
    });

    describe("When the destructive variant is specified", () => {
      it("Then the Badge should have destructive styling", () => {
        render(
          <Badge variant="destructive" data-testid="badge">
            Destructive
          </Badge>,
        );
        const badge = screen.getByTestId("badge");
        expect(badge).toHaveClass("bg-[var(--color-destructive)]");
        expect(badge).toHaveClass("text-[var(--color-destructive-foreground)]");
      });
    });

    describe("When the outline variant is specified", () => {
      it("Then the Badge should have outline styling without background", () => {
        render(
          <Badge variant="outline" data-testid="badge">
            Outline
          </Badge>,
        );
        expect(screen.getByTestId("badge")).toHaveClass("border");
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Badge", () => {
        render(
          <Badge className="custom-class" data-testid="badge">
            Custom
          </Badge>,
        );
        expect(screen.getByTestId("badge")).toHaveClass("custom-class");
      });
    });

    describe("When rendered with default styling", () => {
      it("Then it should have the base badge classes", () => {
        render(<Badge data-testid="badge">Badge</Badge>);
        const badge = screen.getByTestId("badge");
        expect(badge).toHaveClass("inline-flex");
        expect(badge).toHaveClass("items-center");
        expect(badge).toHaveClass("rounded-full");
        expect(badge).toHaveClass("px-2.5");
        expect(badge).toHaveClass("py-0.5");
        expect(badge).toHaveClass("text-xs");
        expect(badge).toHaveClass("font-semibold");
      });
    });

    describe("When the Badge contains multiple children", () => {
      it("Then all children should be rendered", () => {
        render(
          <Badge data-testid="badge">
            <span>Icon</span>
            <span>Text</span>
          </Badge>,
        );
        expect(screen.getByText("Icon")).toBeInTheDocument();
        expect(screen.getByText("Text")).toBeInTheDocument();
      });
    });

    describe("When switching between variants", () => {
      it("Then the variant classes should update correctly", () => {
        const { rerender } = render(
          <Badge variant="default" data-testid="badge">
            Badge
          </Badge>,
        );
        let badge = screen.getByTestId("badge");
        expect(badge).toHaveClass("bg-[var(--color-primary)]");

        rerender(
          <Badge variant="secondary" data-testid="badge">
            Badge
          </Badge>,
        );
        badge = screen.getByTestId("badge");
        expect(badge).toHaveClass("bg-[var(--color-secondary)]");

        rerender(
          <Badge variant="destructive" data-testid="badge">
            Badge
          </Badge>,
        );
        badge = screen.getByTestId("badge");
        expect(badge).toHaveClass("bg-[var(--color-destructive)]");

        rerender(
          <Badge variant="outline" data-testid="badge">
            Badge
          </Badge>,
        );
        badge = screen.getByTestId("badge");
        expect(badge).toHaveClass("border");
      });
    });
  });
});
