/**
 * Error text for failed API responses.
 * Gherkin: tests/features/api-error-detail-ae0446.feature
 */
import { describe, expect, it } from "vitest";
import { responseErrorDetail } from "./response-error";

function jsonResponse(body: unknown, status = 400): Response {
  return new Response(JSON.stringify(body), { status });
}

describe("responseErrorDetail (AE-0446)", () => {
  // Scenario: A handled API error shows its message
  it("returns a string detail", async () => {
    await expect(
      responseErrorDetail(jsonResponse({ detail: "Email already used" })),
    ).resolves.toBe("Email already used");
  });

  // Scenario: A validation error falls back to the translated message
  it("ignores a 422 validation list", async () => {
    const body = { detail: [{ loc: ["body", "email"], msg: "bad" }] };
    await expect(
      responseErrorDetail(jsonResponse(body, 422)),
    ).resolves.toBeUndefined();
  });

  // Scenario: A non-JSON error falls back to the translated message
  it("ignores a body that is not JSON", async () => {
    await expect(
      responseErrorDetail(new Response("Bad Gateway", { status: 502 })),
    ).resolves.toBeUndefined();
  });

  it("ignores JSON without a detail", async () => {
    await expect(
      responseErrorDetail(jsonResponse({ error: "x" })),
    ).resolves.toBeUndefined();
  });
});
