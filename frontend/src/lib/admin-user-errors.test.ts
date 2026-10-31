/**
 * Gherkin: tests/features/users-area-polish-ae0514.feature
 */
import { describe, expect, it } from "vitest";

import {
  adminErrorKey,
  createFieldErrors,
  isPasswordTooShort,
} from "./admin-user-errors";

describe("adminErrorKey", () => {
  // Scenario: A duplicate email shows a translated message
  // Scenario: A last-admin or self-delete refusal is translated
  it.each([
    ["user_email_exists", "emailTaken"],
    ["last_admin", "lastAdminError"],
    ["self_delete", "selfDeleteError"],
  ])("maps the code %s to %s", (code, key) => {
    expect(adminErrorKey(409, { detail: "English", code })).toBe(key);
  });

  // Scenario: A last-admin or self-delete refusal is translated
  it("maps a 404 without a code to the user-gone message", () => {
    expect(adminErrorKey(404, { detail: "User not found" })).toBe(
      "userNotFound",
    );
  });

  // Scenario: An unknown create failure keeps the generic message
  it.each([
    [409, { detail: "English", code: "unknown_code" }],
    [409, { detail: "English" }],
    [500, null],
    [400, { code: 7 }],
    [409, { detail: "English", code: "toString" }],
  ])("leaves %i %o to the caller's fallback", (status, body) => {
    expect(adminErrorKey(status, body)).toBeUndefined();
  });
});

describe("createFieldErrors", () => {
  // Scenario: A 422 field error is shown on its field
  it("keeps only the create-user fields of a 422", () => {
    const body = {
      detail: [
        { loc: ["body", "email"], msg: "bad" },
        { loc: ["body", "role"], msg: "bad" },
        { loc: ["body", "password"], msg: "short" },
        { loc: ["body", "constructor"], msg: "inherited name" },
      ],
    };
    expect(createFieldErrors(422, body)).toEqual({
      email: "emailInvalid",
      password: "minLengthNotMet",
    });
  });

  // Scenario: An unknown create failure keeps the generic message
  it("ignores the same body on another status", () => {
    const body = { detail: [{ loc: ["body", "email"], msg: "bad" }] };
    expect(createFieldErrors(400, body)).toEqual({});
  });
});

describe("isPasswordTooShort", () => {
  // Scenario: A short password is refused without a request
  it.each([
    ["", false],
    ["a", true],
    ["a".repeat(11), true],
    ["a".repeat(12), false],
    ["😀".repeat(12), false],
  ])("%j is too short: %s", (password, expected) => {
    expect(isPasswordTooShort(password)).toBe(expected);
  });
});
