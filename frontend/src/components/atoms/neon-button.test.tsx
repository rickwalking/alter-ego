import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NeonButton, neonButtonVariants } from "@/components/atoms/neon-button";

// Feature: NeonButton Component
describe("NeonButton Component", () => {
  describe("neonButtonVariants", () => {
    it("applies primary gradient classes", () => {
      expect(neonButtonVariants({ variant: "primary" })).toContain(
        "from-neon-cyan",
      );
    });

    it("applies secondary border classes", () => {
      expect(neonButtonVariants({ variant: "secondary" })).toContain("border");
      expect(neonButtonVariants({ variant: "secondary" })).toContain(
        "text-neon-cyan",
      );
    });

    it("applies ghost transparent classes", () => {
      expect(neonButtonVariants({ variant: "ghost" })).toContain(
        "bg-transparent",
      );
    });

    it("applies danger red gradient classes", () => {
      expect(neonButtonVariants({ variant: "danger" })).toContain(
        "from-neon-red",
      );
    });

    it("applies link underline classes", () => {
      expect(neonButtonVariants({ variant: "link" })).toContain(
        "underline-offset-4",
      );
    });

    it("applies size sm, md, lg, and icon classes", () => {
      expect(neonButtonVariants({ size: "sm" })).toContain("h-8");
      expect(neonButtonVariants({ size: "md" })).toContain("h-10");
      expect(neonButtonVariants({ size: "lg" })).toContain("h-12");
      expect(neonButtonVariants({ size: "icon" })).toContain("w-10");
    });

    it("applies fullWidth class when enabled", () => {
      expect(neonButtonVariants({ fullWidth: true })).toContain("w-full");
    });

    it("defaults to primary and md size", () => {
      const classes = neonButtonVariants({});
      expect(classes).toContain("from-neon-cyan");
      expect(classes).toContain("h-10");
    });

    it("produces distinct classes per variant", () => {
      const primary = neonButtonVariants({ variant: "primary" });
      const secondary = neonButtonVariants({ variant: "secondary" });
      const ghost = neonButtonVariants({ variant: "ghost" });
      const danger = neonButtonVariants({ variant: "danger" });
      expect(primary).not.toEqual(secondary);
      expect(secondary).not.toEqual(ghost);
      expect(ghost).not.toEqual(danger);
    });

    it("produces distinct classes per size", () => {
      expect(neonButtonVariants({ size: "sm" })).not.toEqual(
        neonButtonVariants({ size: "lg" }),
      );
    });
  });

  describe("Given the NeonButton component is rendered", () => {
    describe("When a primary variant is rendered with text 'Submit'", () => {
      it("Then the button should be visible with the provided text", () => {
        render(<NeonButton variant="primary">Submit</NeonButton>);
        expect(
          screen.getByRole("button", { name: /submit/i }),
        ).toBeInTheDocument();
      });

      it("Then the button should have primary gradient classes", () => {
        render(<NeonButton variant="primary">Submit</NeonButton>);
        expect(screen.getByRole("button").className).toMatch(/from-neon-cyan/);
      });
    });

    describe("When the button has disabled prop set to true", () => {
      it("Then the button should be disabled and not respond to clicks", async () => {
        const handleClick = vi.fn();
        const user = userEvent.setup();

        render(
          <NeonButton disabled onClick={handleClick}>
            Disabled
          </NeonButton>,
        );

        const button = screen.getByRole("button");
        expect(button).toBeDisabled();
        expect(button).toHaveAttribute("aria-disabled", "true");

        await user.click(button);
        expect(handleClick).not.toHaveBeenCalled();
      });
    });

    describe("When the button is in loading state", () => {
      it("Then a spinner should be shown and button should be disabled", () => {
        render(<NeonButton loading>Processing</NeonButton>);

        const button = screen.getByRole("button");
        expect(button).toBeDisabled();
        expect(button).toHaveAttribute("aria-busy", "true");
        expect(button.querySelector('[role="status"]')).toBeInTheDocument();
        expect(button).toHaveTextContent("Processing");
      });

      it("Then icons should not render while loading", () => {
        render(
          <NeonButton loading icon={<span data-testid="icon">★</span>}>
            Save
          </NeonButton>,
        );
        expect(screen.queryByTestId("icon")).not.toBeInTheDocument();
      });
    });

    describe("When the user clicks the button", () => {
      it("Then the onClick handler should be called", async () => {
        const handleClick = vi.fn();
        const user = userEvent.setup();

        render(<NeonButton onClick={handleClick}>Click</NeonButton>);
        await user.click(screen.getByRole("button"));

        expect(handleClick).toHaveBeenCalledTimes(1);
      });
    });

    describe("When fullWidth prop is true", () => {
      it("Then the button should have w-full class", () => {
        render(<NeonButton fullWidth>Full Width</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("w-full");
      });
    });

    describe("When different size props are provided", () => {
      it("Then the button should have corresponding size classes", () => {
        const { rerender } = render(<NeonButton size="sm">Small</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("h-8");

        rerender(<NeonButton size="md">Medium</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("h-10");

        rerender(<NeonButton size="lg">Large</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("h-12");
      });
    });

    describe("When type prop is specified", () => {
      it("Then the button should have the correct type attribute", () => {
        render(<NeonButton type="submit">Submit</NeonButton>);
        expect(screen.getByRole("button")).toHaveAttribute("type", "submit");
      });
    });

    describe("When variant props are provided", () => {
      it("Then secondary variant should expose outline styling class", () => {
        render(<NeonButton variant="secondary">Cancel</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("border");
      });

      it("Then ghost variant should expose transparent background class", () => {
        render(<NeonButton variant="ghost">Dismiss</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("bg-transparent");
      });

      it("Then danger variant should expose danger gradient class", () => {
        render(<NeonButton variant="danger">Delete</NeonButton>);
        expect(screen.getByRole("button").className).toMatch(/from-neon-red/);
      });

      it("Then link variant should expose link styling", () => {
        render(<NeonButton variant="link">Learn more</NeonButton>);
        expect(screen.getByRole("button").className).toMatch(
          /underline-offset-4/,
        );
      });

      it("Then outline variant should match secondary border styling", () => {
        render(<NeonButton variant="outline">Outline</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("text-neon-cyan");
      });

      it("Then destructive variant should match danger styling", () => {
        render(<NeonButton variant="destructive">Remove</NeonButton>);
        expect(screen.getByRole("button").className).toMatch(/from-neon-red/);
      });

      it("Then default variant should match primary styling", () => {
        render(<NeonButton variant="default">Default</NeonButton>);
        expect(screen.getByRole("button").className).toMatch(/from-neon-cyan/);
      });
    });

    describe("When icon props are provided", () => {
      it("Then left icon should render by default", () => {
        render(
          <NeonButton icon={<span data-testid="left-icon">L</span>}>
            With Icon
          </NeonButton>,
        );
        expect(screen.getByTestId("left-icon")).toBeInTheDocument();
      });

      it("Then right icon should render when iconPosition is right", () => {
        render(
          <NeonButton
            icon={<span data-testid="right-icon">R</span>}
            iconPosition="right"
          >
            Send
          </NeonButton>,
        );
        expect(screen.getByTestId("right-icon")).toBeInTheDocument();
      });
    });

    describe("When custom className is provided", () => {
      it("Then merged classes should include the custom class", () => {
        render(<NeonButton className="custom-class">Styled</NeonButton>);
        expect(screen.getByRole("button")).toHaveClass("custom-class");
      });
    });

    describe("When not loading", () => {
      it("Then aria-busy should not be true", () => {
        render(<NeonButton>Idle</NeonButton>);
        expect(screen.getByRole("button")).not.toHaveAttribute(
          "aria-busy",
          "true",
        );
      });
    });
  });
});
