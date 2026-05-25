import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./button";

describe("Button Component", () => {
  describe("Given the Button component is rendered", () => {
    describe("When the button is displayed with text content", () => {
      it("Then the button should be visible with the provided text", () => {
        render(<Button>Click me</Button>);
        expect(
          screen.getByRole("button", { name: /click me/i }),
        ).toBeInTheDocument();
      });
    });

    describe("When the user clicks the button", () => {
      it("Then the onClick handler should be called", async () => {
        const handleClick = vi.fn();
        const user = userEvent.setup();

        render(<Button onClick={handleClick}>Click</Button>);
        await user.click(screen.getByRole("button"));

        expect(handleClick).toHaveBeenCalledTimes(1);
      });
    });

    describe("When the button has disabled prop set to true", () => {
      it("Then the button should be disabled and not respond to clicks", async () => {
        const handleClick = vi.fn();
        const user = userEvent.setup();

        render(
          <Button disabled onClick={handleClick}>
            Disabled
          </Button>,
        );

        const button = screen.getByRole("button");
        expect(button).toBeDisabled();

        await user.click(button);
        expect(handleClick).not.toHaveBeenCalled();
      });
    });

    describe("When different variant props are provided", () => {
      it("Then the destructive variant should have destructive styling", () => {
        const { rerender } = render(
          <Button variant="destructive">Destructive</Button>,
        );
        expect(screen.getByRole("button")).toHaveClass(
          "bg-[var(--color-destructive)]",
        );

        rerender(<Button variant="outline">Outline</Button>);
        expect(screen.getByRole("button")).toHaveClass("border");

        rerender(<Button variant="ghost">Ghost</Button>);
        expect(screen.getByRole("button")).toHaveClass(
          "hover:bg-[var(--color-accent)]",
        );

        rerender(<Button variant="secondary">Secondary</Button>);
        expect(screen.getByRole("button")).toHaveClass(
          "bg-[var(--color-secondary)]",
        );

        rerender(<Button variant="link">Link</Button>);
        expect(screen.getByRole("button")).toHaveClass("underline-offset-4");
      });
    });

    describe("When different size props are provided", () => {
      it("Then the button should have corresponding size classes", () => {
        const { rerender } = render(<Button size="sm">Small</Button>);
        expect(screen.getByRole("button")).toHaveClass("h-9");

        rerender(<Button size="lg">Large</Button>);
        expect(screen.getByRole("button")).toHaveClass("h-11");

        rerender(<Button size="icon">Icon</Button>);
        expect(screen.getByRole("button")).toHaveClass("h-10 w-10");

        rerender(<Button size="default">Default</Button>);
        expect(screen.getByRole("button")).toHaveClass("h-10");
      });
    });

    describe("When the asChild prop is true", () => {
      it("Then the button should render as the child element", () => {
        render(
          <Button asChild>
            <a href="/test">Link Button</a>
          </Button>,
        );

        expect(
          screen.getByRole("link", { name: /link button/i }),
        ).toBeInTheDocument();
      });
    });

    describe("When a ref is forwarded to the button", () => {
      it("Then the ref should reference the button element", () => {
        const ref = { current: null as HTMLButtonElement | null };
        render(<Button ref={ref}>Ref Test</Button>);
        expect(ref.current).toBeInstanceOf(HTMLButtonElement);
      });
    });

    describe("When type prop is specified", () => {
      it("Then the button should have the correct type attribute", () => {
        const { rerender } = render(<Button type="button">Button</Button>);
        expect(screen.getByRole("button")).toHaveAttribute("type", "button");

        rerender(<Button type="submit">Submit</Button>);
        expect(screen.getByRole("button")).toHaveAttribute("type", "submit");

        rerender(<Button type="reset">Reset</Button>);
        expect(screen.getByRole("button")).toHaveAttribute("type", "reset");
      });
    });

    describe("When custom className is provided", () => {
      it("Then the custom class should be applied to the button", () => {
        render(<Button className="custom-class">Custom</Button>);
        expect(screen.getByRole("button")).toHaveClass("custom-class");
      });
    });

    describe("When combining variant, size, and custom className", () => {
      it("Then all classes should be merged correctly", () => {
        render(
          <Button variant="outline" size="lg" className="my-custom-class">
            Combined
          </Button>,
        );
        const button = screen.getByRole("button");
        expect(button).toHaveClass("border");
        expect(button).toHaveClass("h-11");
        expect(button).toHaveClass("my-custom-class");
      });
    });
  });
});
