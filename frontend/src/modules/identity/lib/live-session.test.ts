/**
 * Gherkin: tests/features/dashboard-chat.feature
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  payload: null as { exp: number } | null,
}));

vi.mock("./jwt-auth", () => ({
  verifyAccessToken: () => Promise.resolve(mocks.payload),
}));

import { isLiveSession } from "./live-session";

const IN_AN_HOUR = Math.floor(Date.now() / 1000) + 3600;

describe("isLiveSession", () => {
  beforeEach(() => {
    mocks.payload = null;
  });

  /** Scenario: A signed-in user opening /chat lands on the dashboard chat */
  it("is true for a valid, unexpired token", async () => {
    mocks.payload = { exp: IN_AN_HOUR };
    await expect(isLiveSession("jwt")).resolves.toBe(true);
  });

  /** Scenario: A signed-in user opening /chat lands on the dashboard chat */
  it.each([
    ["no cookie", undefined, null],
    ["an invalid token", "jwt", null],
    ["an expired session", "jwt", { exp: 1 }],
  ])("is false for %s", async (_label, token, payload) => {
    mocks.payload = payload;
    await expect(isLiveSession(token)).resolves.toBe(false);
  });
});
