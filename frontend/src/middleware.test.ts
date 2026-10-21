/**
 * Route guard behavior, pinned before the middleware was split into
 * small functions (it had no tests).
 * Gherkin: tests/features/auth-middleware-ae0446.feature
 */
import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const verifyAccessToken = vi.fn<(token: string) => Promise<unknown>>();

vi.mock("@/modules/identity", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/identity")>()),
  verifyAccessToken: (token: string) => verifyAccessToken(token),
}));

const { middleware } = await import("./middleware");

const ORIGIN = "http://localhost:3000";

function request(path: string, token?: string): NextRequest {
  const headers = token ? { cookie: `access_token=${token}` } : undefined;
  return new NextRequest(`${ORIGIN}${path}`, { headers });
}

function location(response: Response): string | null {
  return response.headers.get("location");
}

function clearsCookie(response: Response): boolean {
  return (response.headers.get("set-cookie") ?? "").includes("access_token=;");
}

describe("middleware route guard (AE-0446)", () => {
  beforeEach(() => verifyAccessToken.mockReset());

  // Scenario: Public pages and static assets need no session
  it("lets public pages and static assets through", async () => {
    expect(location(await middleware(request("/")))).toBeNull();
    expect(location(await middleware(request("/favicon.ico")))).toBeNull();
  });

  // Scenario: An anonymous visitor is sent to login with a return path
  it("redirects an anonymous dashboard visit to login with the path", async () => {
    const response = await middleware(request("/dashboard/create"));
    expect(location(response)).toBe(
      `${ORIGIN}/login?redirect=%2Fdashboard%2Fcreate`,
    );
  });

  it("renders the login page for an anonymous visitor", async () => {
    expect(location(await middleware(request("/login")))).toBeNull();
  });

  // Scenario: An expired session is cleared
  it("clears an invalid cookie on the login page without redirecting", async () => {
    verifyAccessToken.mockResolvedValue(null);
    const response = await middleware(request("/login", "stale"));
    expect(location(response)).toBeNull();
    expect(clearsCookie(response)).toBe(true);
  });

  it("clears an invalid cookie and sends a dashboard visit to login", async () => {
    verifyAccessToken.mockResolvedValue(null);
    const response = await middleware(request("/dashboard/create", "stale"));
    expect(location(response)).toContain("/login?redirect=");
    expect(clearsCookie(response)).toBe(true);
  });

  // Scenario: A signed-in user skips the login page
  it("sends a signed-in user from login to the dashboard chat", async () => {
    verifyAccessToken.mockResolvedValue({ role: "viewer" });
    const response = await middleware(request("/login", "ok"));
    expect(location(response)).toBe(`${ORIGIN}/dashboard/chat`);
  });

  /**
   * Pinned as-is: "/chat" is a public route, matched before the session check,
   * so the "signed-in public chat -> dashboard chat" branch is unreachable.
   * Behaviour unchanged by owner decision.
   */
  it("keeps the public chat public even with a session", async () => {
    verifyAccessToken.mockResolvedValue({ role: "viewer" });
    expect(location(await middleware(request("/chat", "ok")))).toBeNull();
    expect(verifyAccessToken).not.toHaveBeenCalled();
  });

  // Scenario: Roles gate admin and editor pages
  it("forbids admin pages to a non-admin", async () => {
    verifyAccessToken.mockResolvedValue({ role: "editor" });
    const response = await middleware(request("/admin/users", "ok"));
    expect(location(response)).toBe(`${ORIGIN}/403`);
  });

  it("forbids editor pages to a viewer but opens the dashboard chat", async () => {
    verifyAccessToken.mockResolvedValue({ role: "viewer" });
    expect(location(await middleware(request("/dashboard/create", "ok")))).toBe(
      `${ORIGIN}/403`,
    );
    expect(
      location(await middleware(request("/dashboard/chat", "ok"))),
    ).toBeNull();
  });

  it("opens editor and admin pages to the right roles", async () => {
    verifyAccessToken.mockResolvedValue({ role: "editor" });
    expect(
      location(await middleware(request("/dashboard/create", "ok"))),
    ).toBeNull();
    verifyAccessToken.mockResolvedValue({ role: "admin" });
    expect(
      location(await middleware(request("/admin/users", "ok"))),
    ).toBeNull();
  });
});
