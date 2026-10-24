/**
 * Gherkin: tests/features/chat-polish.feature
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import type {
  ChatSendResult,
  ConversationTarget,
} from "@/modules/conversation";
import { useChatSend } from "./use-chat-send";

const mocks = vi.hoisted(() => ({
  sendMessage:
    vi.fn<
      (
        content: string,
        target?: ConversationTarget | null,
      ) => Promise<ChatSendResult>
    >(),
}));

vi.mock("@/modules/conversation", () => ({
  CHAT_SEND_RESULT: { SENT: "sent", FAILED: "failed", IGNORED: "ignored" },
  useCreateConversation: () => ({ mutateAsync: vi.fn() }),
}));

function renderSend(state: { isStreaming: boolean; busy: boolean }) {
  return renderHook(() =>
    useChatSend({
      conversationId: "conv-1",
      isStreaming: state.isStreaming,
      sendMessage: mocks.sendMessage,
      isBusy: () => state.busy,
      onConversationCreated: vi.fn(),
    }),
  );
}

beforeEach(() => {
  mocks.sendMessage.mockReset();
  mocks.sendMessage.mockResolvedValue("sent");
});

describe("useChatSend suggestions", () => {
  /** Scenario: An empty chat introduces the Alter-Ego and suggests questions */
  it("sends a picked suggestion and leaves the typed text alone", async () => {
    const { result } = renderSend({ isStreaming: false, busy: false });
    act(() => result.current.setInput("draft"));

    await act(() => result.current.sendNow("What do you work on these days?"));

    expect(mocks.sendMessage.mock.calls[0]![0]).toBe(
      "What do you work on these days?",
    );
    expect(result.current.input).toBe("draft");
  });

  /** Scenario: A suggestion picked while a reply is on its way is not sent */
  it.each([
    { isStreaming: true, busy: false },
    { isStreaming: false, busy: true },
  ])("ignores a suggestion while a turn is in flight (%o)", async (state) => {
    const { result } = renderSend(state);

    await act(() => result.current.sendNow("How do you build with LLMs?"));

    expect(mocks.sendMessage).not.toHaveBeenCalled();
  });
});
