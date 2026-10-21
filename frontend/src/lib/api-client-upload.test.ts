import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { apiUpload, ApiError } from "./api-client";

// AE-0376: multipart upload helper (photo library).
const schema = z.object({ id: z.string() });

describe("apiUpload", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts the form without a JSON content type and parses the reply", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "a1", extra: true }),
    });
    vi.stubGlobal("fetch", mockFetch);
    const form = new FormData();
    form.append("role", "hook");

    const result = await apiUpload("/api/upload", schema, form);

    expect(result).toEqual({ id: "a1" });
    const [url, init] = mockFetch.mock.calls[0]! as [string, RequestInit];
    expect(url).toBe("/api/upload");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(form);
    expect(init.credentials).toBe("include");
    expect(init.headers).toBeUndefined();
  });

  it("throws ApiError on a failed upload", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 413,
        statusText: "Too Large",
        json: () => Promise.resolve({ detail: "creator_asset_too_large" }),
        text: () => Promise.resolve("creator_asset_too_large"),
        headers: new Headers(),
      }),
    );
    await expect(
      apiUpload("/api/upload", schema, new FormData()),
    ).rejects.toBeInstanceOf(ApiError);
  });
});
