import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInterface } from "./chat-interface";

vi.mock("./message-list", () => ({
  MessageList: ({ messages }: { messages: Array<{ id: string; content: string }> }) => (
    <div data-testid="message-list">
      {messages.length === 0 ? (
        <p>Start a conversation by typing a message below.</p>
      ) : (
        messages.map((msg) => (
          <div key={msg.id} data-testid={`message-${msg.id}`}>
            {msg.content}
          </div>
        ))
      )}
    </div>
  ),
}));

vi.mock("./message-input", () => ({
  MessageInput: ({
    onSend,
    isLoading,
  }: {
    onSend: (message: string) => void;
    isLoading?: boolean;
  }) => (
    <div data-testid="message-input">
      <input
        type="text"
        data-testid="message-text-input"
        disabled={isLoading}
      />
      <button
        data-testid="send-button"
        disabled={isLoading}
        onClick={() => {
          const input = document.querySelector(
            '[data-testid="message-text-input"]'
          ) as HTMLInputElement;
          if (input?.value) {
            onSend(input.value);
            input.value = "";
          }
        }}
      >
        Send
      </button>
    </div>
  ),
}));

vi.mock("./conversation-sidebar", () => ({
  ConversationSidebar: ({
    conversations,
    activeId,
    onNewChat,
  }: {
    conversations: unknown[];
    activeId?: string | null;
    onNewChat: () => void;
  }) => (
    <div data-testid="conversation-sidebar">
      <button data-testid="new-chat-button" onClick={onNewChat}>
        New Chat
      </button>
      <div data-testid="conversations-count">{conversations.length}</div>
      <div data-testid="active-id">{activeId ?? ""}</div>
    </div>
  ),
}));

vi.mock("@/lib/utils", async () => ({
  generateId: vi.fn(() => "new-id-123"),
  formatDate: vi.fn(() => "Jan 1, 2024"),
  cn: (...inputs: (string | undefined | false | null)[]) =>
    inputs.filter(Boolean).join(" "),
  truncate: vi.fn((str: string, len: number) =>
    str.length > len ? str.slice(0, len - 3) + "..." : str
  ),
  debounce: vi.fn((fn: () => void) => fn),
  throttle: vi.fn((fn: () => void) => fn),
}));

describe("ChatInterface Component", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Given the ChatInterface is rendered", () => {
    describe("When the component is displayed", () => {
      it("Then the conversation sidebar should be visible", () => {
        render(<ChatInterface />);
        expect(screen.getByTestId("conversation-sidebar")).toBeInTheDocument();
      });

      it("Then the message list should be visible", () => {
        render(<ChatInterface />);
        expect(screen.getByTestId("message-list")).toBeInTheDocument();
      });

      it("Then the message input should be visible", () => {
        render(<ChatInterface />);
        expect(screen.getByTestId("message-input")).toBeInTheDocument();
      });

      it("Then initial conversations should be loaded", () => {
        render(<ChatInterface />);
        expect(screen.getByTestId("conversations-count")).toHaveTextContent("1");
      });
    });

    describe("When the New Chat button is clicked", () => {
      it("Then a new conversation should be created", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        await user.click(screen.getByTestId("new-chat-button"));
        expect(screen.getByTestId("conversations-count")).toHaveTextContent("2");
      });

      it("Then the new conversation should become active", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        const initialActiveId = screen.getByTestId("active-id").textContent;
        await user.click(screen.getByTestId("new-chat-button"));
        const newActiveId = screen.getByTestId("active-id").textContent;
        
        expect(newActiveId).not.toBe(initialActiveId);
        expect(newActiveId).toBe("new-id-123");
      });
    });

    describe("When a message is sent", () => {
      it("Then the message should appear in the list", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        const input = screen.getByTestId("message-text-input");
        await user.type(input, "Hello!");
        await user.click(screen.getByTestId("send-button"));

        expect(screen.getByText("Hello!")).toBeInTheDocument();
      });

      it("Then the input should be cleared after sending", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        const input = screen.getByTestId("message-text-input");
        await user.type(input, "Hello!");
        await user.click(screen.getByTestId("send-button"));

        expect(input).toHaveValue("");
      });
    });

    describe("When the component is loading", () => {
      it("Then the message input should be disabled during response", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        const input = screen.getByTestId("message-text-input");
        const sendButton = screen.getByTestId("send-button");

        await user.type(input, "Hello!");
        await user.click(sendButton);

        expect(input).toBeDisabled();
        expect(sendButton).toBeDisabled();
      });
    });

    describe("When the sidebar layout is rendered", () => {
      it("Then it should have flex layout", () => {
        const { container } = render(<ChatInterface />);
        expect(container.firstChild).toHaveClass("flex");
      });

      it("Then the main content area should be present", () => {
        const { container } = render(<ChatInterface />);
        const mainContent = container.querySelector(".flex-1");
        expect(mainContent).toBeInTheDocument();
      });
    });
  });
});
