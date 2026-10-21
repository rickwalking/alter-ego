/**
 * verifyAccessToken with a configured secret: after jose verifies the token the
 * claims are narrowed to their declared types (a non-string email claim in a
 * validly signed token becomes "" instead of a stringified value). jose is
 * mocked because its Uint8Array checks do not hold across the jsdom realm.
 */
import { jwtVerify } from "jose";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { JWT_TYPE_AUTH } from "@/constants/jwt";

import { verifyAccessToken } from "./jwt-auth";

vi.mock("jose", () => ({ jwtVerify: vi.fn() }));

const SECRET = "jwt-auth-test-secret";
const TOKEN = "header.payload.signature";
const SUB = "user-1";
const EMAIL = "owner@example.test";
const ROLE = "admin";
const IAT = 1_700_000_000;
const EXP = 1_700_003_600;

function verified(payload: Record<string, unknown>): void {
  vi.mocked(jwtVerify).mockResolvedValueOnce({
    payload,
    protectedHeader: { alg: "HS256" },
  } as unknown as Awaited<ReturnType<typeof jwtVerify>>);
}

describe("verifyAccessToken", () => {
  beforeEach(() => {
    vi.stubEnv("AUTH_JWT_SECRET", SECRET);
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(jwtVerify).mockReset();
  });

  it("returns the typed claims of a valid auth token", async () => {
    verified({
      sub: SUB,
      email: EMAIL,
      role: ROLE,
      type: JWT_TYPE_AUTH,
      exp: EXP,
      iat: IAT,
    });
    expect(await verifyAccessToken(TOKEN)).toEqual({
      sub: SUB,
      email: EMAIL,
      role: ROLE,
      type: JWT_TYPE_AUTH,
      exp: EXP,
      iat: IAT,
    });
  });

  it("narrows a non-string email claim to an empty string", async () => {
    verified({ sub: SUB, email: 42, role: ROLE, type: JWT_TYPE_AUTH });
    expect((await verifyAccessToken(TOKEN))?.email).toBe("");
  });

  it("defaults missing sub, email, exp and iat claims", async () => {
    verified({ role: ROLE, type: JWT_TYPE_AUTH });
    expect(await verifyAccessToken(TOKEN)).toEqual({
      sub: "",
      email: "",
      role: ROLE,
      type: JWT_TYPE_AUTH,
      exp: 0,
      iat: 0,
    });
  });

  it("returns null when jose rejects the token", async () => {
    vi.mocked(jwtVerify).mockRejectedValueOnce(new Error("bad signature"));
    expect(await verifyAccessToken(TOKEN)).toBeNull();
  });

  it("rejects a non-auth token type and a non-string role", async () => {
    verified({ sub: SUB, role: ROLE, type: "refresh" });
    expect(await verifyAccessToken(TOKEN)).toBeNull();
    verified({ sub: SUB, role: 7, type: JWT_TYPE_AUTH });
    expect(await verifyAccessToken(TOKEN)).toBeNull();
  });
});
