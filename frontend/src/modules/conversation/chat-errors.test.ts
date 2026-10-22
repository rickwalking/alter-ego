/**
 * Gherkin: tests/features/chat-errors-ui.feature
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api-client";
import { SseHttpError } from "@/lib/sse-http-error";
import { classifyChatError } from "./chat-errors";

describe("classifyChatError", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  /** Scenario: An over-long message explains the limit instead of "HTTP 422" */
  it("maps 422 to tooLong", () => {
    expect(classifyChatError(new SseHttpError(422))).toBe("tooLong");
  });

  /** Scenario: Each failure shows a plain, localized message */
  it.each([
    [new SseHttpError(429), "limit"],
    [new ApiError(429, "Too Many Requests"), "limit"],
    [new SseHttpError(500), "generic"],
    [new Error("anything"), "generic"],
    ["not an error", "generic"],
  ])("maps %s to %s", (error, kind) => {
    expect(classifyChatError(error)).toBe(kind);
  });

  /** Scenario: A signed-in user whose session expired is told to sign in again */
  it("maps 401 and 404 to a session or conversation problem", () => {
    expect(classifyChatError(new SseHttpError(401))).toBe("sessionExpired");
    expect(classifyChatError(new SseHttpError(404))).toBe("notFound");
  });

  /** Scenario: Each failure shows a plain, localized message */
  it("maps a network failure or an offline browser to offline", () => {
    expect(classifyChatError(new TypeError("Failed to fetch"))).toBe("offline");
    vi.stubGlobal("navigator", { onLine: false });
    expect(classifyChatError(new Error("x"))).toBe("offline");
  });
});
