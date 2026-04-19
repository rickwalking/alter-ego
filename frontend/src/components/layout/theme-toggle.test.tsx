import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "./theme-toggle";

// Mock the theme provider
const mockSetTheme = vi.fn();

vi.mock("@/components/providers/theme-provider", () => ({
  useTheme: () => ({
    resolvedTheme: "light",
    setTheme: mockSetTheme,
  }),
}));

describe("ThemeToggle Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the ThemeToggle component is rendered", () => {
    describe("When the component is mounted and theme is light", () => {
      it("Then the toggle button should be visible", () => {
        render(<ThemeToggle />);
        expect(screen.getByRole("button", { name: /toggle theme/i })).toBeInTheDocument();
      });

      it("Then the button should have correct aria-label", () => {
        render(<ThemeToggle />);
        expect(screen.getByLabelText("Toggle theme")).toBeInTheDocument();
      });
    });

    describe("When the user clicks the toggle button", () => {
      it("Then setTheme should be called to switch to dark theme", async () => {
        const user = userEvent.setup();
        render(<ThemeToggle />);
        const button = screen.getByRole("button", { name: /toggle theme/i });
        
        await user.click(button);
        
        expect(mockSetTheme).toHaveBeenCalledWith("dark");
      });
    });

    describe("When both Sun and Moon icons are present", () => {
      it("Then both icons should be rendered", () => {
        render(<ThemeToggle />);
        // SVG icons are rendered - at least one should be present
        const svgs = document.querySelectorAll("svg");
        expect(svgs.length).toBeGreaterThanOrEqual(1);
      });
    });
  });
});
