import { describe, expect, it } from "vitest";

import { decodeJwtPayloadUnsafe } from "@/lib/jwt-auth";

function buildToken(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/u, "");
  return `${header}.${body}.signature`;
}

describe("decodeJwtPayloadUnsafe", () => {
  it("rejects expired tokens", () => {
    const token = buildToken({
      sub: "user-1",
      email: "a@b.com",
      role: "admin",
      type: "auth",
      exp: Math.floor(Date.now() / 1000) - 60,
      iat: Math.floor(Date.now() / 1000) - 120,
    });
    expect(decodeJwtPayloadUnsafe(token)).toBeNull();
  });

  it("accepts valid unexpired tokens", () => {
    const token = buildToken({
      sub: "user-1",
      email: "a@b.com",
      role: "admin",
      type: "auth",
      exp: Math.floor(Date.now() / 1000) + 3600,
      iat: Math.floor(Date.now() / 1000),
    });
    expect(decodeJwtPayloadUnsafe(token)?.role).toBe("admin");
  });
});
