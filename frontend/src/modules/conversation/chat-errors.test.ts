/**
 * Gherkin: tests/features/chat-errors-ui.feature
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api-client";
import { SseHttpError } from "@/lib/sse-http-error";
import { classifyChatError } from "./chat-errors";

const CREATING = "creating";
const REQUESTING = "requesting";
const STREAMING = "streaming";

describe("classifyChatError", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  /** Scenario: An over-long message explains the limit instead of "HTTP 422" */
  it("maps a 422 from the stream to tooLong, but not one from creating the conversation", () => {
    expect(classifyChatError(new SseHttpError(422), REQUESTING)).toEqual({
      kind: "tooLong",
      retryable: false,
    });
    expect(classifyChatError(new ApiError(422, "bad"), CREATING).kind).toBe(
      "generic",
    );
  });

  /** Scenario: A full conversation offers a new chat instead of a retry */
  it("maps a 429 to limit, never retryable", () => {
    expect(classifyChatError(new SseHttpError(429), REQUESTING)).toEqual({
      kind: "limit",
      retryable: false,
    });
    expect(classifyChatError(new ApiError(429, "slow"), CREATING)).toEqual({
      kind: "limit",
      retryable: false,
    });
  });

  /** Scenario: Retry is offered only when nothing was saved yet */
  it("lets a 5xx before the response be retried", () => {
    expect(classifyChatError(new SseHttpError(503), REQUESTING)).toEqual({
      kind: "generic",
      retryable: true,
    });
  });

  /** Scenario: Retry is offered only when nothing was saved yet */
  it("never retries once the answer stream had started", () => {
    expect(classifyChatError(new Error("reset"), STREAMING)).toEqual({
      kind: "generic",
      retryable: false,
    });
    expect(
      classifyChatError(new TypeError("network error"), STREAMING),
    ).toEqual({ kind: "generic", retryable: false });
  });

  /** Scenario: Each failure shows a plain, localized message */
  it("treats a fetch TypeError before any response as offline", () => {
    expect(
      classifyChatError(new TypeError("Failed to fetch"), REQUESTING),
    ).toEqual({ kind: "offline", retryable: true });
    expect(classifyChatError(new TypeError("Load failed"), CREATING)).toEqual({
      kind: "offline",
      retryable: true,
    });
  });

  /** Scenario: Each failure shows a plain, localized message */
  it("treats an offline browser as offline at any stage", () => {
    vi.stubGlobal("navigator", { onLine: false });
    expect(classifyChatError(new Error("x"), STREAMING).kind).toBe("offline");
  });

  /** Scenario: A signed-in user whose session expired is told to sign in again */
  it("maps 401 to sessionExpired and 404 to notFound", () => {
    expect(classifyChatError(new SseHttpError(401), REQUESTING).kind).toBe(
      "sessionExpired",
    );
    expect(classifyChatError(new SseHttpError(404), REQUESTING).kind).toBe(
      "notFound",
    );
  });
});
