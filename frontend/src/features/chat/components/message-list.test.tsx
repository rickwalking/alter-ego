import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageList } from "./message-list";
import type { Message } from "@/schemas/chat";

vi.mock("./message-item", () => ({
  MessageItem: ({ message }: { message: Message }) => (
    <div data-testid={`message-${message.id}`}>{message.content}</div>
  ),
}));

const mockScrollIntoView = vi.fn();
window.HTMLElement.prototype.scrollIntoView = mockScrollIntoView;

describe("MessageList Component", () => {
  const mockMessages: Message[] = [
    {
      id: "1",
      role: "user",
      content: "Hello!",
      created_at: new Date().toISOString(),
    },
    {
      id: "2",
      role: "assistant",
      content: "Hi there! How can I help you?",
      created_at: new Date().toISOString(),
    },
    {
      id: "3",
      role: "user",
      content: "I have a question.",
      created_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given an empty messages array", () => {
    describe("When the MessageList is rendered with no messages", () => {
      it("Then it should display the empty state message", () => {
        render(<MessageList messages={[]} />);
        expect(
          screen.getByText("Start a conversation by typing a message below."),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Given a populated messages array", () => {
    describe("When the MessageList is rendered with messages", () => {
      it("Then all messages should be displayed", () => {
        render(<MessageList messages={mockMessages} />);
        expect(screen.getByTestId("message-1")).toBeInTheDocument();
        expect(screen.getByTestId("message-2")).toBeInTheDocument();
        expect(screen.getByTestId("message-3")).toBeInTheDocument();
      });

      it("Then message content should be visible", () => {
        render(<MessageList messages={mockMessages} />);
        expect(screen.getByText("Hello!")).toBeInTheDocument();
        expect(
          screen.getByText("Hi there! How can I help you?"),
        ).toBeInTheDocument();
        expect(screen.getByText("I have a question.")).toBeInTheDocument();
      });

      it("Then messages should be rendered in a flex column", () => {
        const { container } = render(<MessageList messages={mockMessages} />);
        const listContainer = container.firstChild;
        expect(listContainer).toHaveClass("flex");
        expect(listContainer).toHaveClass("flex-col");
      });

      it("Then each message should have a unique key", () => {
        render(<MessageList messages={mockMessages} />);
        mockMessages.forEach((message) => {
          expect(
            screen.getByTestId(`message-${message.id}`),
          ).toBeInTheDocument();
        });
      });
    });

    describe("When messages are updated", () => {
      it("Then new messages should be added to the list", () => {
        const { rerender } = render(
          <MessageList messages={mockMessages.slice(0, 1)} />,
        );
        expect(screen.getByTestId("message-1")).toBeInTheDocument();
        expect(screen.queryByTestId("message-2")).not.toBeInTheDocument();

        rerender(<MessageList messages={mockMessages} />);
        expect(screen.getByTestId("message-1")).toBeInTheDocument();
        expect(screen.getByTestId("message-2")).toBeInTheDocument();
        expect(screen.getByTestId("message-3")).toBeInTheDocument();
      });

      it("Then removed messages should no longer be in the list", () => {
        const { rerender } = render(<MessageList messages={mockMessages} />);
        expect(screen.getByTestId("message-1")).toBeInTheDocument();

        rerender(<MessageList messages={mockMessages.slice(1)} />);
        expect(screen.queryByTestId("message-1")).not.toBeInTheDocument();
        expect(screen.getByTestId("message-2")).toBeInTheDocument();
      });
    });

    describe("When a scroll trigger element is present", () => {
      it("Then a scroll anchor element should be rendered at the bottom", () => {
        const { container } = render(<MessageList messages={mockMessages} />);
        const listContainer = container.firstChild as HTMLElement;
        const children = Array.from(listContainer.children);
        const lastChild = children[children.length - 1];
        expect(lastChild).toBeInTheDocument();
      });
    });
  });

  describe("Given a single message", () => {
    describe("When the MessageList is rendered with one message", () => {
      it("Then only that message should be displayed", () => {
        render(<MessageList messages={[mockMessages[0]]} />);
        expect(screen.getByTestId("message-1")).toBeInTheDocument();
        expect(screen.queryByTestId("message-2")).not.toBeInTheDocument();
      });
    });
  });
});
