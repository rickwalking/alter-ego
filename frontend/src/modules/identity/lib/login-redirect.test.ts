import { describe, expect, it } from "vitest";

import { sanitizeLoginRedirect } from "@/modules/identity";

const FALLBACK = "/dashboard/chat";

describe("sanitizeLoginRedirect", () => {
  // Scenario: A same-origin return path is kept
  it.each([
    ["/dashboard/calendar", "/dashboard/calendar"],
    [
      "/dashboard/calendar?view=month#today",
      "/dashboard/calendar?view=month#today",
    ],
    [
      "/dashboard/create/3acfe723-c504-4dd4-ac39-d3d9063bae4a/publish",
      "/dashboard/create/3acfe723-c504-4dd4-ac39-d3d9063bae4a/publish",
    ],
    ["/blog?q=a%2Fb", "/blog?q=a%2Fb"],
    ["/blog?q=agent%20loops", "/blog?q=agent%20loops"],
    ["/dashboard/../dashboard/calendar", "/dashboard/calendar"],
    ["/", "/"],
    ["/login-help", "/login-help"],
  ])("keeps %s", (input, expected) => {
    expect(sanitizeLoginRedirect(input)).toBe(expected);
  });

  // Scenario: A missing or empty return path falls back to the dashboard chat
  it.each([[null], [""], ["dashboard"], ["   "]])(
    "falls back for %j",
    (input) => {
      expect(sanitizeLoginRedirect(input)).toBe(FALLBACK);
    },
  );

  // Scenario: Absolute and scheme-relative URLs are rejected
  it.each([
    ["https://example.org/"],
    ["http://example.org"],
    ["//example.org"],
    ["///example.org"],
    ["javascript:alert(1)"],
    ["data:text/html,hi"],
    ["https:example.org"],
    ["/.//example.org"],
    ["/..//example.org"],
    ["/a/..//example.org"],
    ["/x/../..//example.org"],
    ["/./.././/example.org"],
    ["/..;/..//example.org"],
    ["/%2E//example.org"],
    ["/%2E%2E//example.org"],
    ["/.%2e//example.org"],
    ["/dashboard/..//evil.com/x?y#z"],
    ["/.//login"],
  ])("rejects %s", (input) => {
    expect(sanitizeLoginRedirect(input)).toBe(FALLBACK);
  });

  // Scenario: Backslash tricks are rejected
  it.each([
    ["/\\example.org"],
    ["/\\/example.org"],
    ["\\\\example.org"],
    ["/%5Cexample.org"],
    ["/%5cexample.org"],
    ["/%255Cexample.org"],
    ["/dashboard\\..\\..\\example.org"],
  ])("rejects %s", (input) => {
    expect(sanitizeLoginRedirect(input)).toBe(FALLBACK);
  });

  // Scenario: Control characters and encoded separators are rejected
  it.each([
    ["/\t/example.org"],
    ["/\n/example.org"],
    ["/\r/example.org"],
    ["/%09/example.org"],
    ["/%0A/example.org"],
    ["/%2Fexample.org"],
    ["/%2F%2Fexample.org"],
    ["%2F%2Fexample.org"],
    ["/%E0%A4%A"],
    ["/dashboard\u0000"],
  ])("rejects %j", (input) => {
    expect(sanitizeLoginRedirect(input)).toBe(FALLBACK);
  });

  // Scenario: A return path back to the login page is rejected
  it.each([
    ["/login"],
    ["/login?redirect=/dashboard"],
    ["/login/"],
    ["/dashboard/../login"],
    ["/login#x"],
  ])("rejects %s", (input) => {
    expect(sanitizeLoginRedirect(input)).toBe(FALLBACK);
  });
});
