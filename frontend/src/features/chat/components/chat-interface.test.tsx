import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test/utils";
import { ChatInterface } from "./chat-interface";

const chatMocks = vi.hoisted(() => ({
  conversations: [
    {
      id: "conv-1",
      title: "Existing conversation",
      created_at: "2026-04-20T00:00:00Z",
      updated_at: "2026-04-20T00:00:00Z",
    },
  ],
  messages: [] as Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    created_at: string;
    sources: never[];
  }>,
  loadingConversations: false,
  loadingMessages: false,
  sendPending: false,
  createConversation: vi.fn(),
  sendMessage: vi.fn(),
}));

vi.mock("../hooks/use-chat", () => ({
  useConversations: () => ({
    data: chatMocks.conversations,
    isLoading: chatMocks.loadingConversations,
  }),
  useConversationMessages: () => ({
    data: chatMocks.messages,
    isLoading: chatMocks.loadingMessages,
  }),
  useCreateConversation: () => ({
    mutateAsync: chatMocks.createConversation,
  }),
  useSendMessage: () => ({
    isPending: chatMocks.sendPending,
    mutateAsync: chatMocks.sendMessage,
  }),
}));

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
    chatMocks.conversations = [
      {
        id: "conv-1",
        title: "Existing conversation",
        created_at: "2026-04-20T00:00:00Z",
        updated_at: "2026-04-20T00:00:00Z",
      },
    ];
    chatMocks.messages = [];
    chatMocks.loadingConversations = false;
    chatMocks.loadingMessages = false;
    chatMocks.sendPending = false;
    chatMocks.createConversation.mockReset();
    chatMocks.createConversation.mockResolvedValue({ id: "new-id-123" });
    chatMocks.sendMessage.mockReset();
    chatMocks.sendMessage.mockResolvedValue({
      content: "Assistant response",
      sources: [],
    });
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
      it("Then a new conversation should not be created until a message is sent", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        await user.click(screen.getByTestId("new-chat-button"));
        expect(chatMocks.createConversation).not.toHaveBeenCalled();
        expect(screen.getByTestId("conversations-count")).toHaveTextContent("1");
      });

      it("Then no existing conversation remains selected while composing", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        await user.click(screen.getByTestId("new-chat-button"));
        expect(screen.getByTestId("active-id")).toHaveTextContent("");
      });

      it("Then the new conversation is created when the first message is sent", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        await user.click(screen.getByTestId("new-chat-button"));
        const input = screen.getByTestId("message-text-input");
        await user.type(input, "Start fresh");
        await user.click(screen.getByTestId("send-button"));

        expect(await screen.findByText("Start fresh")).toBeInTheDocument();
        expect(chatMocks.createConversation).toHaveBeenCalledWith({});
        expect(chatMocks.sendMessage).toHaveBeenCalledWith({
          conversationId: "new-id-123",
          content: "Start fresh",
        });
        expect(screen.getByTestId("active-id")).toHaveTextContent("new-id-123");
      });
    });

    describe("When a message is sent", () => {
      it("Then the message should appear in the list", async () => {
        const user = userEvent.setup();
        render(<ChatInterface />);

        const input = screen.getByTestId("message-text-input");
        await user.type(input, "Hello!");
        await user.click(screen.getByTestId("send-button"));

        expect(await screen.findByText("Hello!")).toBeInTheDocument();
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
      it("Then the message input should be disabled during response", () => {
        chatMocks.sendPending = true;
        render(<ChatInterface />);

        const input = screen.getByTestId("message-text-input");
        const sendButton = screen.getByTestId("send-button");

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
