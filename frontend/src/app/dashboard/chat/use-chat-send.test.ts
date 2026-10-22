/**
 * Gherkin: tests/features/chat-stream-state.feature
 */
import { describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import type {
  ChatSendResult,
  ConversationTarget,
} from "@/modules/conversation";
import { useChatSend } from "./use-chat-send";

type Creator = (signal: AbortSignal) => Promise<string>;

const mocks = vi.hoisted(() => ({
  create: vi.fn<() => Promise<{ id: string }>>(),
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
  useCreateConversation: () => ({ mutateAsync: mocks.create }),
}));

/** Send "hello" with no open conversation and return the creator handed over. */
async function sendAndCaptureCreator(onCreated: (id: string) => void) {
  mocks.create.mockResolvedValue({ id: "conv-9" });
  mocks.sendMessage.mockResolvedValue("sent");
  const { result } = renderHook(() =>
    useChatSend({
      conversationId: null,
      isStreaming: false,
      sendMessage: mocks.sendMessage,
      isBusy: () => false,
      onConversationCreated: onCreated,
    }),
  );
  act(() => result.current.setInput("hello"));
  await act(() => result.current.handleSend());
  const target = mocks.sendMessage.mock.calls[0]![1];
  if (typeof target !== "function") throw new Error("expected a creator");
  return target satisfies Creator;
}

describe("useChatSend conversation creation", () => {
  // Scenario: The message shows as pending while the conversation is created
  it("opens the conversation it created for a live turn", async () => {
    const onCreated = vi.fn();
    const creator = await sendAndCaptureCreator(onCreated);

    await expect(creator(new AbortController().signal)).resolves.toBe("conv-9");
    expect(onCreated).toHaveBeenCalledWith("conv-9");
  });

  // Scenario: A double send while the conversation is being created sends one message
  it("does not open a conversation whose turn New chat abandoned", async () => {
    const onCreated = vi.fn();
    const creator = await sendAndCaptureCreator(onCreated);
    const abandoned = new AbortController();
    abandoned.abort();

    await creator(abandoned.signal);
    expect(onCreated).not.toHaveBeenCalled();
  });

  // Scenario: A double send while the conversation is being created sends one message
  it("keeps the typed text when a turn is still in flight", async () => {
    mocks.sendMessage.mockClear();
    const { result } = renderHook(() =>
      useChatSend({
        conversationId: "conv-1",
        isStreaming: false,
        sendMessage: mocks.sendMessage,
        isBusy: () => true,
        onConversationCreated: vi.fn(),
      }),
    );
    act(() => result.current.setInput("do not lose me"));
    await act(() => result.current.handleSend());

    expect(mocks.sendMessage).not.toHaveBeenCalled();
    expect(result.current.input).toBe("do not lose me");
  });
});
