"use client";

/**
 * SSE event types from the backend.
 */
export const SSE_EVENT_TYPE = {
  TOKEN: "token",
  COMPLETE: "complete",
  ERROR: "error",
  SOURCES: "sources",
  TOOL_RESULT: "tool_result",
} as const;

export type SseEventType = (typeof SSE_EVENT_TYPE)[keyof typeof SSE_EVENT_TYPE];

/**
 * Parsed SSE event.
 */
export interface SseEvent {
  id?: string;
  event?: SseEventType;
  data: Record<string, unknown>;
}

/**
 * Options for streaming SSE from a POST endpoint.
 */
export interface SseStreamOptions {
  url: string;
  body: Record<string, unknown>;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  lastEventId?: string;
  onEvent: (event: SseEvent) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

/**
 * Fetch SSE events from a POST endpoint.
 *
 * Uses fetch + response.text() because Cloudflare HTTP/2 proxy does not
 * reliably support ReadableStream reader with streaming responses.
 * Supports resumability via the ``Last-Event-ID`` header.
 */
export async function streamSseEvents({
  url,
  body,
  headers = {},
  signal,
  lastEventId,
  onEvent,
  onError,
  onComplete,
}: SseStreamOptions): Promise<void> {
  try {
    const requestHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...headers,
    };

    if (lastEventId) {
      requestHeaders["Last-Event-ID"] = lastEventId;
    }

    const response = await fetch(url, {
      method: "POST",
      headers: requestHeaders,
      body: JSON.stringify(body),
      credentials: "include",
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.includes("text/event-stream")) {
      throw new Error(`Unexpected content type: ${contentType}`);
    }

    const text = await response.text();

    // Parse SSE events line-by-line to handle embedded \n\n within JSON data values
    const lines = text.split("\n");
    let currentId: string | undefined;
    let currentEvent: SseEventType | undefined;
    let currentData = "";

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.startsWith("id: ")) {
        currentId = line.slice(4);
      } else if (line.startsWith("event: ")) {
        currentEvent = line.slice(7) as SseEventType;
      } else if (line.startsWith("data: ")) {
        currentData += line.slice(6);
      } else if (line === "" || line === "\r") {
        // Empty line = end of SSE event — dispatch it
        if (currentData || currentEvent) {
          let parsedData: Record<string, unknown> = {};
          if (currentData) {
            try {
              parsedData = JSON.parse(currentData) as Record<string, unknown>;
            } catch {
              parsedData = { raw: currentData };
            }
          }

          // Backend embeds event type in data.type rather than using SSE event: field
          const eventType =
            currentEvent ??
            (parsedData.type && typeof parsedData.type === "string"
              ? (parsedData.type as SseEventType)
              : undefined);

          onEvent({ id: currentId, event: eventType, data: parsedData });
        }
        currentId = undefined;
        currentEvent = undefined;
        currentData = "";
      }
    }

    // Handle the last event if there's no trailing blank line
    if (currentData || currentEvent) {
      let parsedData: Record<string, unknown> = {};
      if (currentData) {
        try {
          parsedData = JSON.parse(currentData) as Record<string, unknown>;
        } catch {
          parsedData = { raw: currentData };
        }
      }
      const eventType =
        currentEvent ??
        (parsedData.type && typeof parsedData.type === "string"
          ? (parsedData.type as SseEventType)
          : undefined);
      onEvent({ id: currentId, event: eventType, data: parsedData });
    }

    onComplete?.();
  } catch (error) {
    onError?.(error instanceof Error ? error : new Error(String(error)));
  }
}
