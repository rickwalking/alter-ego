/**
 * AE-0429: the session-expired logout handler lives at `/auth/logout`, outside
 * `/api` (nginx proxies `/api/*` to FastAPI, so a Next route there never runs).
 * Covers the Gherkin scenarios in
 * `tests/features/session-expired-redirect-ae0429.feature`.
 */
import { NextRequest } from "next/server";
import { describe, expect, it, vi, type MockInstance } from "vitest";

import { COOKIE_ACCESS_TOKEN } from "@/modules/identity";
import { GET } from "./route";

const BACKEND_LOGIN_PATH = "/login";
const SESSION_EXPIRED_ERROR = "session_expired";
const SAFE_REDIRECT = "/dashboard/chat";
const LOGIN_REDIRECT = "/dashboard/create/abc?step=content";

function makeRequest(url: string, cookie?: string): NextRequest {
  const headers = new Headers();
  if (cookie) {
    headers.set("cookie", cookie);
  }
  return new NextRequest(`http://app.test${url}`, { headers });
}

function locationOf(response: Response): URL {
  return new URL(response.headers.get("location") ?? "");
}

function loginUrlWithRedirect(redirect: string): string {
  const url = new URL(BACKEND_LOGIN_PATH, "http://app.test");
  url.searchParams.set("redirect", redirect);
  url.searchParams.set("error", SESSION_EXPIRED_ERROR);
  return url.toString();
}

function mockBackendLogout(
  implementation: () => Promise<Response> = async () =>
    new Response(null, { status: 204 }),
): MockInstance<typeof fetch> {
  return vi.spyOn(globalThis, "fetch").mockImplementation(implementation);
}

function expectCookieCleared(response: Response): void {
  const clearedCookies = response.headers.getSetCookie();
  expect(
    clearedCookies.some((cookie) =>
      cookie.startsWith(`${COOKIE_ACCESS_TOKEN}=;`),
    ),
  ).toBe(true);
}

describe("GET /auth/logout", () => {
  it("clears the cookie and returns to login with the path and query", async () => {
    const fetchMock = mockBackendLogout();
    const response = await GET(
      makeRequest(
        `/auth/logout?redirect=${encodeURIComponent(LOGIN_REDIRECT)}`,
        `${COOKIE_ACCESS_TOKEN}=jwt`,
      ),
    );

    expectCookieCleared(response);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/auth\/logout$/);
    expect(init?.method).toBe("POST");
    expect(locationOf(response).toString()).toBe(
      loginUrlWithRedirect(LOGIN_REDIRECT),
    );
  });

  it("drops a protocol-relative external redirect", async () => {
    mockBackendLogout();
    const response = await GET(makeRequest("/auth/logout?redirect=//evil.com"));

    expectCookieCleared(response);
    expect(locationOf(response).toString()).toBe(
      loginUrlWithRedirect(SAFE_REDIRECT),
    );
  });

  it("drops an absolute external redirect", async () => {
    mockBackendLogout();
    const response = await GET(
      makeRequest("/auth/logout?redirect=https://evil.com"),
    );

    expectCookieCleared(response);
    expect(locationOf(response).toString()).toBe(
      loginUrlWithRedirect(SAFE_REDIRECT),
    );
  });

  it("redirects to login without a redirect param when none is given", async () => {
    mockBackendLogout();
    const response = await GET(makeRequest("/auth/logout"));

    expectCookieCleared(response);
    const location = locationOf(response);
    expect(location.pathname).toBe(BACKEND_LOGIN_PATH);
    expect(location.searchParams.has("redirect")).toBe(false);
    expect(location.searchParams.get("error")).toBe(SESSION_EXPIRED_ERROR);
  });

  it("still clears the cookie and redirects when the backend logout fails", async () => {
    mockBackendLogout(async () => {
      throw new Error("backend down");
    });

    const response = await GET(makeRequest("/auth/logout"));

    expectCookieCleared(response);
    const location = locationOf(response);
    expect(location.pathname).toBe(BACKEND_LOGIN_PATH);
    expect(location.searchParams.get("error")).toBe(SESSION_EXPIRED_ERROR);
  });
});
