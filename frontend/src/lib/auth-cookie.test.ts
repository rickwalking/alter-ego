import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { isSecureRequest, sanitizeLoginRedirect } from "@/lib/auth-cookie";

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
