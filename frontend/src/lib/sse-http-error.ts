/** A non-2xx answer to an SSE request; ``message`` stays ``HTTP <status>``. */
export class SseHttpError extends Error {
  constructor(public readonly status: number) {
    super(`HTTP ${String(status)}`);
    this.name = "SseHttpError";
  }
}
