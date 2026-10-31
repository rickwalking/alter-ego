import { describe, expect, it } from "vitest";

import {
  buildUserUpdatePayload,
  isFullNameValidationError,
  isValidFullName,
} from "./user-update";

const CURRENT_NAME = "Jon Smith";

describe("isValidFullName", () => {
  // Scenario: A blank name is rejected before submit
  it("rejects an empty or whitespace-only name", () => {
    expect(isValidFullName("")).toBe(false);
    expect(isValidFullName("   ")).toBe(false);
  });

  // Scenario: A name longer than 255 characters is rejected before submit
  it("accepts 255 trimmed characters and rejects 256", () => {
    expect(isValidFullName(`  ${"a".repeat(255)}  `)).toBe(true);
    expect(isValidFullName("a".repeat(256))).toBe(false);
  });

  // Scenario: Names are counted in characters, not code units
  it("counts code points, so 200 emoji pass and 256 code points fail", () => {
    expect(isValidFullName("😀".repeat(200))).toBe(true);
    expect(isValidFullName("😀".repeat(255))).toBe(true);
    expect(isValidFullName("😀".repeat(256))).toBe(false);
  });

  // Scenario: Admin renames a user
  it("accepts a one-character name", () => {
    expect(isValidFullName(" J ")).toBe(true);
  });
});

describe("buildUserUpdatePayload", () => {
  // Scenario: Admin renames a user
  it("sends the trimmed name when it changed", () => {
    expect(
      buildUserUpdatePayload(CURRENT_NAME, {
        role: "admin",
        isActive: false,
        fullName: "  John Smith  ",
      }),
    ).toEqual({ role: "admin", is_active: false, full_name: "John Smith" });
  });

  // Scenario: An unchanged name is not sent
  it("omits the name when the trimmed value is the current one", () => {
    expect(
      buildUserUpdatePayload(CURRENT_NAME, {
        role: "editor",
        isActive: true,
        fullName: ` ${CURRENT_NAME} `,
      }),
    ).toEqual({ role: "editor", is_active: true });
  });
});

describe("isFullNameValidationError", () => {
  // Scenario: The backend rejects the name
  it("is true when a validation error points at full_name", () => {
    expect(
      isFullNameValidationError({
        detail: [{ loc: ["body", "full_name"], msg: "too short" }],
      }),
    ).toBe(true);
  });

  // Scenario: Another validation error keeps the generic message
  it("is false for errors on other fields or other body shapes", () => {
    expect(
      isFullNameValidationError({ detail: [{ loc: ["body", "role"] }] }),
    ).toBe(false);
    expect(isFullNameValidationError({ detail: [{ msg: "no loc" }] })).toBe(
      false,
    );
    expect(isFullNameValidationError({ detail: [null] })).toBe(false);
    expect(isFullNameValidationError({ detail: [{ loc: "full_name" }] })).toBe(
      false,
    );
    expect(isFullNameValidationError({ detail: "Invalid role" })).toBe(false);
    expect(isFullNameValidationError({ other: 1 })).toBe(false);
    expect(isFullNameValidationError(null)).toBe(false);
  });
});
