import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Alert, AlertTitle, AlertDescription } from "./alert";

describe("Alert Component", () => {
  describe("Given the Alert component is rendered", () => {
    describe("When the Alert contains child content", () => {
      it("Then the Alert should display the content with alert role", () => {
        render(
          <Alert data-testid="alert">
            <p>Alert message</p>
          </Alert>,
        );
        expect(screen.getByTestId("alert")).toBeInTheDocument();
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });
    });

    describe("When the default variant is used", () => {
      it("Then the Alert should have default styling", () => {
        render(<Alert data-testid="alert">Default alert</Alert>);
        expect(screen.getByTestId("alert")).toHaveClass(
          "bg-[var(--color-background)]",
        );
      });
    });

    describe("When the destructive variant is specified", () => {
      it("Then the Alert should have destructive styling", () => {
        render(
          <Alert variant="destructive" data-testid="alert">
            Destructive alert
          </Alert>,
        );
        expect(screen.getByTestId("alert")).toHaveClass(
          "border-[var(--color-destructive)]/50",
        );
        expect(screen.getByTestId("alert")).toHaveClass(
          "text-[var(--color-destructive)]",
        );
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Alert", () => {
        render(<Alert className="custom-class" data-testid="alert" />);
        expect(screen.getByTestId("alert")).toHaveClass("custom-class");
      });
    });
  });

  describe("Given the AlertTitle component is rendered", () => {
    describe("When the AlertTitle contains text", () => {
      it("Then the title should be rendered as a heading", () => {
        render(<AlertTitle>Alert Title</AlertTitle>);
        expect(
          screen.getByRole("heading", { name: /alert title/i }),
        ).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the AlertTitle", () => {
        render(<AlertTitle className="custom-title">Title</AlertTitle>);
        expect(screen.getByRole("heading")).toHaveClass("custom-title");
      });
    });

    describe("When rendered with default styling", () => {
      it("Then it should have the title styling classes", () => {
        render(<AlertTitle>Title</AlertTitle>);
        const title = screen.getByRole("heading");
        expect(title).toHaveClass("font-medium");
        expect(title).toHaveClass("mb-1");
      });
    });
  });

  describe("Given the AlertDescription component is rendered", () => {
    describe("When the AlertDescription contains text", () => {
      it("Then the description text should be displayed", () => {
        render(<AlertDescription>Description text</AlertDescription>);
        expect(screen.getByText("Description text")).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the AlertDescription", () => {
        render(
          <AlertDescription className="custom-desc">
            Description
          </AlertDescription>,
        );
        expect(screen.getByText("Description")).toHaveClass("custom-desc");
      });
    });

    describe("When rendered with default styling", () => {
      it("Then it should have the description styling classes", () => {
        render(<AlertDescription>Description</AlertDescription>);
        const desc = screen.getByText("Description");
        expect(desc).toHaveClass("text-sm");
      });
    });
  });

  describe("Given a complete Alert structure is rendered", () => {
    describe("When AlertTitle and AlertDescription are used together", () => {
      it("Then the complete Alert should render with title and description", () => {
        render(
          <Alert>
            <AlertTitle>Warning</AlertTitle>
            <AlertDescription>This is a warning message</AlertDescription>
          </Alert>,
        );

        expect(
          screen.getByRole("heading", { name: /warning/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByText("This is a warning message"),
        ).toBeInTheDocument();
      });
    });

    describe("When both default and destructive variants are used", () => {
      it("Then both variants should render correctly", () => {
        const { rerender } = render(
          <Alert data-testid="alert">
            <AlertTitle>Default</AlertTitle>
            <AlertDescription>Default alert description</AlertDescription>
          </Alert>,
        );
        expect(screen.getByTestId("alert")).toHaveClass(
          "bg-[var(--color-background)]",
        );

        rerender(
          <Alert variant="destructive" data-testid="alert">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>Error alert description</AlertDescription>
          </Alert>,
        );
        expect(screen.getByTestId("alert")).toHaveClass(
          "border-[var(--color-destructive)]/50",
        );
      });
    });
  });
});
