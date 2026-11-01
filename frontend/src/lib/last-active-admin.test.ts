/**
 * Gherkin: tests/features/last-active-admin-guard-ae0585.feature
 */
import { describe, expect, it } from "vitest";

import { lastActiveAdminId } from "./last-active-admin";

const ACTIVE_ADMIN = { id: "a1", role: "admin", is_active: true };
const OTHER_ACTIVE_ADMIN = { id: "a2", role: "admin", is_active: true };
const INACTIVE_ADMIN = { id: "a3", role: "admin", is_active: false };
const ACTIVE_EDITOR = { id: "e1", role: "editor", is_active: true };

describe("lastActiveAdminId", () => {
  // Scenario: The role and active controls are locked for the last active admin
  it("returns the id of the only active admin", () => {
    expect(lastActiveAdminId([ACTIVE_EDITOR, ACTIVE_ADMIN])).toBe("a1");
  });

  // Scenario: The controls stay enabled when another admin is active
  it("returns undefined when two admins are active", () => {
    expect(
      lastActiveAdminId([ACTIVE_ADMIN, OTHER_ACTIVE_ADMIN]),
    ).toBeUndefined();
  });

  // Scenario: Inactive admins do not count as active admins
  it("ignores inactive admins", () => {
    expect(lastActiveAdminId([INACTIVE_ADMIN, ACTIVE_ADMIN])).toBe("a1");
  });

  // Scenario: Other users keep their controls
  it("returns undefined when no admin is active", () => {
    expect(lastActiveAdminId([INACTIVE_ADMIN, ACTIVE_EDITOR])).toBeUndefined();
    expect(lastActiveAdminId([])).toBeUndefined();
  });
});
