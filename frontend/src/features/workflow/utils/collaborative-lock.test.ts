import { describe, it, expect } from "vitest";

import { isLockedByAnotherUser } from "./collaborative-lock";
import type { ContentLock } from "../types";

// Feature: phase3_workflow_collaboration.feature
// Scenario: Collaborative editing lock detection

describe("isLockedByAnotherUser", () => {
  const lock: ContentLock = {
    content_id: "post-1",
    content_type: "blog_post",
    user_id: "user-a",
    user_name: "Alice",
    expires_at: "2026-01-01T00:00:00Z",
  };

  it("returns false when lock is null", () => {
    expect(isLockedByAnotherUser(null, "user-b")).toBe(false);
  });

  it("returns false when current user holds the lock", () => {
    expect(isLockedByAnotherUser(lock, "user-a")).toBe(false);
  });

  it("returns true when another user holds the lock", () => {
    expect(isLockedByAnotherUser(lock, "user-b")).toBe(true);
  });
});
