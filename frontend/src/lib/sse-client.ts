"use client";

import { SseHttpError } from "./sse-http-error";

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

/** SSE field prefixes (value starts after the prefix length). */
const SSE_FIELD_ID = "id: ";
const SSE_FIELD_EVENT = "event: ";
const SSE_FIELD_DATA = "data: ";

/** Byte length of a CRLF-style blank-line event delimiter (``\n\r\n``). */
const SSE_DELIMITER_LENGTH_CRLF = 3;

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
 *
 * Comment lines (starting with `:`, keep-alive pings) and unknown lines are
 * ignored.
 */
function parseSseLine(line: string, state: SseParserState): SseEvent | null {
  if (line.startsWith(SSE_FIELD_ID)) {
    state.currentId = line.slice(SSE_FIELD_ID.length);
    return null;
  }
  if (line.startsWith(SSE_FIELD_EVENT)) {
    state.currentEvent = line.slice(SSE_FIELD_EVENT.length) as SseEventType;
    return null;
  }
  if (line.startsWith(SSE_FIELD_DATA)) {
    state.currentData += line.slice(SSE_FIELD_DATA.length);
    return null;
  }
  if (line.startsWith(":")) {
    return null;
  }
  if (line === "" || line === "\r") {
    return flushEvent(state);
  }
  return null;
}

/** The event's JSON data, or ``{raw}`` when it is not JSON. */
function parseEventData(raw: string): Record<string, unknown> {
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return { raw };
  }
}

/** The SSE ``event:`` field, else the backend's ``data.type``. */
function eventTypeOf(
  field: SseEventType | undefined,
  data: Record<string, unknown>,
): SseEventType | undefined {
  if (field) {
    return field;
  }
  return typeof data.type === "string" && data.type
    ? (data.type as SseEventType)
    : undefined;
}

/**
 * Flush the accumulated event from the parser state.
 * Resets accumulators and returns the parsed SseEvent (or ``null`` if empty).
 *
 * The backend embeds the event type in data.type rather than the SSE event:
 * field, so that is the fallback.
 */
function flushEvent(state: SseParserState): SseEvent | null {
  if (!state.currentData && !state.currentEvent) {
    return null;
  }
  const data = parseEventData(state.currentData);
  const event: SseEvent = {
    id: state.currentId,
    event: eventTypeOf(state.currentEvent, data),
    data,
  };

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
 *
 * Incomplete trailing data stays in the buffer until more arrives.
 */
function processChunk(chunk: string, state: SseParserState): SseEvent[] {
  state.buffer += chunk;

  const events: SseEvent[] = [];
  let searchStart = 0;

  while (searchStart < state.buffer.length) {
    const delimIndex = findBlankLine(state.buffer, searchStart);
    if (delimIndex === -1) {
      break;
    }
    const event = consumeEventBlock(
      state.buffer.slice(searchStart, delimIndex),
      state,
    );
    if (event !== null) {
      events.push(event);
    }
    searchStart = delimIndex + findDelimiterLength(state.buffer, delimIndex);
  }

  state.buffer = state.buffer.slice(searchStart);

  return events;
}

/** Parse one event block's lines, then flush the event at its blank line. */
function consumeEventBlock(
  block: string,
  state: SseParserState,
): SseEvent | null {
  for (const line of block.split("\n")) {
    parseSseLine(line, state);
  }
  return flushEvent(state);
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
 *
 * Returns 2 for `\n\n` (also the default) and 3 for `\n\r\n`.
 */
function findDelimiterLength(buffer: string, pos: number): number {
  if (pos + 1 < buffer.length && buffer[pos + 1] === "\n") {
    return 2;
  }
  if (
    pos + 2 < buffer.length &&
    buffer[pos + 1] === "\r" &&
    buffer[pos + 2] === "\n"
  ) {
    return SSE_DELIMITER_LENGTH_CRLF;
  }
  return 2;
}

/**
 * Flush any remaining data in the buffer after the stream ends.
 * Handles the case where the last event has no trailing blank line.
 */
function flushBuffer(state: SseParserState): SseEvent | null {
  const remaining = state.buffer.trim();
  if (!remaining) {
    return null;
  }

  return consumeEventBlock(remaining, state);
}

type SseRequest = Pick<
  SseStreamOptions,
  "url" | "body" | "headers" | "signal" | "lastEventId"
>;

/** JSON in, event stream out, plus ``Last-Event-ID`` when resuming. */
function sseRequestHeaders(
  headers: Record<string, string>,
  lastEventId: string | undefined,
): Record<string, string> {
  const requestHeaders: Record<string, string> = {
    [HEADER_CONTENT_TYPE]: MIME_APPLICATION_JSON,
    [HEADER_ACCEPT]: MIME_TEXT_EVENT_STREAM,
    ...headers,
  };
  if (lastEventId) {
    requestHeaders[HEADER_LAST_EVENT_ID] = lastEventId;
  }
  return requestHeaders;
}

/** POST the request and return the body reader of a valid event stream. */
async function openSseStream({
  url,
  body,
  headers = {},
  signal,
  lastEventId,
}: SseRequest): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const response = await fetch(url, {
    method: METHOD_POST,
    headers: sseRequestHeaders(headers, lastEventId),
    body: JSON.stringify(body),
    credentials: CREDENTIALS_INCLUDE,
    signal,
  });
  if (!response.ok) {
    throw new SseHttpError(response.status);
  }
  const contentType = response.headers.get(HEADER_CONTENT_TYPE) ?? "";
  if (!contentType.includes(MIME_TEXT_EVENT_STREAM)) {
    throw new Error(`Unexpected content type: ${contentType}`);
  }
  if (!response.body) {
    throw new Error("Response body is not readable");
  }
  return response.body.getReader();
}

/**
 * Decode the stream and emit each event as it completes, then the tail.
 *
 * Data left after the stream closes is flushed as a final event.
 */
async function pumpSseEvents(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  const decoder = new TextDecoder();
  const parserState = createParserState();
  for (
    let result = await reader.read();
    !result.done;
    result = await reader.read()
  ) {
    const chunk = decoder.decode(result.value, { stream: true });
    for (const event of processChunk(chunk, parserState)) {
      onEvent(event);
    }
  }
  const finalEvent = flushBuffer(parserState);
  if (finalEvent !== null) {
    onEvent(finalEvent);
  }
}

/** Report a stream failure; a user abort is expected, not an error. */
function reportSseError(
  error: unknown,
  onError: SseStreamOptions["onError"],
): void {
  if (error instanceof DOMException && error.name === "AbortError") {
    return;
  }
  const wrappedError =
    error instanceof Error ? error : new Error(String(error));
  console.warn("[sse-client] Connection error:", wrappedError.message);
  onError?.(wrappedError);
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
export async function streamSseEvents(
  options: SseStreamOptions,
): Promise<void> {
  try {
    const reader = await openSseStream(options);
    await pumpSseEvents(reader, options.onEvent);
    options.onComplete?.();
  } catch (error) {
    reportSseError(error, options.onError);
  }
}
