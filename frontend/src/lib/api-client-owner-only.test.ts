import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { apiCallOwnerOnly, apiUpload, ApiError } from "./api-client";

/**
 * Gherkin: frontend/tests/features/cover-panel-follow-up-ae0554.feature.
 */

const schema = z.object({ id: z.string() });

function stubLocation(): { href: string; pathname: string; search: string } {
  const location = { href: "", pathname: "/dashboard", search: "" };
  Object.defineProperty(globalThis, "location", {
    value: location,
    writable: true,
    configurable: true,
  });
  return location;
}

function answer(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
    headers: new Headers(),
  });
}

describe("apiCallOwnerOnly", () => {
  afterEach(() => vi.unstubAllGlobals());

  /** Scenario: A viewer who is not the owner sees no upload or generate control */
  it("throws a 403 without sending the page to /403", async () => {
    const location = stubLocation();
    vi.stubGlobal(
      "fetch",
      answer(403, { detail: "cover_generation_not_owner" }),
    );

    const error: unknown = await apiCallOwnerOnly("/api/x", schema).catch(
      (err: unknown) => err,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(403);
    expect(location.href).toBe("");
  });

  /** Scenario: A viewer who is not the owner sees no upload or generate control */
  it("still sends a 401 to the login page", async () => {
    const location = stubLocation();
    vi.stubGlobal("fetch", answer(401, { message: "expired" }));

    await expect(apiCallOwnerOnly("/api/x", schema)).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(location.href).toContain("/auth/logout");
  });

  /** Scenario: A viewer who is not the owner sees no upload or generate control */
  it("parses the owner's answer with the schema", async () => {
    vi.stubGlobal("fetch", answer(200, { id: "g1", extra: 1 }));

    await expect(apiCallOwnerOnly("/api/x", schema)).resolves.toEqual({
      id: "g1",
    });
  });
});

describe("apiUpload contract breaks", () => {
  afterEach(() => vi.unstubAllGlobals());

  /** Scenario: An upload failure says its cause */
  it.each([
    ["a reply that is not JSON", () => Promise.reject(new SyntaxError("x"))],
    ["a reply that misses fields", () => Promise.resolve({ other: 1 })],
  ])("reads %s as a server error", async (_case, json) => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 201, json }),
    );

    const error: unknown = await apiUpload(
      "/api/u",
      schema,
      new FormData(),
    ).catch((err: unknown) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(500);
  });
});
