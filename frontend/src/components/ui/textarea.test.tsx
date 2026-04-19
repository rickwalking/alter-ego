import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Textarea } from "./textarea";

describe("Textarea Component", () => {
  describe("Given the Textarea component is rendered", () => {
    describe("When the Textarea has a placeholder", () => {
      it("Then the placeholder text should be displayed", () => {
        render(<Textarea placeholder="Enter text" />);
        expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
      });
    });

    describe("When the user types into the Textarea", () => {
      it("Then the onChange handler should be called", async () => {
        const user = userEvent.setup();
        const handleChange = vi.fn();

        render(<Textarea onChange={handleChange} data-testid="textarea" />);
        const textarea = screen.getByTestId("textarea");

        await user.type(textarea, "hello world");
        expect(handleChange).toHaveBeenCalled();
      });
    });

    describe("When the Textarea has disabled prop set to true", () => {
      it("Then the Textarea should be disabled", () => {
        render(<Textarea disabled data-testid="textarea" />);
        expect(screen.getByTestId("textarea")).toBeDisabled();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Textarea", () => {
        render(<Textarea className="custom-class" data-testid="textarea" />);
        expect(screen.getByTestId("textarea")).toHaveClass("custom-class");
      });
    });

    describe("When a ref is forwarded to the Textarea", () => {
      it("Then the ref should reference the textarea element", () => {
        const ref = { current: null as HTMLTextAreaElement | null };
        render(<Textarea ref={ref} />);
        expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
      });
    });

    describe("When accessibility attributes are provided", () => {
      it("Then the Textarea should be accessible by label", () => {
        render(<Textarea aria-label="Description" />);
        expect(screen.getByLabelText("Description")).toBeInTheDocument();
      });
    });

    describe("When the Textarea has custom rows", () => {
      it("Then the Textarea should have the specified rows", () => {
        render(<Textarea rows={5} data-testid="textarea" />);
        expect(screen.getByTestId("textarea")).toHaveAttribute("rows", "5");
      });
    });

    describe("When the Textarea has minHeight styling", () => {
      it("Then it should have the min-height class from the component", () => {
        render(<Textarea data-testid="textarea" />);
        expect(screen.getByTestId("textarea")).toHaveClass("min-h-[80px]");
      });
    });

    describe("When the Textarea is read-only", () => {
      it("Then the Textarea should have the readOnly attribute", () => {
        render(<Textarea readOnly data-testid="textarea" />);
        expect(screen.getByTestId("textarea")).toHaveAttribute("readonly");
      });
    });

    describe("When the Textarea has a value", () => {
      it("Then the Textarea should display the provided value", () => {
        render(<Textarea value="test value" readOnly data-testid="textarea" />);
        expect(screen.getByDisplayValue("test value")).toBeInTheDocument();
      });
    });

    describe("When the Textarea has defaultValue", () => {
      it("Then the Textarea should display the default value", () => {
        render(<Textarea defaultValue="default value" data-testid="textarea" />);
        expect(screen.getByDisplayValue("default value")).toBeInTheDocument();
      });
    });

    describe("When the Textarea has name and id props", () => {
      it("Then the Textarea should have the correct name and id attributes", () => {
        render(<Textarea name="description" id="desc-id" data-testid="textarea" />);
        const textarea = screen.getByTestId("textarea");
        expect(textarea).toHaveAttribute("name", "description");
        expect(textarea).toHaveAttribute("id", "desc-id");
      });
    });

    describe("When the Textarea has required prop", () => {
      it("Then the Textarea should have the required attribute", () => {
        render(<Textarea required data-testid="textarea" />);
        expect(screen.getByTestId("textarea")).toBeRequired();
      });
    });

    describe("When the Textarea handles multi-line input", () => {
      it("Then it should support newlines in the content", async () => {
        const user = userEvent.setup();
        render(<Textarea data-testid="textarea" />);
        const textarea = screen.getByTestId("textarea");

        await user.type(textarea, "Line 1{Enter}Line 2{Enter}Line 3");
        expect(textarea).toHaveValue("Line 1\nLine 2\nLine 3");
      });
    });
  });
});
