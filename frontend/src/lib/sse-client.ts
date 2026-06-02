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

/** SSE event type derived from SSE_EVENT_TYPE constant. */
type SseEventType = (typeof SSE_EVENT_TYPE)[keyof typeof SSE_EVENT_TYPE];

/** HTTP header name for the Content-Type header. */
const HEADER_CONTENT_TYPE = "content-type";

/** HTTP header name for the Accept header. */
const HEADER_ACCEPT = "accept";

/** HTTP header name for the Last-Event-ID header. */
const HEADER_LAST_EVENT_ID = "last-event-id";

/** MIME type for JSON content. */
const MIME_APPLICATION_JSON = "application/json";

/** MIME type for SSE streaming. */
const MIME_TEXT_EVENT_STREAM = "text/event-stream";

/** HTTP method for creating SSE streams. */
const METHOD_POST = "POST";

/** Credentials mode for including cookies in requests. */
const CREDENTIALS_INCLUDE = "include";

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
 *
 * @remarks onComplete fires at end-of-stream regardless of whether the
 * last event was an error. Callers should inspect the last event's type
 * to distinguish success from in-stream error events.
 */
interface SseStreamOptions {
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
 * Internal state for the incremental SSE parser.
 */
interface SseParserState {
  currentId: string | undefined;
  currentEvent: SseEventType | undefined;
  currentData: string;
  buffer: string;
}

/**
 * Create a fresh parser state.
 */
function createParserState(): SseParserState {
  return {
    currentId: undefined,
    currentEvent: undefined,
    currentData: "",
    buffer: "",
  };
}

/**
 * Parse a single SSE line and accumulate it into the parser state.
 * Returns a parsed SseEvent if a blank-line delimiter completes an event,
 * or ``null`` otherwise.
 */
function parseSseLine(line: string, state: SseParserState): SseEvent | null {
  if (line.startsWith("id: ")) {
    state.currentId = line.slice(4);
    return null;
  }
  if (line.startsWith("event: ")) {
    state.currentEvent = line.slice(7) as SseEventType;
    return null;
  }
  if (line.startsWith("data: ")) {
    state.currentData += line.slice(6);
    return null;
  }
  // Comment lines (starting with :) are ignored (keep-alive pings)
  if (line.startsWith(":")) {
    return null;
  }
  // Empty line = end of SSE event — dispatch it
  if (line === "" || line === "\r") {
    return flushEvent(state);
  }
  // Unknown line — ignore
  return null;
}

/**
 * Flush the accumulated event from the parser state.
 * Resets accumulators and returns the parsed SseEvent (or ``null`` if empty).
 */
function flushEvent(state: SseParserState): SseEvent | null {
  if (!state.currentData && !state.currentEvent) {
    return null;
  }

  let parsedData: Record<string, unknown> = {};
  if (state.currentData) {
    try {
      parsedData = JSON.parse(state.currentData) as Record<string, unknown>;
    } catch {
      parsedData = { raw: state.currentData };
    }
  }

  // Backend embeds event type in data.type rather than using SSE event: field
  const eventType =
    state.currentEvent ??
    (parsedData.type && typeof parsedData.type === "string"
      ? (parsedData.type as SseEventType)
      : undefined);

  const event: SseEvent = {
    id: state.currentId,
    event: eventType,
    data: parsedData,
  };

  // Reset accumulators
  state.currentId = undefined;
  state.currentEvent = undefined;
  state.currentData = "";

  return event;
}

/**
 * Process a text chunk from the stream buffer, extracting complete SSE events.
 *
 * Handles ``\n\n`` delimiters that may span across chunk boundaries by
 * maintaining an internal buffer. Returns an array of parsed events.
 */
function processChunk(chunk: string, state: SseParserState): SseEvent[] {
  state.buffer += chunk;

  const events: SseEvent[] = [];
  let searchStart = 0;

  while (searchStart < state.buffer.length) {
    // Find the next blank-line delimiter (\n\n or \n\r\n)
    const delimIndex = findBlankLine(state.buffer, searchStart);
    if (delimIndex === -1) {
      break; // No complete event yet — wait for more data
    }

    // Extract the event lines (everything up to the blank line)
    const eventBlock = state.buffer.slice(searchStart, delimIndex);
    // Advance past the blank line
    searchStart = delimIndex + findDelimiterLength(state.buffer, delimIndex);

    // Parse each line in the event block — this sets state.currentData etc.
    const lines = eventBlock.split("\n");
    for (const line of lines) {
      parseSseLine(line, state);
    }
    // Blank-line boundary hit — flush the accumulated event
    const event = flushEvent(state);
    if (event !== null) {
      events.push(event);
    }
  }

  // Keep remaining (incomplete) data in the buffer
  state.buffer = state.buffer.slice(searchStart);

  return events;
}

/**
 * Find the position of the next blank-line delimiter (``\n\n`` or ``\n\r\n``)
 * starting from ``start`` in the buffer.
 *
 * Returns the index of the first ``\n`` of the delimiter, or ``-1`` if not found.
 */
function findBlankLine(buffer: string, start: number): number {
  for (let i = start; i < buffer.length - 1; i++) {
    if (buffer[i] === "\n") {
      if (buffer[i + 1] === "\n") {
        return i;
      }
      if (
        i + 2 < buffer.length &&
        buffer[i + 1] === "\r" &&
        buffer[i + 2] === "\n"
      ) {
        return i;
      }
    }
  }
  return -1;
}

/**
 * Determine the length of the delimiter at the given position.
 * The position should be the first ``\n`` of the delimiter.
 */
function findDelimiterLength(buffer: string, pos: number): number {
  if (pos + 1 < buffer.length && buffer[pos + 1] === "\n") {
    return 2; // \n\n
  }
  if (
    pos + 2 < buffer.length &&
    buffer[pos + 1] === "\r" &&
    buffer[pos + 2] === "\n"
  ) {
    return 3; // \n\r\n
  }
  return 2; // default
}

/**
 * Flush any remaining data in the buffer after the stream ends.
 * Handles the case where the last event has no trailing blank line.
 */
function flushBuffer(state: SseParserState): SseEvent | null {
  // Process any complete events remaining in the buffer
  const remaining = state.buffer.trim();
  if (!remaining) {
    return null;
  }

  const lines = remaining.split("\n");
  for (const line of lines) {
    parseSseLine(line, state);
  }

  return flushEvent(state);
}

/**
 * Fetch SSE events from a POST endpoint using a streaming reader.
 *
 * Uses ``response.body.getReader()`` with a ``TextDecoder`` to read the
 * response as a stream, parsing SSE events incrementally as they arrive.
 * This provides true streaming behavior — ``onEvent`` is called as each
 * event is received rather than waiting for the entire response body.
 *
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
      [HEADER_CONTENT_TYPE]: MIME_APPLICATION_JSON,
      [HEADER_ACCEPT]: MIME_TEXT_EVENT_STREAM,
      ...headers,
    };

    if (lastEventId) {
      requestHeaders[HEADER_LAST_EVENT_ID] = lastEventId;
    }

    const response = await fetch(url, {
      method: METHOD_POST,
      headers: requestHeaders,
      body: JSON.stringify(body),
      credentials: CREDENTIALS_INCLUDE,
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const contentType = response.headers.get(HEADER_CONTENT_TYPE) ?? "";
    if (!contentType.includes(MIME_TEXT_EVENT_STREAM)) {
      throw new Error(`Unexpected content type: ${contentType}`);
    }

    if (!response.body) {
      throw new Error("Response body is not readable");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const parserState = createParserState();

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      const events = processChunk(chunk, parserState);

      for (const event of events) {
        onEvent(event);
      }
    }

    // Process any remaining data after the stream closes
    const finalEvent = flushBuffer(parserState);
    if (finalEvent !== null) {
      onEvent(finalEvent);
    }

    onComplete?.();
  } catch (error) {
    // AbortError is expected when the user cancels — do not report as error
    if (error instanceof DOMException && error.name === "AbortError") {
      return;
    }
    const wrappedError =
      error instanceof Error ? error : new Error(String(error));
    console.warn("[sse-client] Connection error:", wrappedError.message);
    onError?.(wrappedError);
  }
}
