/**
 * AE-0165 — Frontend auth BASELINE safety net.
 *
 * Captures the CURRENT (pre-relocation) frontend auth behavior so the later
 * identity-module relocation (AE-0156/0164) can be proven byte-identical. These
 * tests assert what the app ACTUALLY does today; they do not "fix" anything.
 *
 * Deterministic + backend-free:
 *  - The frontend has NO JWT secret configured, so the middleware validates
 *    tokens via the unsafe base64url fallback (signature ignored). We therefore
 *    craft unsigned tokens (see helpers/auth-baseline-tokens.ts) and set them as
 *    the httpOnly `access_token` cookie via `context.addCookies`.
 *  - Every request the page makes to the proxied backend (`/api/auth/*`,
 *    `/api/admin/*`) is intercepted with `page.route(...)` + `route.fulfill(...)`,
 *    so no live backend or external keys are needed.
 *
 * Runs in the dedicated `auth-baseline` Playwright project (no storageState, no
 * `setup` dependency) so it never triggers the real-backend admin login.
 */
import { test, expect, type Page } from "@playwright/test";

import {
  accessTokenCookie,
  craftAdminToken,
  craftEditorToken,
  craftExpiredAdminToken,
  craftViewerToken,
} from "./helpers/auth-baseline-tokens";

const DASHBOARD_CHAT_ROUTE = "/dashboard/chat";
const PROTECTED_DASHBOARD_ROUTE = "/dashboard/knowledge";
const ADMIN_ROUTE = "/admin/users";
const LOGIN_PATH = "/login";

/** A successful /api/auth/me response shape (mirrors useAuth's AuthUser). */
function meResponseBody(role: string): string {
  return JSON.stringify({
    id: `baseline-${role}`,
    email: `${role}@baseline.test`,
    full_name: `Baseline ${role}`,
    role,
  });
}

/** Fulfill GET /api/auth/me with a logged-in user of the given role. */
async function stubAuthMe(page: Page, role: string): Promise<void> {
  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: meResponseBody(role),
    });
  });
}

