import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Input } from "./input";

describe("Input Component", () => {
  describe("Given the Input component is rendered", () => {
    describe("When the Input has a placeholder", () => {
      it("Then the placeholder text should be displayed", () => {
        render(<Input placeholder="Enter text" />);
        expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
      });
    });

    describe("When the user types into the Input", () => {
      it("Then the onChange handler should be called", async () => {
        const user = userEvent.setup();
        const handleChange = vi.fn();

        render(<Input onChange={handleChange} />);
        const input = screen.getByRole("textbox");

        await user.type(input, "hello");
        expect(handleChange).toHaveBeenCalled();
      });
    });

    describe("When the Input has disabled prop set to true", () => {
      it("Then the Input should be disabled", () => {
        render(<Input disabled />);
        expect(screen.getByRole("textbox")).toBeDisabled();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Input", () => {
        render(<Input className="custom-class" data-testid="input" />);
        expect(screen.getByTestId("input")).toHaveClass("custom-class");
      });
    });

    describe("When a ref is forwarded to the Input", () => {
      it("Then the ref should reference the input element", () => {
        const ref = { current: null as HTMLInputElement | null };
        render(<Input ref={ref} />);
        expect(ref.current).toBeInstanceOf(HTMLInputElement);
      });
    });

    describe("When different type props are provided", () => {
      it("Then the Input should have the correct type attribute", () => {
        const { rerender } = render(<Input type="text" data-testid="input" />);
        expect(screen.getByTestId("input")).toHaveAttribute("type", "text");

        rerender(<Input type="email" data-testid="input" />);
        expect(screen.getByTestId("input")).toHaveAttribute("type", "email");

        rerender(<Input type="password" data-testid="input" />);
        expect(screen.getByTestId("input")).toHaveAttribute("type", "password");

        rerender(<Input type="number" data-testid="input" />);
        expect(screen.getByTestId("input")).toHaveAttribute("type", "number");

        rerender(<Input type="search" data-testid="input" />);
        expect(screen.getByTestId("input")).toHaveAttribute("type", "search");
      });
    });

    describe("When accessibility attributes are provided", () => {
      it("Then the Input should be accessible by label", () => {
        render(<Input aria-label="Username" />);
        expect(screen.getByLabelText("Username")).toBeInTheDocument();
      });

      it("Then the Input should be accessible by aria-labelledby", () => {
        render(
          <>
            <label id="email-label">Email</label>
            <Input aria-labelledby="email-label" />
          </>
        );
        expect(screen.getByLabelText("Email")).toBeInTheDocument();
      });
    });

    describe("When the Input has a value prop", () => {
      it("Then the Input should display the provided value", () => {
        render(<Input value="test value" readOnly />);
        expect(screen.getByDisplayValue("test value")).toBeInTheDocument();
      });
    });

    describe("When the Input has defaultValue prop", () => {
      it("Then the Input should display the default value", () => {
        render(<Input defaultValue="default value" />);
        expect(screen.getByDisplayValue("default value")).toBeInTheDocument();
      });
    });

    describe("When the Input has name and id props", () => {
      it("Then the Input should have the correct name and id attributes", () => {
        render(<Input name="username" id="user-id" data-testid="input" />);
        const input = screen.getByTestId("input");
        expect(input).toHaveAttribute("name", "username");
        expect(input).toHaveAttribute("id", "user-id");
      });
    });

    describe("When the Input has required prop", () => {
      it("Then the Input should have the required attribute", () => {
        render(<Input required data-testid="input" />);
        expect(screen.getByTestId("input")).toBeRequired();
      });
    });
  });
});
