import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { Mock } from "vitest";
import { streamSseEvents } from "./sse-client";
import { createSseResponse } from "./sse-client.test-utils";
import type { SseEvent } from "./sse-client";

// Feature: SSE Client — Edge Cases & Mutation Coverage
// These tests cover less common SSE protocol scenarios that would
// otherwise survive as mutants in mutation testing.

describe("streamSseEvents edge cases", () => {
  let onEvent: Mock<(event: SseEvent) => void>;
  let onError: Mock<(error: Error) => void>;
  let onComplete: Mock<() => void>;

  beforeEach(() => {
    onEvent = vi.fn() as Mock<(event: SseEvent) => void>;
    onError = vi.fn() as Mock<(error: Error) => void>;
    onComplete = vi.fn() as Mock<() => void>;
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // Scenario: Event without id: field kills the null-id mutant
  //   Given an SSE event without an id prefix
  //   When streamSseEvents is called
  //   Then the event is dispatched with undefined id
  it("dispatches event even without id field", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse(['data: {"type":"token","content":"NoId"}\n\n']),
    );

    const events: SseEvent[] = [];
    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent: (event) => {
        events.push(event);
      },
      onError,
      onComplete,
    });

    expect(events).toHaveLength(1);
    expect(events[0]?.id).toBeUndefined();
    expect(events[0]?.event).toBe("token");
    expect(events[0]?.data.content).toBe("NoId");
    expect(onComplete).toHaveBeenCalledOnce();
  });

  // Scenario: Non-JSON data falls back to raw field
  //   Given an SSE event with invalid JSON data
  //   When streamSseEvents is called
  //   Then the data contains the raw string
  it("falls back to raw data when JSON parsing fails", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse(["id: 1\ndata: not-valid-json\n\n"]),
    );

    const events: SseEvent[] = [];
    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent: (event) => {
        events.push(event);
      },
      onError,
      onComplete,
    });

    expect(events).toHaveLength(1);
    expect(events[0]?.data.raw).toBe("not-valid-json");
    expect(onComplete).toHaveBeenCalledOnce();
  });

  // Scenario: CRLF \r\n line endings are handled
  //   Given an SSE response with \r\n line endings
  //   When streamSseEvents is called
  //   Then events are still correctly parsed
  it("handles CRLF line endings", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse([
        'id: 1\r\ndata: {"type":"token","content":"CRLF"}\r\n\r\n',
      ]),
    );

    const events: SseEvent[] = [];
    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent: (event) => {
        events.push(event);
      },
      onError,
      onComplete,
    });

    expect(events).toHaveLength(1);
    expect(events[0]?.event).toBe("token");
    expect(events[0]?.data.content).toBe("CRLF");
    expect(onComplete).toHaveBeenCalledOnce();
  });

  // Scenario: Unicode/multi-byte content is handled
  //   Given an SSE response with Unicode text content
  //   When streamSseEvents is called
  //   Then the Unicode text is correctly decoded
  it("handles unicode content correctly", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse([
        'id: 1\ndata: {"type":"token","content":"Olá mundo 🌍"}\n\n',
      ]),
    );

    const events: SseEvent[] = [];
    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent: (event) => {
        events.push(event);
      },
      onError,
      onComplete,
    });

    expect(events).toHaveLength(1);
    expect(events[0]?.data.content).toBe("Olá mundo 🌍");
    expect(onComplete).toHaveBeenCalledOnce();
  });

  // Scenario: Empty response body produces no events
  //   Given a valid SSE response with an empty body
  //   When streamSseEvents is called
  //   Then no events are dispatched
  //   And onComplete is called
  it("handles empty response body gracefully", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(createSseResponse([""]));

    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent,
      onError,
      onComplete,
    });

    expect(onEvent).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledOnce();
  });

  // Scenario: Mid-stream abort after receiving some events
  //   Given an active SSE stream that receives an abort mid-way
  //   When the abort signal is triggered
  //   Then no error callback is called
  it("silently handles mid-stream abort signal", async () => {
    const abortController = new AbortController();
    vi.mocked(fetch).mockImplementationOnce(() => {
      const encoder = new TextEncoder();
      const chunks = [
        encoder.encode('id: 1\ndata: {"type":"token","content":"Hello"}\n\n'),
      ];

      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "text/event-stream" }),
        body: {
          getReader: () => {
            let index = 0;
            let aborted = false;
            const reader = {
              read: async () => {
                if (index < chunks.length) {
                  const value = chunks[index]!;
                  index++;
                  return { done: false, value };
                }
                // Hang until aborted
                await new Promise<void>((resolve) => {
                  const onAbort = () => {
                    aborted = true;
                    resolve();
                  };
                  abortController.signal.addEventListener("abort", onAbort, {
                    once: true,
                  });
                });
                if (aborted) {
                  throw new DOMException(
                    "The operation was aborted",
                    "AbortError",
                  );
                }
                return { done: true, value: undefined };
              },
            };
            return reader;
          },
        } as unknown as ReadableStream<Uint8Array>,
      } as Response);
    });

    const startedPromise = streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      signal: abortController.signal,
      onEvent,
      onError,
      onComplete,
    });

    // Let the first event be read, then abort
    await new Promise((resolve) => setTimeout(resolve, 10));
    abortController.abort();

    await startedPromise;

    expect(onEvent).toHaveBeenCalledOnce();
    expect(onEvent.mock.calls[0]?.[0]?.data.content).toBe("Hello");
    expect(onError).not.toHaveBeenCalled();
    expect(onComplete).not.toHaveBeenCalled();
  });
});
