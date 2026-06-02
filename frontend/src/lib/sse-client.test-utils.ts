/**
 * Test utilities for SSE client tests.
 *
 * Provides mock ReadableStream reader and Response factories
 * to simulate SSE streaming responses in vitest/jsdom.
 */

/**
 * Create a mock ReadableStream reader that yields Uint8Array chunks.
 */
export function createMockReader(
  chunks: Uint8Array[],
): { read: () => Promise<ReadableStreamReadResult<Uint8Array>> } {
  let index = 0;
  return {
    read: async () => {
      if (index < chunks.length) {
        const value = chunks[index]!;
        index++;
        return { done: false, value };
      }
      return { done: true, value: undefined };
    },
  };
}

/**
 * Create a mock Response for SSE streaming tests.
 */
export function createSseResponse(
  chunks: string[],
  status = 200,
): Response {
  const encoder = new TextEncoder();
  const reader = createMockReader(
    chunks.map((chunk) => encoder.encode(chunk)),
  );

  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    headers: new Headers({
      "content-type": "text/event-stream",
    }),
    body: {
      getReader: () => reader,
    } as unknown as ReadableStream<Uint8Array>,
  } as Response;
}
