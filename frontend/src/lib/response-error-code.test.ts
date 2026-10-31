/**
 * Gherkin: tests/features/users-area-polish-ae0514.feature
 */
import { describe, expect, it } from "vitest";

import {
  errorBodyCode,
  responseErrorBody,
  validationErrorFields,
} from "./response-error";

describe("responseErrorBody", () => {
  // Scenario: A duplicate email shows a translated message
  it("reads the JSON body and leaves the response readable", async () => {
    const response = new Response(JSON.stringify({ code: "x" }), {
      status: 409,
    });
    await expect(responseErrorBody(response)).resolves.toEqual({ code: "x" });
    await expect(response.json()).resolves.toEqual({ code: "x" });
  });

  // Scenario: An unknown create failure keeps the generic message
  it("gives null for a body that is not JSON", async () => {
    await expect(
      responseErrorBody(new Response("Bad Gateway", { status: 502 })),
    ).resolves.toBeNull();
  });
});

describe("errorBodyCode", () => {
  // Scenario: A deactivated account sees a translated login message
  it("returns a string code", () => {
    expect(errorBodyCode({ detail: "x", code: "user_inactive" })).toBe(
      "user_inactive",
    );
  });

  // Scenario: Wrong credentials keep the translated invalid-credentials message
  it.each([null, "text", { detail: "x" }, { code: 3 }])(
    "gives undefined for %o",
    (body) => {
      expect(errorBodyCode(body)).toBeUndefined();
    },
  );
});

describe("validationErrorFields", () => {
  // Scenario: A 422 field error is shown on its field
  it("lists the last loc segment of each validation error", () => {
    const body = {
      detail: [
        { loc: ["body", "email"] },
        { loc: ["body", "password"] },
        { loc: ["body", 0] },
        { loc: "body" },
        { msg: "no loc" },
        null,
      ],
    };
    expect(validationErrorFields(body)).toEqual(["email", "password"]);
  });

  // Scenario: An unknown create failure keeps the generic message
  it.each([null, { detail: "English" }, { other: [] }])(
    "gives an empty list for %o",
    (body) => {
      expect(validationErrorFields(body)).toEqual([]);
    },
  );
});
