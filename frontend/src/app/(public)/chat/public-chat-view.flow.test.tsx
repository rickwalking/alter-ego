/**
 * Gherkin: tests/features/chat-errors-ui.feature
 *
 * The public chat end to end with the real hooks: only the network seams (the
 * SSE client and conversation creation) are faked, so the error banner comes
 * from a real failed turn.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { SseHttpError } from "@/lib/sse-http-error";
import { PublicChatView } from "./public-chat-view";

interface StreamOptions {
  body: { content: string };
  onOpen?: () => void;
  onEvent: (event: { event: string; data: Record<string, unknown> }) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

const mocks = vi.hoisted(() => ({
  stream: vi.fn<(options: StreamOptions) => Promise<void>>(),
  create: vi.fn<
    () => Promise<{
      id: string;
      title: null;
      metadata: object;
      created_at: string;
      updated_at: string;
    }>
  >(),
}));

vi.mock("@/lib/sse-client", () => ({
  streamSseEvents: mocks.stream,
  SSE_EVENT_TYPE: {
    TOKEN: "token",
    COMPLETE: "complete",
    ERROR: "error",
    SOURCES: "sources",
    TOOL_RESULT: "tool_result",
  },
}));

vi.mock("@/modules/conversation/queries", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/conversation/queries")>()),
  createConversation: mocks.create,
}));

function failsBeforeTheResponse(options: StreamOptions): Promise<void> {
  options.onError?.(new SseHttpError(503));
  return Promise.resolve();
}

function failsMidStream(options: StreamOptions): Promise<void> {
  options.onOpen?.();
  options.onEvent({ event: "token", data: { content: "Half" } });
  options.onError?.(new TypeError("network error"));
  return Promise.resolve();
}

function answers(options: StreamOptions): Promise<void> {
  options.onOpen?.();
  options.onEvent({ event: "token", data: { content: "ok" } });
  options.onComplete?.();
  return Promise.resolve();
}

function renderChat() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <PublicChatView />
    </QueryClientProvider>,
  );
  return screen.getByRole("textbox");
}

async function send(textbox: HTMLElement, text: string): Promise<void> {
  fireEvent.change(textbox, { target: { value: text } });
  await act(async () => {
    fireEvent.keyDown(textbox, { key: "Enter" });
    await Promise.resolve();
  });
}

describe("PublicChatView failures", () => {
  beforeEach(() => {
    mocks.stream.mockReset();
    mocks.create.mockReset();
    mocks.create.mockResolvedValue({
      id: "conv-1",
      title: null,
      metadata: {},
      created_at: "2026-10-22T12:00:00Z",
      updated_at: "2026-10-22T12:00:00Z",
    });
  });

  /** Scenario: Retry is offered only when nothing was saved yet */
  it("retries a send that failed before the server answered", async () => {
    mocks.stream.mockImplementationOnce(failsBeforeTheResponse);
    mocks.stream.mockImplementationOnce(answers);
    const textbox = renderChat();

    await send(textbox, "hello");
    const retry = await screen.findByRole("button", { name: "Try again" });
    expect(screen.getByRole("alert")).toHaveTextContent(
      /something went wrong/i,
    );
    expect(textbox).toHaveValue("hello");

    await act(async () => {
      fireEvent.click(retry);
      await Promise.resolve();
    });

    await waitFor(() => expect(mocks.stream).toHaveBeenCalledTimes(2));
    expect(mocks.stream.mock.calls[1]![0].body.content).toBe("hello");
    expect(textbox).toHaveValue("");
    expect(await screen.findByText("ok")).toBeInTheDocument();
  });

  /** Scenario: Retry is offered only when nothing was saved yet */
  it("offers only a new chat once the answer had started", async () => {
    mocks.stream.mockImplementationOnce(failsMidStream);
    const textbox = renderChat();

    await send(textbox, "tell me more");

    expect(
      await screen.findByRole("button", { name: "Start a new chat" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Try again" }),
    ).not.toBeInTheDocument();
  });

  /** Scenario: A full conversation offers a new chat instead of a retry */
  it("offers a new chat when the conversation is full", async () => {
    mocks.stream.mockImplementationOnce((options) => {
      options.onError?.(new SseHttpError(429));
      return Promise.resolve();
    });
    const textbox = renderChat();

    await send(textbox, "one more");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /too many messages|chat is full/i,
    );
    expect(
      screen.queryByRole("button", { name: "Try again" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start a new chat" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  /** Scenario: A double click sends the message once */
  it("sends once and keeps the composer empty on a double click", async () => {
    mocks.stream.mockImplementation(answers);
    const textbox = renderChat();
    fireEvent.change(textbox, { target: { value: "2+2?" } });
    const sendButton = screen.getByRole("button", { name: "Send message" });

    await act(async () => {
      fireEvent.click(sendButton);
      fireEvent.click(sendButton);
      await Promise.resolve();
    });

    await waitFor(() => expect(mocks.stream).toHaveBeenCalledOnce());
    expect(mocks.create).toHaveBeenCalledOnce();
    expect(textbox).toHaveValue("");
  });
});
