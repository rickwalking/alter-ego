import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Label } from "./label";

describe("Label Component", () => {
  describe("Given the Label component is rendered", () => {
    describe("When the Label contains text content", () => {
      it("Then the Label should display the text", () => {
        render(<Label>Label Text</Label>);
        expect(screen.getByText("Label Text")).toBeInTheDocument();
      });
    });

    describe("When the Label is associated with an input via htmlFor", () => {
      it("Then the Label should be associated with the input element", () => {
        render(
          <>
            <Label htmlFor="username">Username</Label>
            <input id="username" type="text" />
          </>
        );
        expect(screen.getByLabelText("Username")).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Label", () => {
        render(<Label className="custom-class" data-testid="label">Custom</Label>);
        expect(screen.getByTestId("label")).toHaveClass("custom-class");
      });
    });

    describe("When rendered with default styling", () => {
      it("Then it should have the base label classes", () => {
        render(<Label data-testid="label">Test</Label>);
        const label = screen.getByTestId("label");
        expect(label).toHaveClass("text-sm");
        expect(label).toHaveClass("font-medium");
        expect(label).toHaveClass("leading-none");
      });
    });

    describe("When the Label is used with form controls", () => {
      it("Then it should work with various input types", () => {
        const { rerender } = render(
          <>
            <Label htmlFor="email">Email</Label>
            <input id="email" type="email" />
          </>
        );
        expect(screen.getByLabelText("Email")).toHaveAttribute("type", "email");

        rerender(
          <>
            <Label htmlFor="password">Password</Label>
            <input id="password" type="password" />
          </>
        );
        expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
      });

      it("Then it should work with textarea elements", () => {
        render(
          <>
            <Label htmlFor="description">Description</Label>
            <textarea id="description" />
          </>
        );
        expect(screen.getByLabelText("Description")).toBeInTheDocument();
      });
    });

    describe("When the Label is disabled via peer", () => {
      it("Then it should support peer-disabled styling", () => {
        render(
          <>
            <input id="disabled-input" disabled className="peer" />
            <Label htmlFor="disabled-input" data-testid="label">Disabled Label</Label>
          </>
        );
        const label = screen.getByTestId("label");
        expect(label).toHaveClass("peer-disabled:cursor-not-allowed");
        expect(label).toHaveClass("peer-disabled:opacity-70");
      });
    });

    describe("When the Label has complex children", () => {
      it("Then it should render nested elements correctly", () => {
        render(
          <Label>
            <span>Required Field</span>
            <span className="text-red-500">*</span>
          </Label>
        );
        expect(screen.getByText("Required Field")).toBeInTheDocument();
        expect(screen.getByText("*")).toBeInTheDocument();
      });
    });
  });
});
