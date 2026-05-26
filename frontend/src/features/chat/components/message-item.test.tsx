import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageItem } from "./message-item";
import type { Message } from "@/schemas/chat";

vi.mock("@/lib/utils", async () => {
  const actual = await vi.importActual("@/lib/utils");
  return {
    ...actual,
    formatRelativeTime: vi.fn(() => "just now"),
    cn: (...inputs: (string | undefined | false | null)[]) =>
      inputs.filter(Boolean).join(" "),
  };
});

describe("MessageItem Component", () => {
  const mockUserMessage: Message = {
    id: "1",
    role: "user",
    content: "Hello, how are you?",
    created_at: new Date().toISOString(),
  };

  const mockAssistantMessage: Message = {
    id: "2",
    role: "assistant",
    content: "I'm doing well, thank you for asking!",
    created_at: new Date().toISOString(),
  };

  const mockStreamingMessage: Message = {
    id: "3",
    role: "assistant",
    content: "Typing response...",
    created_at: new Date().toISOString(),
  };

  describe("Given a user message is rendered", () => {
    describe("When the MessageItem displays a user message", () => {
      it("Then it should show 'You' as the sender", () => {
        render(<MessageItem message={mockUserMessage} />);
        expect(screen.getByText("You")).toBeInTheDocument();
      });

      it("Then it should display the message content", () => {
        render(<MessageItem message={mockUserMessage} />);
        expect(screen.getByText("Hello, how are you?")).toBeInTheDocument();
      });

      it("Then it should have user-specific background styling", () => {
        render(<MessageItem message={mockUserMessage} />);
        const messageContainer = screen
          .getByText("Hello, how are you?")
          .closest("div")?.parentElement?.parentElement;
        expect(messageContainer).toHaveClass("bg-[var(--color-background)]");
      });
    });
  });

  describe("Given an assistant message is rendered", () => {
    describe("When the MessageItem displays an assistant message", () => {
      it("Then it should show 'Assistant' as the sender", () => {
        render(<MessageItem message={mockAssistantMessage} />);
        expect(screen.getByText("Assistant")).toBeInTheDocument();
      });

      it("Then it should display the message content", () => {
        render(<MessageItem message={mockAssistantMessage} />);
        expect(
          screen.getByText("I'm doing well, thank you for asking!"),
        ).toBeInTheDocument();
      });

      it("Then it should have assistant-specific background styling", () => {
        render(<MessageItem message={mockAssistantMessage} />);
        const messageContainer = screen
          .getByText("I'm doing well, thank you for asking!")
          .closest("div")?.parentElement?.parentElement;
        expect(messageContainer).toHaveClass("bg-[var(--color-muted)]");
      });
    });
  });

  describe("Given a streaming message is rendered", () => {
    describe("When the MessageItem displays a streaming message", () => {
      it("Then it should show the streaming message content", () => {
        render(<MessageItem message={mockStreamingMessage} />);
        expect(screen.getByText("Typing response...")).toBeInTheDocument();
      });

      it("Then the streaming message should use the standard message prose styling", () => {
        render(<MessageItem message={mockStreamingMessage} />);
        expect(screen.getByText("Typing response...")).toHaveClass("prose");
      });
    });
  });

  describe("Given a message with timestamp is rendered", () => {
    describe("When the MessageItem displays the timestamp", () => {
      it("Then it should show the relative time", () => {
        render(<MessageItem message={mockUserMessage} />);
        expect(
          screen.getByText(
            new Date(mockUserMessage.created_at).toLocaleTimeString(),
          ),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Given a message with long content", () => {
    describe("When the MessageItem displays the content", () => {
      it("Then it should render the content within prose styling", () => {
        const longMessage: Message = {
          ...mockUserMessage,
          content:
            "This is a longer message with multiple sentences. It should be displayed properly.",
        };
        render(<MessageItem message={longMessage} />);
        const content = screen.getByText(longMessage.content);
        expect(content.closest("div")).toHaveClass("prose");
      });
    });
  });
});
