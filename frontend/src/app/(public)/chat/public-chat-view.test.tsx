import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PublicChatView } from "@/app/(public)/chat/public-chat-view";

type SendTarget =
  | string
  | ((signal: AbortSignal) => Promise<string>)
  | null
  | undefined;

const mocks = vi.hoisted(() => ({
  sendMessage:
    vi.fn<(content: string, target: SendTarget) => Promise<string>>(),
  createConversation: vi.fn<() => Promise<{ id: string }>>(),
}));

vi.mock("@/modules/conversation", () => ({
  CHAT_SEND_RESULT: { SENT: "sent", FAILED: "failed", IGNORED: "ignored" },
  useCreateConversation: () => ({ mutateAsync: mocks.createConversation }),
  useSseChat: () => ({
    messages: [],
    isStreaming: false,
    error: null,
    sendMessage: mocks.sendMessage,
    startNewChat: vi.fn(),
  }),
}));

function composer(): HTMLTextAreaElement {
  return screen.getByPlaceholderText(/ask the alter-ego/i);
}

function typeAndSend(text: string): void {
  fireEvent.change(composer(), { target: { value: text } });
  fireEvent.keyDown(composer(), { key: "Enter" });
}

describe("PublicChatView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.createConversation.mockResolvedValue({ id: "conv-1" });
    mocks.sendMessage.mockResolvedValue("sent");
  });

  // Scenario: Public chat does not list conversation history
  it("does not render conversation history sidebar", () => {
    render(<PublicChatView />);
    expect(
      screen.queryByRole("complementary", { name: /conversations/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/search conversations/i),
    ).not.toBeInTheDocument();
  });

  it("shows sign-in hint for ephemeral sessions", () => {
    render(<PublicChatView />);
    expect(screen.getByText(/not saved after refresh/i)).toBeInTheDocument();
  });

  // Scenario: The message shows as pending while the conversation is created
  it("hands the hook a creator instead of waiting for the conversation", async () => {
    render(<PublicChatView />);
    typeAndSend("hello");

    await waitFor(() => expect(mocks.sendMessage).toHaveBeenCalledOnce());
    const [content, target] = mocks.sendMessage.mock.calls[0]!;
    expect(content).toBe("hello");
    expect(mocks.createConversation).not.toHaveBeenCalled();
    expect(typeof target).toBe("function");
    if (typeof target !== "function") return;
    await expect(target(new AbortController().signal)).resolves.toBe("conv-1");
    expect(mocks.createConversation).toHaveBeenCalledOnce();
  });

  // Scenario: A failed send keeps the bubble and gives the text back
  it("gives the typed text back when the send fails", async () => {
    mocks.sendMessage.mockResolvedValue("failed");
    render(<PublicChatView />);
    typeAndSend("offline message");

    await waitFor(() => expect(composer().value).toBe("offline message"));
  });

  it("clears the composer once the message is sent", async () => {
    render(<PublicChatView />);
    typeAndSend("hello");

    await waitFor(() => expect(mocks.sendMessage).toHaveBeenCalled());
    expect(composer().value).toBe("");
  });
});
