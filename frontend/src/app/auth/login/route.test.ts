/**
 * The no-JavaScript sign-in handler at `/auth/login`. Covers
 * `tests/features/login-form-post-only.feature`.
 */
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { COOKIE_ACCESS_TOKEN } from "@/modules/identity";
import { POST } from "./route";

const EMAIL = "owner@example.test";
const PASSWORD = "s3cret-Passw0rd";
const RETURN_PATH = "/dashboard/create/abc?step=content";

interface PostOptions {
  referer?: string;
  origin?: string;
  fetchSite?: string;
  fields?: Record<string, string>;
}

function postLogin({
  referer = "http://app.test/login",
  origin = "http://app.test",
  fetchSite = "same-origin",
  fields = { email: EMAIL, password: PASSWORD },
}: PostOptions = {}): Promise<Response> {
  const headers = new Headers({
    host: "app.test",
    origin,
    referer,
    "sec-fetch-site": fetchSite,
  });
  return POST(
    new NextRequest("http://app.test/auth/login", {
      method: "POST",
      headers,
      body: new URLSearchParams(fields),
    }),
  );
}

function mockBackend(
  implementation: () => Promise<Response>,
): MockInstance<typeof fetch> {
  return vi.spyOn(globalThis, "fetch").mockImplementation(implementation);
}

function tokenResponse(): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify({ access_token: "jwt-token" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function expectNoCredentialsIn(location: string): void {
  expect(location).not.toContain(PASSWORD);
  expect(location).not.toContain("password");
  expect(location).not.toContain(encodeURIComponent(EMAIL));
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("POST /auth/login", () => {
  // Scenario: A login form submitted without JavaScript signs in by POST
  it("signs in, sets the session cookie and returns to the safe path", async () => {
    const fetchMock = mockBackend(tokenResponse);
    const response = await postLogin({
      referer: `http://app.test/login?redirect=${encodeURIComponent(RETURN_PATH)}`,
    });

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(RETURN_PATH);
    expect(
      response.headers
        .getSetCookie()
        .some((cookie) =>
          cookie.startsWith(`${COOKIE_ACCESS_TOKEN}=jwt-token`),
        ),
    ).toBe(true);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toMatch(/\/api\/auth\/token$/);
    expect(init?.method).toBe("POST");
    expect(typeof init?.body).toBe("string");
    expect(JSON.parse(init?.body as string)).toEqual({
      email: EMAIL,
      password: PASSWORD,
    });
  });

  // Scenario: A failed sign-in without JavaScript returns an error code only
  it.each([
    [
      "the backend rejects the credentials",
      () => Promise.resolve(new Response("{}", { status: 401 })),
    ],
    ["the backend is unreachable", () => Promise.reject(new Error("offline"))],
    [
      "the backend answers without a token",
      () => Promise.resolve(new Response("{}", { status: 200 })),
    ],
    [
      "the backend answers invalid JSON",
      () => Promise.resolve(new Response("nope", { status: 200 })),
    ],
  ])("returns to login with an error when %s", async (_case, backend) => {
    mockBackend(backend);
    const response = await postLogin({
      referer: `http://app.test/login?redirect=${encodeURIComponent(RETURN_PATH)}`,
    });

    const location = response.headers.get("location") ?? "";
    expect(response.status).toBe(303);
    expect(location).toBe(
      `/login?error=invalid_credentials&redirect=${encodeURIComponent(RETURN_PATH)}`,
    );
    expectNoCredentialsIn(location);
    expect(response.headers.getSetCookie()).toEqual([]);
  });

  // Scenario: A failed sign-in without JavaScript returns an error code only
  it.each([
    [{ email: EMAIL }],
    [{ password: PASSWORD }],
    [{ email: "", password: PASSWORD }],
  ])("does not call the backend for incomplete fields %j", async (fields) => {
    const fetchMock = mockBackend(tokenResponse);
    const response = await postLogin({ fields });

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.get("location")).toBe(
      "/login?error=invalid_credentials",
    );
  });

  // Scenario: A login form submitted without JavaScript signs in by POST
  it("drops an unsafe return path", async () => {
    mockBackend(tokenResponse);
    const response = await postLogin({
      referer: "http://app.test/login?redirect=//evil.example",
    });

    expect(response.headers.get("location")).toBe("/dashboard/chat");
  });

  // Scenario: A sign-in posted from another site is refused
  it.each([
    [{ fetchSite: "cross-site" }],
    [{ origin: "https://evil.example" }],
    [{ origin: "not a url" }],
  ])("refuses a cross-site post %j", async (options) => {
    const fetchMock = mockBackend(tokenResponse);
    const response = await postLogin(options);

    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.getSetCookie()).toEqual([]);
  });
});
