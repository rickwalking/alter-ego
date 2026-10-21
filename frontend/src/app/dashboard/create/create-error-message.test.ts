import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api-client";
import { createErrorMessage } from "./create-error-message";

/** Echo translator (key + params), so assertions target the looked-up copy. */
const t = (key: string, values?: Record<string, string | number>): string =>
  values ? `${key}:${JSON.stringify(values)}` : key;

function apiError(status: number, detail?: unknown): ApiError {
  const error = new ApiError(status, `HTTP error! status: ${status}`);
  error.detail = detail;
  return error;
}

const nicheTooLong = {
  type: "string_too_long",
  loc: ["body", "niche"],
  msg: "String should have at most 200 characters",
  ctx: { max_length: 200 },
};

describe("createErrorMessage", () => {
  // Scenario: API validation errors are readable
  it("names the field and its limit once for a duplicated 422 detail", () => {
    const error = apiError(422, [nicheTooLong, nicheTooLong]);
    expect(createErrorMessage(error, t)).toBe(
      'errors.tooLong:{"field":"errors.fields.niche","max":200}',
    );
  });

  it("joins several fields and maps missing / too-short to required", () => {
    const error = apiError(422, [
      { type: "missing", loc: ["body", "topic"], msg: "Field required" },
      { type: "string_too_short", loc: ["body", "audience"], msg: "short" },
      { type: "value_error", loc: ["body", "theme"], msg: "bad theme" },
    ]);
    expect(createErrorMessage(error, t)).toBe(
      [
        'errors.required:{"field":"errors.fields.topic"}',
        'errors.required:{"field":"errors.fields.audience"}',
        'errors.invalid:{"field":"theme","message":"bad theme"}',
      ].join(" · "),
    );
  });

  it("falls back to a generic validation line when the 422 has no list", () => {
    expect(createErrorMessage(apiError(422, "bad"), t)).toBe(
      "errors.validation",
    );
    expect(createErrorMessage(apiError(422, []), t)).toBe("errors.validation");
  });

  it("keeps a string detail of other errors", () => {
    expect(createErrorMessage(apiError(409, "duplicate"), t)).toBe(
      'errors.createFailedDetail:{"detail":"duplicate"}',
    );
  });

  it("never shows the raw HTTP status text", () => {
    expect(createErrorMessage(apiError(500), t)).toBe("errors.createFailed");
    expect(createErrorMessage(new Error("network"), t)).toBe(
      "errors.createFailed",
    );
    expect(createErrorMessage("boom", t)).toBe("errors.createFailed");
  });
});
