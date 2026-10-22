/**
 * Shared harness for the useSseChat tests: a controllable fake SSE stream (the
 * test drives each event), a settable history and a real QueryClient. Each
 * test file mocks `@/lib/sse-client` and `use-chat` itself (vi.mock hoisting).
 */
import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { vi } from "vitest";

import { streamSseEvents } from "@/lib/sse-client";
import { useConversationMessages } from "@/modules/conversation/hooks/use-chat";
import type { Message } from "@/schemas/chat";
import { useSseChat } from "./use-sse-chat";

export const mockUseConversationMessages = vi.mocked(useConversationMessages);
const mockStream = vi.mocked(streamSseEvents);

export const CONV_ID = "conv-1";

export type SseEventName =
  | "token"
  | "complete"
  | "error"
  | "sources"
  | "tool_result";

/** A controllable fake stream: captures each call's callbacks for the test to drive. */
export function controllableStream() {
  const calls: {
    opts: Parameters<typeof streamSseEvents>[0];
    resolve: () => void;
  }[] = [];
  mockStream.mockImplementation((opts) => {
    return new Promise<void>((resolve) => {
      calls.push({ opts, resolve });
    });
  });
  return {
    get count() {
      return calls.length;
    },
    last: () => calls[calls.length - 1],
    emit(
      event: SseEventName,
      data: Record<string, unknown>,
      i = calls.length - 1,
    ) {
      act(() => calls[i]!.opts.onEvent({ event, data }));
    },
    complete(i = calls.length - 1) {
      act(() => {
        calls[i]!.opts.onComplete?.();
        calls[i]!.resolve();
      });
    },
    fail(message: string, i = calls.length - 1) {
      act(() => calls[i]!.opts.onError?.(new Error(message)));
    },
  };
}

export function setHistory(messages: Message[]) {
  mockUseConversationMessages.mockReturnValue({
    data: messages,
  } as ReturnType<typeof useConversationMessages>);
}

export function wrapperWithClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const Wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
  return { Wrapper, invalidateSpy };
}

export function renderChat(options: Parameters<typeof useSseChat>[0] = {}) {
  const { Wrapper, invalidateSpy } = wrapperWithClient();
  const view = renderHook(() => useSseChat(options), { wrapper: Wrapper });
  return { ...view, invalidateSpy };
}
