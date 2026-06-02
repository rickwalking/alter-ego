import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonInput } from "@/components/atoms/neon-input";
import { TEXT } from "@/constants/neon";

// Feature: NeonInput Component
describe("NeonInput Component", () => {
  describe("When rendered with a placeholder", () => {
    it("Then the input should be visible and accessible", () => {
      render(<NeonInput placeholder="Email" aria-label="Email" />);
      expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
    });

    it("Then it should apply the neon text color", () => {
      render(<NeonInput aria-label="Email" />);
      expect(screen.getByLabelText("Email")).toHaveStyle({ color: TEXT });
    });
  });
});
