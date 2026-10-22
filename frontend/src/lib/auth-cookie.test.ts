import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

import {
  isSecureRequest,
  sanitizeLoginRedirect,
  setAccessTokenCookie,
} from "@/lib/auth-cookie";

describe("sanitizeLoginRedirect", () => {
  it("returns dashboard chat when redirect is missing", () => {
    expect(sanitizeLoginRedirect(null)).toBe("/dashboard/chat");
  });

  it("rejects external URLs", () => {
    expect(sanitizeLoginRedirect("//evil.com")).toBe("/dashboard/chat");
    expect(sanitizeLoginRedirect("https://evil.com")).toBe("/dashboard/chat");
  });

  it("allows internal dashboard paths", () => {
    expect(
      sanitizeLoginRedirect(
        "/dashboard/create/3acfe723-c504-4dd4-ac39-d3d9063bae4a/publish",
      ),
    ).toBe("/dashboard/create/3acfe723-c504-4dd4-ac39-d3d9063bae4a/publish");
  });
});

describe("isSecureRequest", () => {
  it("detects HTTPS from forwarded proto header", () => {
    const request = new NextRequest("http://localhost/login", {
      headers: { "x-forwarded-proto": "https" },
    });
    expect(isSecureRequest(request)).toBe(true);
  });

  it("returns false for plain HTTP", () => {
    const request = new NextRequest("http://127.0.0.1:3000/login");
    expect(isSecureRequest(request)).toBe(false);
  });
});

describe("setAccessTokenCookie", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  function sessionCookie(): string {
    const response = NextResponse.json({});
    setAccessTokenCookie(
      response,
      "jwt",
      new NextRequest("http://localhost/auth/login"),
    );
    return response.headers.getSetCookie()[0] ?? "";
  }

  // Scenario: The no-JavaScript sign-in sets the same session cookie as the normal login
  it("sets an HttpOnly SameSite=Strict cookie for the backend's token lifetime", () => {
    vi.stubEnv("ACCESS_TOKEN_EXPIRE_MINUTES", "30");
    const cookie = sessionCookie();
    expect(cookie).toMatch(/^access_token=jwt;/);
    expect(cookie).toMatch(/; HttpOnly/i);
    expect(cookie).toMatch(/; SameSite=strict/i);
    expect(cookie).toMatch(/; Max-Age=1800(;|$)/);
  });

  // Scenario: The no-JavaScript sign-in sets the same session cookie as the normal login
  it.each([[""], ["0"], ["-5"], ["1.5"], ["soon"]])(
    "falls back to the backend default of 60 minutes for %j",
    (value) => {
      vi.stubEnv("ACCESS_TOKEN_EXPIRE_MINUTES", value);
      expect(sessionCookie()).toMatch(/; Max-Age=3600(;|$)/);
    },
  );
});
