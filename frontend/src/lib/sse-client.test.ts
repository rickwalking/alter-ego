import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { Mock } from "vitest";
import { streamSseEvents } from "./sse-client";
import { createSseResponse } from "./sse-client.test-utils";
import type { SseEvent } from "./sse-client";

// Feature: SSE Client
// Scenario: Parse single token event from stream
describe("streamSseEvents", () => {
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

  // Scenario: Stream yields a single token event
  //   Given a streaming SSE response with a token event
  //   When streamSseEvents is called
  //   Then onEvent is called with the token event
  //   And onComplete is called
  it("dispatches a single token event and calls onComplete", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse([
        'id: 1\ndata: {"type":"token","content":"Hello"}\n\n',
      ]),
    );

    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent,
      onError,
      onComplete,
    });

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith({
      id: "1",
      event: "token",
      data: { type: "token", content: "Hello" },
    });
    expect(onError).not.toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledOnce();
  });

  // Scenario: Stream yields multiple token events
  //   Given a streaming SSE response with multiple token events
  //   When streamSseEvents is called
  //   Then onEvent is called for each token
  it("dispatches multiple token events incrementally", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse([
        'id: 1\ndata: {"type":"token","content":"Hello"}\n\n',
        'id: 2\ndata: {"type":"token","content":" world"}\n\n',
        'id: 3\ndata: {"type":"token","content":"!"}\n\n',
        'id: 4\ndata: {"type":"complete","content":"Hello world!"}\n\n',
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

    expect(events).toHaveLength(4);
    expect(events[0]?.event).toBe("token");
    expect(events[0]?.data.content).toBe("Hello");
    expect(events[1]?.event).toBe("token");
    expect(events[1]?.data.content).toBe(" world");
    expect(events[2]?.event).toBe("token");
    expect(events[2]?.data.content).toBe("!");
    expect(events[3]?.event).toBe("complete");
    expect(onError).not.toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledOnce();
  });

  // Scenario: Chunks arrive split at arbitrary boundaries
  //   Given a streaming response where SSE events span across chunk boundaries
  //   When streamSseEvents is called
  //   Then all events are still parsed correctly
  it("handles chunk boundaries that split SSE events", async () => {
    const mockFetch = vi.mocked(fetch);
    // Split 'id: 1\ndata: {"type":"token","content":"Hello"}\n\n'
    // into two chunks
    mockFetch.mockResolvedValue(
      createSseResponse([
        'id: 1\ndata: {"type":"tok',
        'en","content":"Hello"}\n\nid: 2\ndata: {"type":"complete"}\n\n',
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

    expect(events).toHaveLength(2);
    expect(events[0]?.event).toBe("token");
    expect(events[0]?.data.content).toBe("Hello");
    expect(events[1]?.event).toBe("complete");
    expect(onError).not.toHaveBeenCalled();
  });

  // Scenario: Keep-alive comment lines are ignored
  //   Given a streaming response with keep-alive ping comments
  //   When streamSseEvents is called
  //   Then comment lines are ignored and events are still dispatched
  it("ignores keep-alive comment lines", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse([
        ": ping\n\n",
        'id: 1\ndata: {"type":"token","content":"Hi"}\n\n',
        ": ping\n\n",
        'id: 2\ndata: {"type":"complete"}\n\n',
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

    expect(events).toHaveLength(2);
    expect(events[0]?.event).toBe("token");
    expect(events[1]?.event).toBe("complete");
    expect(onError).not.toHaveBeenCalled();
  });

  // Scenario: HTTP error returns an error
  //   Given a non-200 HTTP response
  //   When streamSseEvents is called
  //   Then onError is called with the HTTP status code (no statusText leakage)
  it("calls onError on HTTP error with sanitized message", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(createSseResponse([], 500));

    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent,
      onError,
      onComplete,
    });

    expect(onError).toHaveBeenCalled();
    expect(onError.mock.calls[0]?.[0]?.message).toBe("HTTP 500");
    expect(onError.mock.calls[0]?.[0]?.message).not.toContain("Error");
    expect(onEvent).not.toHaveBeenCalled();
    expect(onComplete).not.toHaveBeenCalled();
  });

  // Scenario: Wrong content type returns an error
  //   Given a response with incorrect content type
  //   When streamSseEvents is called
  //   Then onError is called with the content type error
  it("calls onError on unexpected content type", async () => {
    const mockFetch = vi.mocked(fetch);
    const response = createSseResponse(['data: {}\n\n']);
    // Override content type
    response.headers.set("content-type", "application/json");
    mockFetch.mockResolvedValue(response);

    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent,
      onError,
      onComplete,
    });

    expect(onError).toHaveBeenCalled();
    expect(onError.mock.calls[0]?.[0]?.message).toContain(
      "Unexpected content type",
    );
    expect(onEvent).not.toHaveBeenCalled();
  });

  // Scenario: Abort signal prevents request
  //   Given an AbortController that is aborted
  //   When streamSseEvents is called with the abort signal
  //   Then no callbacks are called (abort is silent)
  it("silently handles AbortError without calling onError", async () => {
    const abortController = new AbortController();
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockRejectedValue(new DOMException("Aborted", "AbortError"));

    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      signal: abortController.signal,
      onEvent,
      onError,
      onComplete,
    });

    expect(onError).not.toHaveBeenCalled();
    expect(onEvent).not.toHaveBeenCalled();
    expect(onComplete).not.toHaveBeenCalled();
  });

  // Scenario: Network error calls onError
  //   Given a network failure
  //   When streamSseEvents is called
  //   Then onError is called with the error
  it("calls onError on network error", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockRejectedValue(new TypeError("Failed to fetch"));

    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent,
      onError,
      onComplete,
    });

    expect(onError).toHaveBeenCalled();
    expect(onError.mock.calls[0]?.[0]?.message).toContain("Failed to fetch");
    expect(onEvent).not.toHaveBeenCalled();
    expect(onComplete).not.toHaveBeenCalled();
  });

  // Scenario: Error event dispatched via onComplete + onEvent
  //   Given a streaming response with an error event followed by stream end
  //   When streamSseEvents is called
  //   Then onEvent is called with the error event AND onComplete is called
  it("dispatches error event via onEvent and then calls onComplete", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse([
        'id: 1\ndata: {"type":"error","content":"Something went wrong"}\n\n',
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
    expect(events[0]?.event).toBe("error");
    expect(events[0]?.data.content).toBe("Something went wrong");
    // Backend sends error as an event in the stream, not as HTTP error
    expect(onError).not.toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledOnce();
  });

  // Scenario: Last-Event-ID header is sent when provided
  //   Given a lastEventId option
  //   When streamSseEvents is called
  //   Then the Last-Event-ID header is included in the request
  it("includes Last-Event-ID header when provided", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse([
        'id: 2\ndata: {"type":"complete","content":""}\n\n',
      ]),
    );

    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      lastEventId: "1",
      onEvent,
      onError,
      onComplete,
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          "last-event-id": "1",
        }),
      }),
    );
  });

  // Scenario: Response body is null
  //   Given a response with a null body
  //   When streamSseEvents is called
  //   Then onError is called
  it("calls onError when response body is null", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream" }),
      body: null,
    } as unknown as Response);

    await streamSseEvents({
      url: "/api/conversations/abc/chat/stream",
      body: { content: "Hi" },
      onEvent,
      onError,
      onComplete,
    });

    expect(onError).toHaveBeenCalled();
    expect(onError.mock.calls[0]?.[0]?.message).toContain(
      "body is not readable",
    );
  });

  // Scenario: SSE event without trailing blank line
  //   Given a stream that ends without a trailing blank line after the last event
  //   When streamSseEvents is called
  //   Then the last event is still dispatched
  it("dispatches last event even without trailing blank line", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      createSseResponse([
        'id: 1\ndata: {"type":"token","content":"Hello"}\n\nid: 2\ndata: {"type":"complete"}',
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

    expect(events).toHaveLength(2);
    expect(events[0]?.event).toBe("token");
    expect(events[1]?.event).toBe("complete");
    expect(onComplete).toHaveBeenCalledOnce();
  });
});
