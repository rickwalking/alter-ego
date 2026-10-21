/**
 * Typed dispatch for SSE chat events. Each chat hook declares one
 * handler per event type instead of an if-chain over `event.event`.
 */
import type { SseEvent } from "@/lib/sse-client";

type SseEventType = NonNullable<SseEvent["event"]>;

export type SseEventData = SseEvent["data"];

export type SseEventHandlers = Partial<
  Record<SseEventType, (data: SseEventData) => void>
>;

/** Route an event to its handler; events without one are ignored. */
export function dispatchSseEvent(
  handlers: SseEventHandlers,
): (event: SseEvent) => void {
  return (event: SseEvent): void => {
    if (event.event === undefined) {
      return;
    }
    handlers[event.event]?.(event.data);
  };
}

/** `data.content` when it is a string, else `fallback`. */
export function sseContentText(data: SseEventData, fallback: string): string {
  return typeof data.content === "string" ? data.content : fallback;
}
