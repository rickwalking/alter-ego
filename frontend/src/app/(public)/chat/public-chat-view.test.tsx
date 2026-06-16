import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { PublicChatView } from "@/app/(public)/chat/public-chat-view";

vi.mock("@/modules/conversation", () => ({
  useCreateConversation: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ id: "conv-1" }),
  }),
  useSseChat: () => ({
    messages: [],
    isStreaming: false,
    error: null,
    sendMessage: vi.fn(),
    startNewChat: vi.fn(),
  }),
}));

describe("PublicChatView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Gherkin: Public chat does not list conversation history
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
});