test.describe("auth baseline safety net", () => {
  // Scenario: Unauthenticated guard
  // No cookie -> visiting a protected dashboard route redirects to /login with
  // the original path captured in the `redirect` query param.
  test("unauthenticated request to a protected route redirects to /login with redirect param", async ({
    page,
  }) => {
    await page.goto(PROTECTED_DASHBOARD_ROUTE);

    await expect(page).toHaveURL(
      new RegExp(
        `/login\\?redirect=${encodeURIComponent(PROTECTED_DASHBOARD_ROUTE)}`,
      ),
    );
    const url = new URL(page.url());
    expect(url.pathname).toBe(LOGIN_PATH);
    expect(url.searchParams.get("redirect")).toBe(PROTECTED_DASHBOARD_ROUTE);
  });

  // Scenario: Login success
  // Start at /login, mock POST /api/auth/token to succeed. The real /api/auth/token
  // handler sets the httpOnly cookie from the backend; since we intercept it, we
  // set the cookie ourselves inside the route handler (Set-Cookie via fulfill is
  // not reliably applied to the browser context for httpOnly cookies), then the
  // client navigates to the sanitized redirect (dashboard chat).
  test("successful login navigates from /login to the dashboard chat route", async ({
    page,
    context,
  }) => {
    const adminToken = craftAdminToken();
    await stubAuthMe(page, "admin");

    // Approach used: addCookies inside the token route handler (deterministic for
    // httpOnly cookies; Set-Cookie via route.fulfill proved unreliable).
    await page.route("**/api/auth/token", async (route) => {
      await context.addCookies([accessTokenCookie(adminToken)]);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: adminToken,
          token_type: "bearer",
        }),
      });
    });

    await page.goto(LOGIN_PATH);
    await page.locator("#email").fill("admin@baseline.test");
    await page.locator("#password").fill("baseline-password");
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(page).toHaveURL(new RegExp(`${DASHBOARD_CHAT_ROUTE}$`));
    await expect(page).not.toHaveURL(/\/login/);
  });

  // Scenario: Logout (BASELINE — captures the ACTUAL behavior, which differs from
  // a naive "logout lands on /login" expectation).
  //
  // useAuth.logout() does `fetch POST /api/auth/logout` then
  // `window.location.href = "/login"`. OBSERVED divergence from the architecture
  // description:
  //   1. The local app/api/auth/logout route ONLY defines GET (which is what
  //      clears the cookie); the hook calls it with POST. So the logout request
  //      does NOT clear the `access_token` cookie.
  //   2. Because the (still valid) admin cookie survives, navigating to "/login"
  //      hits the middleware, which treats /login as an auth route with a valid
  //      token and IMMEDIATELY redirects back to DASHBOARD_ROUTES.CHAT.
  // Net observed outcome: clicking Logout bounces /login -> /dashboard/chat and
  // the session cookie is STILL present. We assert that real behavior here.
  test("logout from the dashboard shell calls logout, keeps the cookie, and bounces back to /dashboard/chat", async ({
    page,
    context,
  }) => {
    await context.addCookies([accessTokenCookie(craftAdminToken())]);
    await stubAuthMe(page, "admin");

    let logoutCalled = false;
    await page.route("**/api/auth/logout", async (route) => {
      logoutCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "{}",
      });
    });

    await page.goto(DASHBOARD_CHAT_ROUTE);
    await page.getByRole("button", { name: "Logout" }).click();

    // The logout endpoint was hit...
    await expect.poll(() => logoutCalled).toBe(true);

    // ...but the middleware bounces the valid-cookie session away from /login
    // back to the dashboard chat route (OBSERVED, not /login).
    await expect(page).toHaveURL(new RegExp(`${DASHBOARD_CHAT_ROUTE}$`));

    // OBSERVED: the access_token cookie is NOT cleared by the POST logout path.
    const cookies = await context.cookies();
    const accessCookie = cookies.find((c) => c.name === "access_token");
    expect(accessCookie).toBeDefined();
  });

  // Scenario: Expired / invalid token
  // An expired crafted cookie on a protected route -> middleware clears the session
  // and redirects to /login (with redirect param).
  test("expired token on a protected route redirects to /login and clears session", async ({
    page,
    context,
  }) => {
    await context.addCookies([accessTokenCookie(craftExpiredAdminToken())]);

    await page.goto(PROTECTED_DASHBOARD_ROUTE);

    await expect(page).toHaveURL(new RegExp("/login"));
    const url = new URL(page.url());
    expect(url.pathname).toBe(LOGIN_PATH);
    expect(url.searchParams.get("redirect")).toBe(PROTECTED_DASHBOARD_ROUTE);

    // OBSERVED: redirectWithClearedSession deletes the access_token cookie.
    const cookies = await context.cookies();
    const accessCookie = cookies.find((c) => c.name === "access_token");
    expect(accessCookie).toBeUndefined();
  });

  // Scenario: Admin guard — non-admin blocked
  // Editor-role cookie visiting /admin/* -> middleware redirects to /403.
  test("editor role visiting an admin route is redirected to /403", async ({
    page,
    context,
  }) => {
    await context.addCookies([accessTokenCookie(craftEditorToken())]);
    await stubAuthMe(page, "editor");

    await page.goto(ADMIN_ROUTE);

    await expect(page).toHaveURL(new RegExp("/403$"));
  });

  // Scenario: Admin guard — admin allowed
  // Admin-role cookie visiting /admin/* -> route loads (no /403 redirect).
  test("admin role visiting an admin route is not redirected to /403", async ({
    page,
    context,
  }) => {
    await context.addCookies([accessTokenCookie(craftAdminToken())]);
    await stubAuthMe(page, "admin");
    // The admin users page fetches /api/admin/users on mount; stub it.
    await page.route("**/api/admin/users**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    await page.goto(ADMIN_ROUTE);

    await expect(page).toHaveURL(new RegExp(`${ADMIN_ROUTE}$`));
    await expect(page).not.toHaveURL(/\/403/);
  });

  // Scenario: Editor-dashboard guard — plain role blocked
  // A plain (viewer) role on an editor-only dashboard route -> /403.
  test("plain role visiting an editor-only dashboard route is redirected to /403", async ({
    page,
    context,
  }) => {
    await context.addCookies([accessTokenCookie(craftViewerToken())]);
    await stubAuthMe(page, "viewer");

    await page.goto(PROTECTED_DASHBOARD_ROUTE);

    await expect(page).toHaveURL(new RegExp("/403$"));
  });
});
