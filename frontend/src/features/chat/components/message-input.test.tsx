import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageInput } from "./message-input";

describe("MessageInput Component", () => {
  const mockOnSend = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the MessageInput component is rendered", () => {
    describe("When the component is displayed", () => {
      it("Then the textarea should be visible with default placeholder", () => {
        render(<MessageInput onSend={mockOnSend} />);
        expect(screen.getByPlaceholderText("Type your message...")).toBeInTheDocument();
      });

      it("Then the send button should be visible", () => {
        render(<MessageInput onSend={mockOnSend} />);
        expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument();
      });
    });
  });

  describe("Given the user types in the textarea", () => {
    describe("When text is entered", () => {
      it("Then the textarea value should update", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "Hello world");

        expect(textarea).toHaveValue("Hello world");
      });
    });

    describe("When the send button is clicked with text", () => {
      it("Then onSend should be called with the message", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "Test message");
        await user.click(screen.getByRole("button", { name: /send message/i }));

        expect(mockOnSend).toHaveBeenCalledWith("Test message");
      });

      it("Then the textarea should be cleared after sending", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "Test message");
        await user.click(screen.getByRole("button", { name: /send message/i }));

        expect(textarea).toHaveValue("");
      });
    });

    describe("When Enter key is pressed without Shift", () => {
      it("Then onSend should be called with the message", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "Test message");
        await user.keyboard("{Enter}");

        expect(mockOnSend).toHaveBeenCalledWith("Test message");
      });
    });

    describe("When Shift+Enter is pressed", () => {
      it("Then onSend should not be called", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "Test message");
        await user.keyboard("{Shift>}{Enter}{/Shift}");

        expect(mockOnSend).not.toHaveBeenCalled();
      });
    });
  });

  describe("Given the send button state", () => {
    describe("When the textarea is empty", () => {
      it("Then the send button should be disabled", () => {
        render(<MessageInput onSend={mockOnSend} />);
        expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
      });
    });

    describe("When the textarea contains only whitespace", () => {
      it("Then the send button should be disabled", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "   ");

        expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
      });

      it("Then clicking the button should not call onSend", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "   ");
        await user.click(screen.getByRole("button", { name: /send message/i }));

        expect(mockOnSend).not.toHaveBeenCalled();
      });
    });

    describe("When the textarea has content with leading/trailing whitespace", () => {
      it("Then the message should be trimmed before sending", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "  Test message  ");
        await user.click(screen.getByRole("button", { name: /send message/i }));

        expect(mockOnSend).toHaveBeenCalledWith("Test message");
      });
    });
  });

  describe("Given the isLoading prop is true", () => {
    describe("When the component is in loading state", () => {
      it("Then the textarea should be disabled", () => {
        render(<MessageInput onSend={mockOnSend} isLoading />);
        expect(screen.getByPlaceholderText("Type your message...")).toBeDisabled();
      });

      it("Then the send button should be disabled", () => {
        render(<MessageInput onSend={mockOnSend} isLoading />);
        expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
      });

      it("Then the textarea should have reduced opacity", () => {
        render(<MessageInput onSend={mockOnSend} isLoading />);
        expect(screen.getByPlaceholderText("Type your message...")).toHaveClass("opacity-50");
      });
    });
  });

  describe("Given the form submission", () => {
    describe("When the form is submitted", () => {
      it("Then the default form submission should be prevented", async () => {
        const user = userEvent.setup();
        render(<MessageInput onSend={mockOnSend} />);

        const textarea = screen.getByPlaceholderText("Type your message...");
        await user.type(textarea, "Test");
        
        await user.keyboard("{Enter}");
        
        expect(mockOnSend).toHaveBeenCalled();
      });
    });
  });
});
