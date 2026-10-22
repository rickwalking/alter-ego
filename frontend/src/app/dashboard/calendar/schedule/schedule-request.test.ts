/**
 * Scenarios: tests/features/calendar-schedule-post.feature.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { BlogPost } from "@/modules/publishing";

const { mockFetch } = vi.hoisted(() => ({ mockFetch: vi.fn() }));
vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: mockFetch }));

import { requestSchedule } from "./schedule-request";

const POST = { id: "p1", title: "Launch", lock_version: 3 } as BlogPost;
const AT = new Date("2026-10-23T23:00:00.000Z");

function reply(status: number, body: unknown): void {
  mockFetch.mockResolvedValueOnce(
    new Response(JSON.stringify(body), { status }),
  );
}

describe("requestSchedule", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  // Scenario: Scheduling an approved post sends the UTC time with the post's version
  it("POSTs the UTC time with the lock version as If-Match", async () => {
    reply(200, { ...POST, scheduled_publish_at: AT.toISOString() });
    const result = await requestSchedule(POST, AT);
    expect(result).toEqual({
      ok: true,
      post: { ...POST, scheduled_publish_at: AT.toISOString() },
    });
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/blog-posts/p1/schedule");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({
      "Content-Type": "application/json",
      "If-Match": "3",
    });
    expect(JSON.parse(init.body as string)).toEqual({
      scheduled_publish_at: "2026-10-23T23:00:00.000Z",
    });
  });

  // Scenario: A post changed since the list loaded is reported
  it("maps 409 to a version conflict", async () => {
    reply(409, { detail: "version_conflict" });
    expect(await requestSchedule(POST, AT)).toEqual({
      ok: false,
      error: "versionConflict",
    });
  });

  // Scenario: A post that is not ready to publish is reported
  it("maps 422 to not ready", async () => {
    reply(422, { detail: "ai_disclosure_required" });
    expect(await requestSchedule(POST, AT)).toEqual({
      ok: false,
      error: "notReady",
    });
  });

  // Scenario: The backend refusing a past time is reported
  it("maps 400 schedule_in_past to a past time", async () => {
    reply(400, { detail: "schedule_in_past" });
    expect(await requestSchedule(POST, AT)).toEqual({
      ok: false,
      error: "timeInPast",
    });
  });

  // Scenario: An unexpected failure is reported
  it("maps any other refusal or a network error to failed", async () => {
    reply(400, { detail: "invalid_status_transition" });
    expect(await requestSchedule(POST, AT)).toMatchObject({ error: "failed" });
    mockFetch.mockResolvedValueOnce(new Response("oops", { status: 400 }));
    expect(await requestSchedule(POST, AT)).toMatchObject({ error: "failed" });
    reply(500, {});
    expect(await requestSchedule(POST, AT)).toMatchObject({ error: "failed" });
    mockFetch.mockRejectedValueOnce(new Error("offline"));
    expect(await requestSchedule(POST, AT)).toMatchObject({ error: "failed" });
  });
});
