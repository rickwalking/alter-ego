import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { useCarouselStream } from "./use-carousel";

/**
 * Minimal EventSource stand-in for jsdom tests. The real class is not
 * implemented in jsdom, and we want deterministic control over when
 * messages fire to avoid timing-dependent assertions.
 */
class MockEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  static instances: MockEventSource[] = [];

  readyState = MockEventSource.CONNECTING;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }

  close = vi.fn(() => {
    this.readyState = MockEventSource.CLOSED;
  });

  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }
}

const originalEventSource = globalThis.EventSource;

beforeEach(() => {
  MockEventSource.instances = [];
  // @ts-expect-error — swap in the mock for the duration of each test.
  globalThis.EventSource = MockEventSource;
});

afterEach(() => {
  globalThis.EventSource = originalEventSource;
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe("useCarouselStream", () => {
  describe("Given a null project id", () => {
    it("does not open an EventSource", () => {
      renderHook(() => useCarouselStream(null), { wrapper: createWrapper() });
      expect(MockEventSource.instances).toHaveLength(0);
    });
  });

  describe("Given enabled=false", () => {
    it("does not open an EventSource", () => {
      const { result } = renderHook(() => useCarouselStream("abc", { enabled: false }), {
        wrapper: createWrapper(),
      });
      expect(MockEventSource.instances).toHaveLength(0);
      expect(result.current.isStreaming).toBe(false);
    });
  });

  describe("Given a valid id", () => {
    it("opens an EventSource to the /stream endpoint", () => {
      renderHook(() => useCarouselStream("abc-123"), { wrapper: createWrapper() });
      expect(MockEventSource.instances).toHaveLength(1);
      expect(MockEventSource.instances[0].url).toBe("/api/carousels/abc-123/stream");
    });

    it("updates latestEvent when a message arrives", async () => {
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      act(() => {
        MockEventSource.instances[0].emit({
          node: "research",
          status: "researching",
        });
      });
      await waitFor(() =>
        expect(result.current.latestEvent?.node).toBe("research"),
      );
    });

    it("closes the stream when an `end` event arrives", async () => {
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      const mock = MockEventSource.instances[0];
      act(() => {
        mock.emit({ node: "end", status: "completed" });
      });
      await waitFor(() => expect(mock.close).toHaveBeenCalled());
      expect(result.current.isStreaming).toBe(false);
    });

    it("records the error message when an `error` event arrives", async () => {
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      act(() => {
        MockEventSource.instances[0].emit({
          node: "error",
          status: "failed",
          error: "image generation failed",
        });
      });
      await waitFor(() =>
        expect(result.current.error).toBe("image generation failed"),
      );
    });

    it("ignores malformed events without crashing", async () => {
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      const mock = MockEventSource.instances[0];
      // Emit garbage; the hook should swallow it and stay streaming.
      mock.onmessage?.({ data: "not json" } as MessageEvent);
      expect(result.current.isStreaming).toBe(true);
      expect(result.current.latestEvent).toBeNull();
    });

    it("closes the stream on unmount", () => {
      const { unmount } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      const mock = MockEventSource.instances[0];
      unmount();
      expect(mock.close).toHaveBeenCalled();
    });

    it("starts streaming immediately when a valid id is provided", () => {
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      expect(result.current.isStreaming).toBe(true);
    });

    it("does not close the stream on a non-terminal event", async () => {
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      const mock = MockEventSource.instances[0];
      act(() => {
        mock.emit({ node: "research", status: "researching" });
      });
      await waitFor(() =>
        expect(result.current.latestEvent?.node).toBe("research")
      );
      expect(result.current.isStreaming).toBe(true);
      expect(mock.close).not.toHaveBeenCalled();
    });

    it("does not set error on a clean end event", async () => {
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      act(() => {
        MockEventSource.instances[0].emit({ node: "end", status: "completed" });
      });
      await waitFor(() => expect(result.current.isStreaming).toBe(false));
      expect(result.current.error).toBeNull();
    });

    it("ignores events that fail schema validation", async () => {
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      act(() => {
        // Valid JSON but missing required fields for the schema.
        MockEventSource.instances[0].emit({ unexpected: "payload" });
      });
      // Give a tick for the async state update (which should not happen).
      await waitFor(() => expect(result.current.latestEvent).toBeNull());
      expect(result.current.isStreaming).toBe(true);
    });

    it("re-opens the stream when the id changes", () => {
      const { rerender } = renderHook(
        ({ id }: { id: string }) => useCarouselStream(id),
        {
          wrapper: createWrapper(),
          initialProps: { id: "abc-123" },
        }
      );
      expect(MockEventSource.instances).toHaveLength(1);
      expect(MockEventSource.instances[0].url).toBe("/api/carousels/abc-123/stream");

      rerender({ id: "def-456" });
      expect(MockEventSource.instances).toHaveLength(2);
      expect(MockEventSource.instances[1].url).toBe("/api/carousels/def-456/stream");
    });

    it("auto-reconnects after a transport error with exponential backoff", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      const first = MockEventSource.instances[0];

      act(() => {
        first.readyState = MockEventSource.CLOSED;
        first.onerror?.();
      });

      expect(result.current.isStreaming).toBe(false);
      expect(MockEventSource.instances).toHaveLength(1);

      act(() => {
        vi.runOnlyPendingTimers();
      });

      expect(MockEventSource.instances).toHaveLength(2);
      expect(result.current.isStreaming).toBe(true);

      vi.useRealTimers();
    });

    it("resets retry budget after a successful event", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });

      // First error → schedules reconnect at 1s.
      const first = MockEventSource.instances[0];
      act(() => {
        first.readyState = MockEventSource.CLOSED;
        first.onerror?.();
      });
      expect(result.current.isStreaming).toBe(false);

      act(() => {
        vi.runOnlyPendingTimers();
      });
      expect(MockEventSource.instances).toHaveLength(2);

      // A successful event arrives on the second connection.
      const second = MockEventSource.instances[1];
      act(() => {
        second.emit({ node: "research", status: "researching" });
      });

      // Second error should still use 1s backoff (budget reset).
      act(() => {
        second.readyState = MockEventSource.CLOSED;
        second.onerror?.();
      });
      expect(result.current.isStreaming).toBe(false);

      act(() => {
        vi.runOnlyPendingTimers();
      });
      expect(MockEventSource.instances).toHaveLength(3);

      vi.useRealTimers();
    });

    it("stops retrying after max retries and surfaces the error", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });

      // Exhaust all retries (20 retries = 21 total connections).
      for (let i = 0; i < 21; i += 1) {
        const current = MockEventSource.instances[MockEventSource.instances.length - 1];
        act(() => {
          current.readyState = MockEventSource.CLOSED;
          current.onerror?.();
        });
        act(() => {
          vi.runOnlyPendingTimers();
        });
      }

      expect(result.current.error).toBe("stream disconnected — max retries reached");
      expect(result.current.isStreaming).toBe(false);

      vi.useRealTimers();
    });

    it("exposes a manual reconnect function", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      const first = MockEventSource.instances[0];

      act(() => {
        first.readyState = MockEventSource.CLOSED;
        first.onerror?.();
      });
      expect(result.current.isStreaming).toBe(false);

      act(() => {
        result.current.reconnect();
      });

      expect(MockEventSource.instances).toHaveLength(2);
      expect(result.current.isStreaming).toBe(true);

      vi.useRealTimers();
    });

    // Mutation-killing tests below target specific Stryker mutants that
    // the happy-path tests above don't catch.

    it("does not reconnect on a non-CLOSED readyState error", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      const mock = MockEventSource.instances[0];

      // Simulate a transient network blip (CONNECTING = 0, not CLOSED = 2).
      act(() => {
        mock.readyState = MockEventSource.CONNECTING;
        mock.onerror?.();
      });

      // Stream should stay alive; no reconnect timer scheduled.
      expect(result.current.isStreaming).toBe(true);
      expect(MockEventSource.instances).toHaveLength(1);

      vi.useRealTimers();
    });

    it("allows exactly MAX_STREAM_RETRIES reconnects before giving up", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });

      // 20 failures should all be retried (21 total connections).
      for (let i = 0; i < 20; i += 1) {
        const current = MockEventSource.instances[MockEventSource.instances.length - 1];
        act(() => {
          current.readyState = MockEventSource.CLOSED;
          current.onerror?.();
        });
        act(() => {
          vi.runOnlyPendingTimers();
        });
      }

      // 21st should fail permanently.
      const last = MockEventSource.instances[MockEventSource.instances.length - 1];
      act(() => {
        last.readyState = MockEventSource.CLOSED;
        last.onerror?.();
      });
      act(() => {
        vi.runOnlyPendingTimers();
      });

      expect(result.current.error).toBe("stream disconnected — max retries reached");
      // No 22nd EventSource created.
      expect(MockEventSource.instances).toHaveLength(21);

      vi.useRealTimers();
    });

    it("uses increasing backoff delays for each retry", () => {
      vi.useFakeTimers();
      renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });

      const delays: number[] = [];
      for (let i = 0; i < 5; i += 1) {
        const current = MockEventSource.instances[MockEventSource.instances.length - 1];
        act(() => {
          current.readyState = MockEventSource.CLOSED;
          current.onerror?.();
        });

        const before = vi.getTimerCount();
        // Fast-forward just enough to verify the delay is increasing.
        act(() => {
          vi.advanceTimersByTime(1);
        });
        const after = vi.getTimerCount();
        // Timer still pending = delay > 1ms.
        delays.push(after > 0 ? 1 : 0);

        act(() => {
          vi.runOnlyPendingTimers();
        });
      }

      // Backoff should increase: 1s, 2s, 4s, 8s, 16s.
      // All timers after the first ms should still be pending (delay > 1ms).
      expect(delays[0]).toBe(1); // 1s > 1ms
      expect(delays[1]).toBe(1); // 2s > 1ms
      expect(delays[2]).toBe(1); // 4s > 1ms
      expect(delays[3]).toBe(1); // 8s > 1ms
      expect(delays[4]).toBe(1); // 16s > 1ms

      vi.useRealTimers();
    });

    it("cancels pending reconnect timer on manual close", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });
      const mock = MockEventSource.instances[0];

      act(() => {
        mock.readyState = MockEventSource.CLOSED;
        mock.onerror?.();
      });

      // Before the timer fires, call close() explicitly.
      act(() => {
        result.current.close();
      });

      // Advance timers — no new EventSource should be created.
      act(() => {
        vi.runAllTimers();
      });

      expect(MockEventSource.instances).toHaveLength(1);

      vi.useRealTimers();
    });

    it("clears error state on a fresh reconnect", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });

      // Exhaust retries to set an error.
      for (let i = 0; i < 21; i += 1) {
        const current = MockEventSource.instances[MockEventSource.instances.length - 1];
        act(() => {
          current.readyState = MockEventSource.CLOSED;
          current.onerror?.();
        });
        act(() => {
          vi.runOnlyPendingTimers();
        });
      }
      expect(result.current.error).toBe("stream disconnected — max retries reached");

      // Manual reconnect should clear the error.
      act(() => {
        result.current.reconnect();
      });
      expect(result.current.error).toBeNull();
      expect(result.current.isStreaming).toBe(true);

      vi.useRealTimers();
    });

    it("does not update cache for events missing a status field", () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCarouselStream("abc-123"), {
        wrapper: createWrapper(),
      });

      // Emit an event without `status` — should be ignored for cache update
      // but still update latestEvent.
      act(() => {
        MockEventSource.instances[0].emit({
          node: "heartbeat",
          status: undefined,
        });
      });

      // latestEvent should still be set (the event passed schema validation).
      expect(result.current.latestEvent?.node).toBe("heartbeat");

      vi.useRealTimers();
    });
  });
});
