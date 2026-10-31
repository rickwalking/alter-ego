import { describe, expect, it } from "vitest";

import { buildUserUpdatePayload, isValidFullName } from "./user-update";

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
