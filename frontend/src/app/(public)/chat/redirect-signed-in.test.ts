/**
 * Gherkin: tests/features/dashboard-chat.feature
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";

const mocks = vi.hoisted(() => ({
  token: undefined as string | undefined,
  live: false,
  redirect: vi.fn(),
  isLiveSession: vi.fn(),
}));

vi.mock("next/headers", () => ({
  cookies: () =>
    Promise.resolve({
      get: () => (mocks.token ? { value: mocks.token } : undefined),
    }),
}));

vi.mock("next/navigation", () => ({ redirect: mocks.redirect }));

vi.mock("@/modules/identity", () => ({
  COOKIE_ACCESS_TOKEN: "access_token",
  isLiveSession: mocks.isLiveSession,
}));

import { redirectSignedInToDashboardChat } from "./redirect-signed-in";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.token = undefined;
  mocks.live = false;
  mocks.isLiveSession.mockImplementation(() => Promise.resolve(mocks.live));
});

describe("redirectSignedInToDashboardChat", () => {
  /** Scenario: A signed-in user opening /chat lands on the dashboard chat */
  it("sends a signed-in user to the dashboard chat", async () => {
    mocks.token = "jwt";
    mocks.live = true;

    await redirectSignedInToDashboardChat();

    expect(mocks.isLiveSession).toHaveBeenCalledWith("jwt");
    expect(mocks.redirect).toHaveBeenCalledWith(DASHBOARD_ROUTES.CHAT);
  });

  /** Scenario: A signed-in user opening /chat lands on the dashboard chat */
  it("keeps a visitor without a session cookie on the public chat", async () => {
    await redirectSignedInToDashboardChat();

    expect(mocks.isLiveSession).toHaveBeenCalledWith(undefined);
    expect(mocks.redirect).not.toHaveBeenCalled();
  });

  /** Scenario: A signed-in user opening /chat lands on the dashboard chat */
  it("keeps a visitor or an expired session on the public chat", async () => {
    mocks.token = "expired";
    mocks.live = false;

    await redirectSignedInToDashboardChat();

    expect(mocks.isLiveSession).toHaveBeenCalledWith("expired");
    expect(mocks.redirect).not.toHaveBeenCalled();
  });
});
